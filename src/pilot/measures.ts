// The pilot's measures (ARCHITECTURE.md section 13): first-try correctness, median time to first keystroke,
// stuck presses by reason, and the cold-challenge score. Information only: no score against a target.
import type { Attempt, StuckReason } from '../data/types';

export interface Summary {
  linesAttempted: number;
  firstTryCorrect: number;
  medianSecondsToFirstKey: number | null;
  /** The part or effect missed most among first attempts, e.g. "verb", "landing", "effect". */
  missedMost: string | null;
  stuck: Record<StuckReason, number>;
}

export interface ColdScore {
  correct: number;
  total: number;
}

export function median(xs: number[]): number | null {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function summarise(attempts: Attempt[]): Summary {
  const firsts = attempts.filter((a) => a.first && a.format !== 'cold');
  const tally = new Map<string, number>();
  const bump = (k: string) => tally.set(k, (tally.get(k) ?? 0) + 1);
  for (const a of firsts) {
    if (!a.correct) bump(a.blame ?? (a.stage === 'stuck' ? `stuck: ${a.stuckReason}` : 'value'));
    if (a.effectCorrect === false) bump('effect');
  }
  const top = [...tally.entries()].sort((a, b) => b[1] - a[1])[0];
  const stuck: Summary['stuck'] = { verb: 0, assemble: 0, effect: 0 };
  for (const a of attempts) if (a.stuckReason && a.format !== 'cold') stuck[a.stuckReason]++;
  const keys = firsts.map((a) => a.msToFirstKey).filter((x): x is number => x !== null);
  const m = median(keys);
  return {
    linesAttempted: firsts.length,
    firstTryCorrect: firsts.filter((a) => a.correct).length,
    medianSecondsToFirstKey: m === null ? null : Math.round(m / 100) / 10,
    missedMost: top ? top[0] : null,
    stuck,
  };
}

export function coldScore(attempts: Attempt[]): ColdScore {
  const cold = attempts.filter((a) => a.format === 'cold');
  return { correct: cold.filter((a) => a.correct).length, total: cold.length };
}
