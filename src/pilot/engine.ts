// The session engine: owns the queue and everything that must happen when an answer comes in (checking, logging,
// scheduling, picking help). The UI only renders what it returns. Guardrails live here: nothing is revealed
// before an answer is committed, only the first L5 attempt reaches the schedule, and the learner never rates a card.
import type { Store } from '../data/store';
import type { Attempt, Format, Instance, Pattern, Schedule, StuckReason } from '../data/types';
import type {
  BenchResult,
  BlankResult,
  CheckOptions,
  CheckResult,
  PartName,
  RefEffects,
  ResultOf,
} from '../python/protocol';
import { dayKey } from './dates';
import { summarise, type Summary } from './measures';
import { pickFormat, pickIntent, pickInstance } from './pick';
import { buildQueue, insertRetry, type QueueItem, type SessionOptions } from './queue';
import { partOrder, PART_ROTATION, routeMiss, routeStuck, type CardProgress, type Help } from './routing';
import { afterFirstAttempt, gateOn, isFluent, newSchedule } from './schedule';

export interface PythonApi {
  check(req: { setups: string[]; reference: string; answer: string; options?: CheckOptions }): Promise<CheckResult>;
  bench(setup: string, line?: string): Promise<BenchResult>;
  blank(line: string, part: PartName): Promise<BlankResult | null>;
  effects(setup: string, reference: string): Promise<RefEffects>;
  parts(line: string): Promise<ResultOf['parts']>;
}

export interface Deps {
  store: Store;
  python: PythonApi;
  now: () => Date;
  rng: () => number;
  options?: SessionOptions;
}

export type EffectName = 'rebinds' | 'mutates' | 'sends_out' | 'nothing';

export interface Card {
  pattern: Pattern;
  instance: Instance;
  intentIndex: number;
  format: Exclude<Format, 'cold'>;
  /** The effect gate is shown while a pattern is new, and again after an effect or landing miss. */
  gate: boolean;
  /** Fluent patterns show only the verdict after a correct answer; the bench sits behind Explain. */
  fluent: boolean;
  isRetry: boolean;
  refEffects: RefEffects;
  /** L5 attempts so far on this card (the very first one is the one scheduling sees). */
  l5Attempts: number;
  progress: CardProgress;
}

export interface Timing {
  msToFirstKey: number | null;
  msToAnswer: number | null;
}

export interface L5Input extends Timing {
  answer: string;
  /** Null when the gate is off for this pattern. */
  effectPicked: EffectName[] | null;
  sure: boolean;
}

export interface L5Outcome {
  result: CheckResult;
  effectCorrect: boolean | null;
  help: Help;
  /** The reference line, shown only once a retry has been answered (section 8). */
  reveal: string | null;
  /** The card itself is broken (a setup fails): not the learner's miss, nothing was logged or scheduled. */
  noteError: boolean;
}

const sameSet = (a: string[], b: string[]) => a.length === b.length && a.every((x) => b.includes(x));

export class Engine {
  readonly sessionAttempts: Attempt[] = [];
  private queue: QueueItem[];

  private constructor(
    private d: Deps,
    private patterns: Pattern[],
    queue: QueueItem[],
  ) {
    this.queue = queue;
  }

  static async create(d: Deps): Promise<Engine> {
    const patterns = await d.store.patterns();
    const schedules = await d.store.schedules();
    return new Engine(d, patterns, buildQueue(patterns, schedules, dayKey(d.now()), d.options));
  }

  /** Cards still to come, not counting the one on screen. */
  get cardsLeft(): number {
    return this.queue.length;
  }

  async nextCard(): Promise<Card | null> {
    const item = this.queue.shift();
    if (!item) return null;
    const pattern = this.patterns.find((p) => p.id === item.patternId)!;
    const sched = await this.d.store.schedule(pattern.id);
    const instance = item.instanceId
      ? pattern.instances.find((i) => i.id === item.instanceId)!
      : pickInstance(pattern, sched);
    const intentIndex = pickIntent(instance, sched, item.avoidIntent);
    const isRetry = item.kind === 'retry';
    if (isRetry && sched) {
      await this.d.store.putSchedule({ ...sched, lastIntent: { ...sched.lastIntent, [instance.id]: intentIndex } });
    }
    return {
      pattern,
      instance,
      intentIndex,
      format: item.format === 'notebook' || item.format === 'english' ? item.format : pickFormat(sched, this.d.rng),
      gate: gateOn(sched),
      fluent: !isRetry && isFluent(sched),
      isRetry,
      refEffects: await this.d.python.effects(instance.setups[0], instance.reference),
      l5Attempts: 0,
      progress: { assembleMisses: 0, l4Missed: false, blanked: [] },
    };
  }

  /** The bench before the line runs: the first setup, nothing executed. */
  async benchBefore(card: Card): Promise<BenchResult['before']> {
    return (await this.d.python.bench(card.instance.setups[0], '')).before;
  }

  /** Before and after the learner's own line, on the setup that exposed the miss. */
  benchFor(card: Card, line: string, setupIndex?: number | null): Promise<BenchResult> {
    return this.d.python.bench(card.instance.setups[setupIndex ?? 0] ?? card.instance.setups[0], line);
  }

  async submitL5(card: Card, input: L5Input): Promise<L5Outcome> {
    const { pattern, instance } = card;
    const result = await this.d.python.check({
      setups: instance.setups,
      reference: instance.reference,
      answer: input.answer,
      options: pattern.options,
    });
    if (result.stage === 'note') return { result, effectCorrect: null, help: { kind: 'end' }, reveal: null, noteError: true };

    const effectCorrect = input.effectPicked ? this.gradePick(input.effectPicked, result, card) : null;
    const first = !card.isRetry && card.l5Attempts === 0;
    card.l5Attempts++;
    await this.log(card, {
      level: 'L5',
      first,
      sure: input.sure,
      stuckReason: null,
      effectPicked: input.effectPicked,
      effectCorrect,
      answer: input.answer,
      correct: result.correct,
      stage: result.stage,
      blame: result.blame ?? null,
      setupIndex: result.setup_index ?? null,
      msToFirstKey: input.msToFirstKey,
      msToAnswer: input.msToAnswer,
    });
    if (first) await this.recordFirst(card, result.correct, effectCorrect, result.blame ?? null);

    let help: Help = { kind: 'done' };
    if (!result.correct) {
      if (card.isRetry) help = { kind: 'end' };
      else {
        if (result.blame === 'assemble') card.progress.assembleMisses++;
        help = routeMiss(result.blame, card.progress);
      }
    }
    return { result, effectCorrect, help, reveal: card.isRetry ? instance.reference : null, noteError: false };
  }

  /** `?` at L5: counts as a miss, then one question (verb / assemble / effect) decides the help. */
  async stuck(card: Card, reason: StuckReason, timing: Timing): Promise<{ help: Help; reveal: string | null }> {
    const first = !card.isRetry && card.l5Attempts === 0;
    card.l5Attempts++;
    await this.log(card, {
      level: 'L5',
      first,
      sure: null,
      stuckReason: reason,
      effectPicked: null,
      effectCorrect: null,
      answer: '',
      correct: false,
      stage: 'stuck',
      blame: null,
      setupIndex: null,
      msToFirstKey: timing.msToFirstKey,
      msToAnswer: timing.msToAnswer,
    });
    if (first) await this.recordFirst(card, false, null, null);
    if (card.isRetry) return { help: { kind: 'end' }, reveal: card.instance.reference };
    return { help: routeStuck(reason), reveal: null };
  }

  /** Blank one part of the reference. `want` is a part, or 'rotate' for subject → verb → details → landing. */
  async openL4(card: Card, want: PartName | 'rotate'): Promise<BlankResult | null> {
    const sched = await this.d.store.schedule(card.pattern.id);
    const start = sched?.blankNext ?? 0;
    for (const part of partOrder(want, start, card.progress.blanked)) {
      const blank = await this.d.python.blank(card.instance.reference, part);
      if (!blank) continue;
      card.progress.blanked.push(part);
      if (want === 'rotate' && sched) {
        await this.d.store.putSchedule({ ...sched, blankNext: (PART_ROTATION.indexOf(part) + 1) % PART_ROTATION.length });
      }
      return blank;
    }
    return null;
  }

  /** The filled line is judged by the checker, so every correct spelling of the missing part is accepted. */
  async submitL4(
    card: Card,
    blank: BlankResult,
    typed: string,
    timing: Timing,
    effectPicked: EffectName[] | null,
  ): Promise<{ result: CheckResult; filled: string }> {
    const filled = blank.blanked.replace('____', typed.trim());
    const result = await this.d.python.check({
      setups: card.instance.setups,
      reference: card.instance.reference,
      answer: filled,
      options: card.pattern.options,
    });
    if (!result.correct) card.progress.l4Missed = true;
    await this.log(card, {
      level: 'L4',
      first: false,
      sure: null,
      stuckReason: null,
      effectPicked,
      effectCorrect: effectPicked ? this.gradePick(effectPicked, result, card) : null,
      answer: filled,
      correct: result.correct,
      stage: result.stage,
      blame: result.blame ?? null,
      setupIndex: result.setup_index ?? null,
      msToFirstKey: timing.msToFirstKey,
      msToAnswer: timing.msToAnswer,
    });
    return { result, filled };
  }

  /** The effect prompt: grade the pick, then say the reference's effects in words. The reference line stays hidden. */
  async effectPrompt(card: Card, picked: EffectName[]) {
    const effectCorrect = sameSet(picked, card.refEffects.effects);
    await this.log(card, {
      level: 'prompt',
      first: false,
      sure: null,
      stuckReason: null,
      effectPicked: picked,
      effectCorrect,
      answer: '',
      correct: effectCorrect,
      stage: 'prompt',
      blame: effectCorrect ? null : 'effect',
      setupIndex: null,
      msToFirstKey: null,
      msToAnswer: null,
    });
    return { effectCorrect, words: effectWords(card.refEffects) };
  }

  /** Stuck 1: only the verb of the reference, never the line. */
  async verbHint(card: Card): Promise<string> {
    const verb = (await this.d.python.parts(card.instance.reference)).verb;
    if (!verb) return 'This line has no single verb; it is built straight from its parts.';
    if (verb === '[ ]') return 'The verb is a lookup: square brackets [ ].';
    return `The verb is ${verb}`;
  }

  summary(): Summary {
    return summarise(this.sessionAttempts);
  }

  // ---- internals ----

  private gradePick(picked: string[], result: CheckResult, card: Card): boolean {
    // Graded against the reference's effects, or against the learner's own when the line was correct another way.
    const target = result.correct && result.effects ? result.effects.yours : card.refEffects.effects;
    return sameSet(picked, target);
  }

  private async recordFirst(card: Card, correct: boolean, effectCorrect: boolean | null, blame: string | null) {
    const today = dayKey(this.d.now());
    const sched: Schedule = (await this.d.store.schedule(card.pattern.id)) ?? newSchedule(card.pattern.id, today);
    await this.d.store.putSchedule(
      afterFirstAttempt(sched, {
        correct,
        instanceId: card.instance.id,
        intentIndex: card.intentIndex,
        today,
        effectCorrect,
        blame,
      }),
    );
    if (!correct) {
      this.queue = insertRetry(this.queue, {
        patternId: card.pattern.id,
        kind: 'retry',
        instanceId: card.instance.id,
        format: card.format,
        avoidIntent: card.intentIndex,
      });
    }
  }

  private async log(card: Card, a: Omit<Attempt, 'patternId' | 'instanceId' | 'at' | 'format' | 'intentIndex'>) {
    const row: Attempt = {
      patternId: card.pattern.id,
      instanceId: card.instance.id,
      at: this.d.now().getTime(),
      format: card.format,
      intentIndex: card.intentIndex,
      ...a,
    };
    this.sessionAttempts.push(row);
    await this.d.store.addAttempt(row);
  }
}

/** "should rebind `df`", "should change `fruits` itself": the reference's effects, without the line. */
export function effectWords(e: RefEffects): string[] {
  const words = [
    ...e.rebound.map((n) => `should rebind \`${n}\``),
    ...e.mutated.map((n) => `should change \`${n}\` itself`),
  ];
  if (e.effects.includes('sends_out')) words.push('should send something out (print)');
  return words.length ? words : ["shouldn't change any name"];
}
