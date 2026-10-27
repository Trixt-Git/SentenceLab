// Which instance, which wording and which format a card uses (ARCHITECTURE.md section 5).
import type { Instance, Pattern, Schedule } from '../data/types';

export const NOTEBOOK_AT = 2;
export const NOTEBOOK_CHANCE = 0.25;

const practice = (p: Pattern) => p.instances.filter((i) => i.role === 'practice');

/** A new pattern stays on its first instance until it has been right on a first attempt; after that, the least
 * recently seen practice instance, so the same line never comes twice in a row. Cold instances are never used here. */
export function pickInstance(p: Pattern, s?: Schedule): Instance {
  const pool = practice(p);
  if (!s || s.correctCount === 0) return pool[0];
  const seen = (i: Instance) => s.recentInstanceIds.indexOf(i.id);
  return [...pool].sort((a, b) => seen(a) - seen(b))[0];
}

/** The next wording for an instance, never the one shown last time, and never `avoid` (the wording of the miss). */
export function pickIntent(inst: Instance, s?: Schedule, avoid?: number): number {
  const n = inst.intents.length;
  const last = s?.lastIntent[inst.id];
  let idx = last === undefined ? 0 : (last + 1) % n;
  if (avoid !== undefined && idx === avoid) idx = (idx + 1) % n;
  return idx;
}

/** After 2 correct first attempts, about one review in four is shown as a small notebook cell. */
export function pickFormat(s: Schedule | undefined, rng: () => number): 'english' | 'notebook' {
  return s && s.correctCount >= NOTEBOOK_AT && rng() < NOTEBOOK_CHANCE ? 'notebook' : 'english';
}
