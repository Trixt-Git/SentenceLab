import { describe, expect, it } from 'vitest';
import core from '../../content/decks/core.json';
import pandas from '../../content/decks/pandas.json';
import sklearn from '../../content/decks/sklearn.json';
import { MemoryStore } from '../data/store';
import { decksFromFiles, seedPatterns } from '../data/seed';
import type { DeckFile, Pattern, Schedule } from '../data/types';
import type { BlankResult, CheckResult, PartName } from '../python/protocol';
import { ColdChallenge, coldCandidates, coldOffer } from './cold';
import { addDays, dayKey } from './dates';
import { Engine, effectWords, type EffectName, type PythonApi } from './engine';
import { median, summarise } from './measures';
import { pickFormat, pickInstance, pickIntent } from './pick';
import { buildQueue, insertRetry, type QueueItem } from './queue';
import { partOrder, routeMiss, routeStuck } from './routing';
import { afterFirstAttempt, GAPS, gateOn, isFluent, newSchedule } from './schedule';

const SEED: Pattern[] = decksFromFiles({ core, pandas, sklearn } as unknown as Record<string, DeckFile>);
const byId = (id: string) => SEED.find((p) => p.id === id)!;
const at = (d: number, h = 12) => new Date(2026, 9, 26 + d, h);

/** A stand-in for the Pyodide checker: the reference is right, a few magic strings are wrong in set ways. */
class FakePython implements PythonApi {
  blankable: PartName[] = ['subject', 'verb', 'details', 'landing'];
  async check(req: { reference: string; answer: string }): Promise<CheckResult> {
    const effects = { reference: ['rebinds'], yours: ['rebinds'] };
    if (req.answer === req.reference || req.answer.includes('GOOD')) {
      return { correct: true, stage: 'compare', blame: null, messages: ['Same effects, same result.'], style: [], effects };
    }
    const m = /^BLAME:(\w+)/.exec(req.answer);
    const blame = (m ? m[1] : 'verb') as CheckResult['blame'];
    return {
      correct: false,
      stage: blame === 'assemble' ? 'assemble' : 'compare',
      blame,
      messages: ['nope'],
      effects,
      setup_index: 0,
    };
  }
  async bench() {
    const state = { names: [], objects: [] };
    return { before: state, after: state, error: null, stdout: '' };
  }
  async blank(_line: string, part: PartName): Promise<BlankResult | null> {
    return this.blankable.includes(part) ? { blanked: `____ ${part}`, part, answer: 'x' } : null;
  }
  async effects() {
    return { effects: ['rebinds'], rebound: ['x'], mutated: [], error: null };
  }
  async parts() {
    return { landing: null, subject: null, verb: '.foo', details: [] };
  }
}

async function setup(day = 0, rng = () => 0.99, store = new MemoryStore()) {
  await seedPatterns(store, SEED);
  let now = at(day);
  const python = new FakePython();
  const mk = () => Engine.create({ store, python, now: () => now, rng });
  return { store, python, mk, setNow: (d: Date) => (now = d) };
}

const t = { msToFirstKey: 900, msToAnswer: 3000 };
const answerOf = (card: { instance: { reference: string } }) => card.instance.reference;
const gateAnswer = (c: { refEffects: { effects: string[] } }) => c.refEffects.effects as EffectName[];

describe('seed decks', () => {
  it('holds 21 patterns: 63 practice and 21 cold instances, in deck order', () => {
    expect(SEED).toHaveLength(21);
    const inst = SEED.flatMap((p) => p.instances);
    expect(inst.filter((i) => i.role === 'practice')).toHaveLength(63);
    expect(inst.filter((i) => i.role === 'cold')).toHaveLength(21);
    expect(SEED[0].id).toBe('core-compare');
    expect(SEED.map((p) => p.deck).join()).toMatch(/^(core,)+(pandas,)+(sklearn,?)+$/);
  });

  it('imports once and not again', async () => {
    const store = new MemoryStore();
    expect(await seedPatterns(store, SEED)).toBe(21);
    expect(await seedPatterns(store, SEED)).toBe(0);
    expect(await seedPatterns(store, SEED.map((p) => ({ ...p, version: p.version + 1 })))).toBe(21);
  });
});

describe('days', () => {
  it('a new day starts at 4am', () => {
    expect(dayKey(new Date(2026, 9, 27, 3, 59))).toBe('2026-10-26');
    expect(dayKey(new Date(2026, 9, 27, 4, 0))).toBe('2026-10-27');
    expect(addDays('2026-10-30', 3)).toBe('2026-11-02');
  });
});

describe('fixed gaps', () => {
  const first = (s: Schedule, correct: boolean, over = {}) =>
    afterFirstAttempt(s, { correct, instanceId: 'i', intentIndex: 0, today: '2026-10-26', effectCorrect: null, blame: null, ...over });

  it('walks 1, 3, 7, 14, 30 days on correct first attempts and stays at 30', () => {
    let s = newSchedule('p', '2026-10-26');
    const days: string[] = [];
    for (let n = 0; n < 6; n++) {
      s = first(s, true);
      days.push(s.dueDay);
    }
    expect(days).toEqual(GAPS.concat(30).map((g) => addDays('2026-10-26', g)));
  });

  it('a miss sends the pattern back to 1 day', () => {
    let s = newSchedule('p', '2026-10-26');
    for (let n = 0; n < 4; n++) s = first(s, true);
    expect(s.dueDay).toBe(addDays('2026-10-26', 14));
    s = first(s, false);
    expect(s.dueDay).toBe(addDays('2026-10-26', 1));
    expect(s.gapIndex).toBe(0);
    expect(s.stuckCount).toBe(1);
  });
});

describe('the effect gate fades and returns', () => {
  const first = (s: Schedule, over: object) =>
    afterFirstAttempt(s, { correct: true, instanceId: 'i', intentIndex: 0, today: '2026-10-26', effectCorrect: true, blame: null, ...over });

  it('is on for a new pattern and off after 3 correct picks in a row', () => {
    let s = newSchedule('p', '2026-10-26');
    expect(gateOn(undefined)).toBe(true);
    for (let n = 0; n < 2; n++) s = first(s, {});
    expect(gateOn(s)).toBe(true);
    s = first(s, {});
    expect(gateOn(s)).toBe(false);
  });

  it('a wrong pick resets the streak', () => {
    let s = newSchedule('p', '2026-10-26');
    s = first(first(s, {}), {});
    s = first(s, { effectCorrect: false });
    expect(s.gateStreak).toBe(0);
  });

  it('returns after a miss blamed on effect or landing, but not on a verb', () => {
    let s = newSchedule('p', '2026-10-26');
    for (let n = 0; n < 3; n++) s = first(s, {});
    expect(gateOn(s)).toBe(false);
    expect(gateOn(first(s, { correct: false, effectCorrect: null, blame: 'verb' }))).toBe(false);
    expect(gateOn(first(s, { correct: false, effectCorrect: null, blame: 'effect' }))).toBe(true);
    expect(gateOn(first(s, { correct: false, effectCorrect: null, blame: 'landing' }))).toBe(true);
  });

  it('fluent after 3 correct first attempts in a row; any miss brings the framework back', () => {
    let s = newSchedule('p', '2026-10-26');
    for (let n = 0; n < 3; n++) s = first(s, { effectCorrect: null });
    expect(isFluent(s)).toBe(true);
    expect(isFluent(first(s, { correct: false, effectCorrect: null }))).toBe(false);
  });
});

describe('instances, wordings and formats', () => {
  it('a new pattern stays on its first instance until it is right on a first attempt', () => {
    const p = byId('pd-newcol');
    const s = { ...newSchedule(p.id, '2026-10-26'), recentInstanceIds: [p.instances[0].id] };
    expect(pickInstance(p, undefined).id).toBe(p.instances[0].id);
    expect(pickInstance(p, s).id).toBe(p.instances[0].id);
  });

  it('then rotates through the practice instances, never twice in a row and never to a cold one', () => {
    const p = byId('pd-newcol');
    let s = { ...newSchedule(p.id, '2026-10-26'), correctCount: 1 };
    const seen: string[] = [];
    for (let n = 0; n < 9; n++) {
      const inst = pickInstance(p, s);
      seen.push(inst.id);
      s = afterFirstAttempt(s, { correct: true, instanceId: inst.id, intentIndex: 0, today: '2026-10-26', effectCorrect: null, blame: null });
    }
    expect(seen.every((id, i) => i === 0 || id !== seen[i - 1])).toBe(true);
    expect(new Set(seen).size).toBe(3);
    expect(seen.some((id) => id.endsWith('cold'))).toBe(false);
  });

  it('never repeats a wording for the same instance, nor the wording that was missed', () => {
    const inst = byId('core-compare').instances[0];
    let s = newSchedule('core-compare', '2026-10-26');
    const used: number[] = [];
    for (let n = 0; n < 5; n++) {
      const idx = pickIntent(inst, s);
      used.push(idx);
      s = { ...s, lastIntent: { [inst.id]: idx } };
    }
    expect(used.every((x, i) => i === 0 || x !== used[i - 1])).toBe(true);
    expect(pickIntent(inst, { ...s, lastIntent: {} }, 0)).not.toBe(0);
  });

  it('notebook format needs 2 correct first attempts, then shows about one card in four', () => {
    const s = newSchedule('p', '2026-10-26');
    expect(pickFormat(s, () => 0)).toBe('english');
    expect(pickFormat({ ...s, correctCount: 2 }, () => 0.1)).toBe('notebook');
    expect(pickFormat({ ...s, correctCount: 2 }, () => 0.5)).toBe('english');
  });
});

describe('building a session', () => {
  it('starts with at most 5 new patterns and only the ones with no prerequisites', () => {
    const q = buildQueue(SEED, [], '2026-10-26');
    expect(q).toHaveLength(5);
    expect(q.every((i) => i.kind === 'new')).toBe(true);
    for (const i of q) expect(byId(i.patternId).requires).toEqual([]);
    expect(q.map((i) => i.patternId)).toEqual(SEED.filter((p) => !p.requires.length).slice(0, 5).map((p) => p.id));
  });

  it('unlocks a pattern only after every required one has a correct first attempt', () => {
    const asScheduled = (id: string, correctCount: number): Schedule => ({ ...newSchedule(id, '2026-10-20'), correctCount, dueDay: '2099-01-01' });
    const none = buildQueue(SEED, [asScheduled('core-compare', 0)], '2026-10-26', { newPerDay: 50 });
    expect(none.map((i) => i.patternId)).not.toContain('pd-filter');
    const some = buildQueue(SEED, [asScheduled('core-compare', 1)], '2026-10-26', { newPerDay: 50 });
    expect(some.map((i) => i.patternId)).toContain('pd-filter');
    expect(some.map((i) => i.patternId)).not.toContain('pd-and');
  });

  it('puts due reviews first, oldest first, and counts what was introduced today', () => {
    const due = (id: string, day: string): Schedule => ({ ...newSchedule(id, '2026-10-20'), dueDay: day, correctCount: 1 });
    const q = buildQueue(SEED, [due('core-len', '2026-10-25'), due('core-pop', '2026-10-24')], '2026-10-26');
    expect(q.slice(0, 2).map((i) => i.patternId)).toEqual(['core-pop', 'core-len']);
    expect(q[0].kind).toBe('review');
    const introduced = { ...newSchedule('core-comp', '2026-10-26'), dueDay: '2026-10-27' };
    const q2 = buildQueue(SEED, [introduced, ...Array.from({ length: 4 }, (_, n) => ({ ...newSchedule(`x${n}`, '2026-10-26'), dueDay: '2099-01-01' }))], '2026-10-26');
    expect(q2.filter((i) => i.kind === 'new')).toHaveLength(0);
  });

  it('caps a session at 20 cards', () => {
    const many = SEED.slice(0, 20).map((p) => ({ ...newSchedule(p.id, '2026-10-01'), dueDay: '2026-10-02', correctCount: 1 }));
    expect(buildQueue(SEED, many, '2026-10-26', { newPerDay: 5, sessionSize: 20 })).toHaveLength(20);
    expect(buildQueue(SEED, many, '2026-10-26', { sessionSize: 8 })).toHaveLength(8);
  });

  it('puts a retry 5 cards later, or last when fewer remain', () => {
    const q = Array.from({ length: 8 }, (_, n): QueueItem => ({ patternId: `p${n}`, kind: 'review' }));
    const retry: QueueItem = { patternId: 'r', kind: 'retry' };
    expect(insertRetry(q, retry).findIndex((i) => i.kind === 'retry')).toBe(5);
    expect(insertRetry(q.slice(0, 3), retry).at(-1)).toBe(retry);
    expect(insertRetry([], retry)).toEqual([retry]);
  });
});

describe('help after a miss in the pilot (section 13 table)', () => {
  const p = { assembleMisses: 1, l4Missed: false, blanked: [] as PartName[] };

  it('routes each blame exactly as the table says', () => {
    expect(routeMiss('assemble', p)).toEqual({ kind: 'fix' });
    expect(routeMiss('assemble', { ...p, assembleMisses: 2 })).toEqual({ kind: 'l4', part: 'rotate' });
    expect(routeMiss('verb', p)).toEqual({ kind: 'l4', part: 'verb' });
    expect(routeMiss('details', p)).toEqual({ kind: 'l4', part: 'details' });
    expect(routeMiss('subject', p)).toEqual({ kind: 'l4', part: 'subject' });
    expect(routeMiss('landing', p)).toEqual({ kind: 'l4', part: 'landing' });
    expect(routeMiss('effect', p)).toEqual({ kind: 'effect-prompt', then: 'l4-verb' });
    expect(routeMiss(null, p)).toEqual({ kind: 'l4', part: 'rotate' });
  });

  it('routes each stuck reason exactly as the table says', () => {
    expect(routeStuck('verb')).toEqual({ kind: 'verb-hint' });
    expect(routeStuck('assemble')).toEqual({ kind: 'l4', part: 'rotate' });
    expect(routeStuck('effect')).toEqual({ kind: 'effect-prompt', then: 'l5' });
  });

  it('rotates subject, verb, details, landing, and a second L4 blanks a different part', () => {
    expect(partOrder('rotate', 0, [])).toEqual(['subject', 'verb', 'details', 'landing']);
    expect(partOrder('rotate', 2, [])[0]).toBe('details');
    expect(partOrder('rotate', 0, ['subject'])[0]).toBe('verb');
    expect(partOrder('landing', 0, [])[0]).toBe('landing');
    expect(partOrder('rotate', 0, ['subject', 'verb', 'details', 'landing'])).toHaveLength(4);
  });

  it('says the reference effects in words and never the line', () => {
    expect(effectWords({ effects: ['rebinds'], rebound: ['df'], mutated: [], error: null })).toEqual(['should rebind `df`']);
    expect(effectWords({ effects: ['mutates'], rebound: [], mutated: ['fruits'], error: null })).toEqual(['should change `fruits` itself']);
    expect(effectWords({ effects: ['nothing'], rebound: [], mutated: [], error: null })).toEqual(["shouldn't change any name"]);
  });
});

describe('a session', () => {
  it('first card is the first unlocked pattern; a right answer schedules it and queues no retry', async () => {
    const { mk, store } = await setup();
    const e = await mk();
    const card = (await e.nextCard())!;
    expect(card.pattern.id).toBe('core-compare');
    expect(card.instance.id).toBe(card.pattern.instances[0].id);
    expect(card.gate).toBe(true);
    const out = await e.submitL5(card, { answer: answerOf(card), effectPicked: gateAnswer(card), sure: true, ...t });
    expect(out.result.correct).toBe(true);
    expect(out.effectCorrect).toBe(true);
    expect(out.help).toEqual({ kind: 'done' });
    expect(e.cardsLeft).toBe(4);
    const s = (await store.schedule('core-compare'))!;
    expect(s.dueDay).toBe(addDays('2026-10-26', 1));
    expect(s.correctCount).toBe(1);
    expect(s.gateStreak).toBe(1);
  });

  it('a miss goes to L4 for a verb blame, schedules it back to 1 day, and queues a retry 5 cards later', async () => {
    const { mk, store } = await setup();
    const e = await mk();
    const card = (await e.nextCard())!;
    const out = await e.submitL5(card, { answer: 'BLAME:verb', effectPicked: gateAnswer(card), sure: true, ...t });
    expect(out.help).toEqual({ kind: 'l4', part: 'verb' });
    expect(out.reveal).toBeNull();
    expect((await store.schedule('core-compare'))!.gapIndex).toBe(0);
    expect(e.cardsLeft).toBe(4 + 1);
    // 4 other new patterns remain; the retry is last because fewer than 5 remain.
    const ids: string[] = [];
    for (let n = 0; n < 5; n++) ids.push((await e.nextCard())!.pattern.id);
    expect(ids.at(-1)).toBe('core-compare');
    expect(ids.slice(0, 4)).not.toContain('core-compare');
  });

  it('the retry is the same instance, another wording, a real L5, and never touches the schedule', async () => {
    const { mk, store } = await setup();
    const e = await mk();
    const first = (await e.nextCard())!;
    await e.submitL5(first, { answer: 'BLAME:details', effectPicked: gateAnswer(first), sure: true, ...t });
    const before = (await store.schedule('core-compare'))!;
    let retry = (await e.nextCard())!;
    while (!retry.isRetry) retry = (await e.nextCard())!;
    expect(retry.instance.id).toBe(first.instance.id);
    expect(retry.intentIndex).not.toBe(first.intentIndex);
    const out = await e.submitL5(retry, { answer: answerOf(retry), effectPicked: gateAnswer(retry), sure: true, ...t });
    expect(out.result.correct).toBe(true);
    expect(out.reveal).toBe(first.instance.reference);
    const after = (await store.schedule('core-compare'))!;
    expect({ ...after, lastIntent: {} }).toEqual({ ...before, lastIntent: {} });
    expect(e.sessionAttempts.map((a) => a.first)).toEqual([true, false]);
  });

  it('a wrong retry reveals the reference and ends the card; nothing loops', async () => {
    const { mk } = await setup();
    const e = await mk();
    const first = (await e.nextCard())!;
    await e.submitL5(first, { answer: 'BLAME:verb', effectPicked: null, sure: true, ...t });
    let retry = (await e.nextCard())!;
    while (!retry.isRetry) retry = (await e.nextCard())!;
    const out = await e.submitL5(retry, { answer: 'BLAME:verb', effectPicked: null, sure: true, ...t });
    expect(out.help).toEqual({ kind: 'end' });
    expect(out.reveal).toBe(retry.instance.reference);
    expect(e.cardsLeft).toBe(0);
  });

  it('a syntax miss gets one fix-it attempt, and a second goes to L4 with the rotation', async () => {
    const { mk } = await setup();
    const e = await mk();
    const card = (await e.nextCard())!;
    const one = await e.submitL5(card, { answer: 'BLAME:assemble', effectPicked: null, sure: true, ...t });
    expect(one.help).toEqual({ kind: 'fix' });
    const two = await e.submitL5(card, { answer: 'BLAME:assemble', effectPicked: null, sure: true, ...t });
    expect(two.help).toEqual({ kind: 'l4', part: 'rotate' });
    const flags = e.sessionAttempts.map((a) => a.first);
    expect(flags).toEqual([true, false]);
  });

  it('a fix-it that works ends the card, but the first miss still queued its retry', async () => {
    const { mk, store } = await setup();
    const e = await mk();
    const card = (await e.nextCard())!;
    await e.submitL5(card, { answer: 'BLAME:assemble', effectPicked: null, sure: true, ...t });
    const fixed = await e.submitL5(card, { answer: answerOf(card), effectPicked: null, sure: true, ...t });
    expect(fixed.help).toEqual({ kind: 'done' });
    expect((await store.schedule('core-compare'))!.gapIndex).toBe(0);
    expect(e.cardsLeft).toBe(5);
  });

  it('stuck counts as a miss, logs its reason, routes by reason, and reveals nothing', async () => {
    const { mk, store } = await setup();
    const e = await mk();
    const card = (await e.nextCard())!;
    const res = await e.stuck(card, 'verb', t);
    expect(res).toEqual({ help: { kind: 'verb-hint' }, reveal: null });
    expect((await store.schedule('core-compare'))!.gapIndex).toBe(0);
    expect(e.sessionAttempts[0]).toMatchObject({ stuckReason: 'verb', first: true, correct: false, stage: 'stuck' });
    expect((await e.stuck(card, 'effect', t)).help).toEqual({ kind: 'effect-prompt', then: 'l5' });
    expect((await e.stuck(card, 'assemble', t)).help).toEqual({ kind: 'l4', part: 'rotate' });
    expect(e.sessionAttempts.filter((a) => a.first)).toHaveLength(1);
  });

  it('L4 blanks the part, judges the filled line with the checker, and logs level L4', async () => {
    const { mk } = await setup();
    const e = await mk();
    const card = (await e.nextCard())!;
    const blank = (await e.openL4(card, 'verb'))!;
    expect(blank.part).toBe('verb');
    const ok = await e.submitL4(card, blank, 'GOOD', t, null);
    expect(ok.filled).toBe('____ verb'.replace('____', 'GOOD'));
    expect(ok.result.correct).toBe(true);
    const bad = await e.submitL4(card, blank, 'wrong', t, null);
    expect(bad.result.correct).toBe(false);
    expect(card.progress.l4Missed).toBe(true);
    expect(e.sessionAttempts.map((a) => a.level)).toEqual(['L4', 'L4']);
  });

  it('skips a part the line does not have and moves on in the rotation', async () => {
    const { mk, python } = await setup();
    python.blankable = ['verb'];
    const e = await mk();
    const card = (await e.nextCard())!;
    expect((await e.openL4(card, 'landing'))!.part).toBe('verb');
    python.blankable = [];
    expect(await e.openL4(card, 'rotate')).toBeNull();
  });

  it('a second L4 on one card blanks a different part', async () => {
    const { mk } = await setup();
    const e = await mk();
    const card = (await e.nextCard())!;
    const a = (await e.openL4(card, 'rotate'))!;
    const b = (await e.openL4(card, 'rotate'))!;
    expect(a.part).not.toBe(b.part);
  });

  it('the effect prompt grades the pick, logs a miss against effect, and never reveals the line', async () => {
    const { mk } = await setup();
    const e = await mk();
    const card = (await e.nextCard())!;
    const wrong = await e.effectPrompt(card, ['mutates']);
    expect(wrong.effectCorrect).toBe(false);
    expect(wrong.words).toEqual(['should rebind `x`']);
    expect(JSON.stringify(wrong)).not.toContain(card.instance.reference);
    expect(e.sessionAttempts[0]).toMatchObject({ level: 'prompt', blame: 'effect', effectCorrect: false });
    expect((await e.effectPrompt(card, ['rebinds'])).effectCorrect).toBe(true);
  });

  it('a broken card is not the learner\'s miss: nothing is logged or scheduled', async () => {
    const { mk, python, store } = await setup();
    python.check = async () => ({ correct: false, stage: 'note', messages: ["The note's setup fails"] });
    const e = await mk();
    const card = (await e.nextCard())!;
    const out = await e.submitL5(card, { answer: 'x', effectPicked: null, sure: true, ...t });
    expect(out.noteError).toBe(true);
    expect(e.sessionAttempts).toHaveLength(0);
    expect(await store.schedule(card.pattern.id)).toBeUndefined();
  });

  it('the gate stops after 3 correct picks and returns after a landing miss', async () => {
    const store = new MemoryStore();
    const { mk, setNow } = await setup(0, () => 0.99, store);
    const id = 'core-compare';
    const run = async (day: number, answer: (c: { instance: { reference: string } }) => string, pick: boolean) => {
      setNow(at(day));
      const e = await mk();
      let c = await e.nextCard();
      while (c && c.pattern.id !== id) c = await e.nextCard();
      const gate = c!.gate;
      await e.submitL5(c!, { answer: answer(c!), effectPicked: pick ? gateAnswer(c!) : null, sure: true, ...t });
      return gate;
    };
    const gates: boolean[] = [];
    for (let d = 0; d < 4; d++) gates.push(await run(d * 40, answerOf, true));
    expect(gates).toEqual([true, true, true, false]);
    await run(200, () => 'BLAME:landing', false);
    expect(await run(300, answerOf, true)).toBe(true);
  });

  it('runs end to end over many days: all 21 patterns introduced, 5 a day at most, instances rotate', async () => {
    const store = new MemoryStore();
    const { mk, setNow } = await setup(0, () => 0.99, store);
    const shownByPattern = new Map<string, string[]>();
    let introduced = 0;
    for (let d = 0; d < 40; d++) {
      setNow(at(d));
      const e = await mk();
      const before = (await store.schedules()).length;
      let c;
      while ((c = await e.nextCard())) {
        await e.submitL5(c, { answer: answerOf(c), effectPicked: c.gate ? gateAnswer(c) : null, sure: true, ...t });
        const arr = shownByPattern.get(c.pattern.id) ?? [];
        arr.push(c.instance.id);
        shownByPattern.set(c.pattern.id, arr);
      }
      const added = (await store.schedules()).length - before;
      expect(added).toBeLessThanOrEqual(5);
      introduced += added;
    }
    expect(introduced).toBe(21);
    for (const [, ids] of shownByPattern) {
      const practice = ids.filter((_, i) => i > 0);
      expect(practice.every((id, i) => i === 0 || id !== practice[i - 1])).toBe(true);
      expect(ids.some((id) => id.endsWith('cold'))).toBe(false);
    }
    const multi = [...shownByPattern.values()].filter((ids) => new Set(ids).size === 3);
    expect(multi.length).toBeGreaterThan(10);
  });

  it('is deterministic about requires inside a session: nothing unlocks mid-session', async () => {
    const { mk } = await setup();
    const e = await mk();
    const ids: string[] = [];
    let c;
    while ((c = await e.nextCard())) {
      ids.push(c.pattern.id);
      await e.submitL5(c, { answer: answerOf(c), effectPicked: null, sure: true, ...t });
    }
    expect(ids).not.toContain('pd-filter');
  });
});

describe('measures', () => {
  it('computes first-try correctness, median start time, stuck reasons and what was missed most', async () => {
    const { mk } = await setup();
    const e = await mk();
    const c1 = (await e.nextCard())!;
    await e.submitL5(c1, { answer: answerOf(c1), effectPicked: gateAnswer(c1), sure: true, msToFirstKey: 1000, msToAnswer: 2000 });
    const c2 = (await e.nextCard())!;
    await e.submitL5(c2, { answer: 'BLAME:landing', effectPicked: ['mutates'], sure: true, msToFirstKey: 3000, msToAnswer: 4000 });
    const c3 = (await e.nextCard())!;
    await e.stuck(c3, 'effect', { msToFirstKey: null, msToAnswer: 500 });
    const s = e.summary();
    expect(s.linesAttempted).toBe(3);
    expect(s.firstTryCorrect).toBe(1);
    expect(s.medianSecondsToFirstKey).toBe(2);
    expect(s.stuck).toEqual({ verb: 0, assemble: 0, effect: 1 });
    expect(['landing', 'effect', 'stuck: effect']).toContain(s.missedMost);
  });

  it('median handles empty, odd and even lists; an empty session has no median', () => {
    expect(median([])).toBeNull();
    expect(median([3, 1, 2])).toBe(2);
    expect(median([4, 1, 2, 3])).toBe(2.5);
    expect(summarise([])).toEqual({ linesAttempted: 0, firstTryCorrect: 0, medianSecondsToFirstKey: null, missedMost: null, stuck: { verb: 0, assemble: 0, effect: 0 } });
  });
});

describe('weekly cold challenge', () => {
  async function withProgress(correct: Record<string, number>) {
    const ctx = await setup();
    for (const [id, n] of Object.entries(correct)) {
      await ctx.store.putSchedule({ ...newSchedule(id, '2026-10-01'), correctCount: n, dueDay: '2099-01-01' });
    }
    return ctx;
  }

  it('only patterns with 2 correct first attempts are eligible, one unused cold instance each', async () => {
    const { store } = await withProgress({ 'core-len': 2, 'core-pop': 1, 'core-comp': 5 });
    const c = coldCandidates(await store.patterns(), await store.schedules());
    expect(c.map((x) => x.pattern.id).sort()).toEqual(['core-comp', 'core-len']);
    expect(c.every((x) => x.instance.role === 'cold')).toBe(true);
  });

  it('is offered weekly, never when nothing is eligible, and never forced', async () => {
    const { store } = await withProgress({ 'core-len': 2 });
    expect(await coldOffer(store, at(0))).toBe(true);
    await store.setSetting('lastColdAt', at(0).getTime());
    expect(await coldOffer(store, at(3))).toBe(false);
    expect(await coldOffer(store, at(7))).toBe(true);
    expect(await coldOffer(new MemoryStore(), at(0))).toBe(false);
  });

  it('asks up to 4, uses each cold instance once, leaves the schedule alone, and records the score', async () => {
    const { store, python } = await withProgress({ 'core-len': 2, 'core-pop': 2, 'core-comp': 2, 'core-augadd': 2, 'core-set': 2 });
    const before = (await store.schedules()).map((s) => s.dueDay);
    const run = async () => {
      const cold = await ColdChallenge.create({ store, python, now: () => at(0), rng: () => 0.3 });
      const asked = cold.items.length;
      while (cold.current) {
        await cold.submit(cold.current.instance.reference, t);
        cold.advance();
      }
      return { asked, score: await cold.finish(), cold };
    };
    const first = await run();
    expect(first.asked).toBe(4);
    expect(first.score).toEqual({ correct: 4, total: 4 });
    const second = await run();
    expect(second.asked).toBe(1);
    const third = await ColdChallenge.create({ store, python, now: () => at(0), rng: () => 0.3 });
    expect(third.items).toHaveLength(0);
    expect((await store.schedules()).map((s) => s.dueDay)).toEqual(before);
    const attempts = await store.attempts();
    expect(attempts.every((a) => a.format === 'cold' && a.first)).toBe(true);
    expect(new Set(attempts.map((a) => a.instanceId)).size).toBe(5);
    expect(summarise(attempts).linesAttempted).toBe(0);
  });

  it('counts a wrong answer and says why, with no retry', async () => {
    const { store, python } = await withProgress({ 'core-len': 2 });
    const cold = await ColdChallenge.create({ store, python, now: () => at(0), rng: () => 0 });
    const r = await cold.submit('BLAME:verb', t);
    expect(r.correct).toBe(false);
    expect(r.messages.length).toBeGreaterThan(0);
    expect(cold.advance()).toBe(false);
    expect(await cold.finish()).toEqual({ correct: 0, total: 1 });
  });
});
