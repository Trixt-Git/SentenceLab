// Weekly cold challenge (ARCHITECTURE.md section 7): up to 4 unseen cold instances from patterns that already have
// 2 correct first attempts, at L5, with no effect gate, no help, no retry, no diagram and nothing sent to the
// schedule. Each cold instance is used once and then retired. Results feed only the Goal 1 finish line.
import type { Store } from '../data/store';
import type { Attempt, Instance, Pattern, Schedule } from '../data/types';
import { coldScore, type ColdScore } from './measures';
import type { PythonApi, Timing } from './engine';
import type { CheckResult } from '../python/protocol';

export const COLD_EVERY_DAYS = 7;
export const COLD_SIZE = 4;
export const COLD_ELIGIBLE_AT = 2;
const LAST_COLD_KEY = 'lastColdAt';

export interface ColdItem {
  pattern: Pattern;
  instance: Instance;
  intentIndex: number;
}

export function coldCandidates(patterns: Pattern[], schedules: Schedule[]): { pattern: Pattern; instance: Instance }[] {
  const byId = new Map(schedules.map((s) => [s.patternId, s]));
  const out: { pattern: Pattern; instance: Instance }[] = [];
  for (const pattern of patterns) {
    const s = byId.get(pattern.id);
    if (!s || s.correctCount < COLD_ELIGIBLE_AT) continue;
    const unused = pattern.instances.find((i) => i.role === 'cold' && !s.coldUsed.includes(i.id));
    if (unused) out.push({ pattern, instance: unused });
  }
  return out;
}

/** Offered once a week, never forced, and only when there is something to ask. */
export async function coldOffer(store: Store, now: Date): Promise<boolean> {
  const last = await store.getSetting<number>(LAST_COLD_KEY);
  if (last !== undefined && now.getTime() - last < COLD_EVERY_DAYS * 86_400_000) return false;
  return coldCandidates(await store.patterns(), await store.schedules()).length > 0;
}

export class ColdChallenge {
  readonly attempts: Attempt[] = [];
  private i = 0;

  private constructor(
    private d: { store: Store; python: PythonApi; now: () => Date },
    readonly items: ColdItem[],
  ) {}

  static async create(d: { store: Store; python: PythonApi; now: () => Date; rng: () => number }) {
    const pool = coldCandidates(await d.store.patterns(), await d.store.schedules());
    const shuffled = pool
      .map((c) => ({ c, k: d.rng() }))
      .sort((a, b) => a.k - b.k)
      .map(({ c }) => c)
      .slice(0, COLD_SIZE);
    const items = shuffled.map((c) => ({ ...c, intentIndex: Math.floor(d.rng() * c.instance.intents.length) }));
    return new ColdChallenge(d, items);
  }

  get current(): ColdItem | null {
    return this.items[this.i] ?? null;
  }
  get cardsLeft(): number {
    return Math.max(0, this.items.length - this.i - 1);
  }

  /** Checks one answer, retires the instance and moves on. Returns the checker's feedback; nothing more is shown. */
  async submit(answer: string, timing: Timing): Promise<CheckResult> {
    const item = this.current!;
    const result = await this.d.python.check({
      setups: item.instance.setups,
      reference: item.instance.reference,
      answer,
      options: item.pattern.options,
    });
    if (result.stage === 'note') return result;
    const row: Attempt = {
      patternId: item.pattern.id,
      instanceId: item.instance.id,
      at: this.d.now().getTime(),
      format: 'cold',
      level: 'L5',
      first: true,
      sure: null,
      stuckReason: null,
      intentIndex: item.intentIndex,
      effectPicked: null,
      effectCorrect: null,
      answer,
      correct: result.correct,
      stage: result.stage,
      blame: result.blame ?? null,
      setupIndex: result.setup_index ?? null,
      msToFirstKey: timing.msToFirstKey,
      msToAnswer: timing.msToAnswer,
    };
    this.attempts.push(row);
    await this.d.store.addAttempt(row);
    const s = await this.d.store.schedule(item.pattern.id);
    if (s) await this.d.store.putSchedule({ ...s, coldUsed: [...s.coldUsed, item.instance.id] });
    return result;
  }

  advance(): boolean {
    this.i++;
    return this.current !== null;
  }

  async finish(): Promise<ColdScore> {
    await this.d.store.setSetting(LAST_COLD_KEY, this.d.now().getTime());
    return coldScore(this.attempts);
  }
}
