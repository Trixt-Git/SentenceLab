// Pilot scheduling: fixed gaps instead of FSRS (ARCHITECTURE.md section 13). Only the first L5 attempt of a review
// reaches this file; fallback levels and the delayed retry are practice and never change the schedule.
import type { Schedule } from '../data/types';
import { addDays } from './dates';

export const GAPS = [1, 3, 7, 14, 30];
export const FLUENT_AT = 3;
export const GATE_OFF_AT = 3;
export const STUCK_AT = 5;

export function newSchedule(patternId: string, today: string): Schedule {
  return {
    patternId,
    introducedDay: today,
    dueDay: today,
    gapIndex: -1,
    correctCount: 0,
    fluentStreak: 0,
    gateStreak: 0,
    stuckCount: 0,
    recentInstanceIds: [],
    lastIntent: {},
    coldUsed: [],
    blankNext: 0,
  };
}

export interface FirstAttempt {
  correct: boolean;
  instanceId: string;
  intentIndex: number;
  today: string;
  /** Null when the gate wasn't shown or couldn't be graded. */
  effectCorrect: boolean | null;
  blame: string | null;
}

export function afterFirstAttempt(s: Schedule, a: FirstAttempt): Schedule {
  const next: Schedule = {
    ...s,
    recentInstanceIds: [...s.recentInstanceIds.filter((id) => id !== a.instanceId), a.instanceId].slice(-12),
    lastIntent: { ...s.lastIntent, [a.instanceId]: a.intentIndex },
  };
  if (a.correct) {
    next.gapIndex = Math.min(s.gapIndex + 1, GAPS.length - 1);
    next.correctCount = s.correctCount + 1;
    next.fluentStreak = s.fluentStreak + 1;
  } else {
    next.gapIndex = 0;
    next.fluentStreak = 0;
    next.stuckCount = s.stuckCount + 1;
  }
  next.dueDay = addDays(a.today, GAPS[next.gapIndex]);
  if (a.effectCorrect !== null) next.gateStreak = a.effectCorrect ? s.gateStreak + 1 : 0;
  // The gate comes back for a pattern after a miss blamed on effect or landing.
  if (!a.correct && (a.blame === 'effect' || a.blame === 'landing')) next.gateStreak = 0;
  return next;
}

export const gateOn = (s?: Schedule) => !s || s.gateStreak < GATE_OFF_AT;
export const isFluent = (s?: Schedule) => !!s && s.fluentStreak >= FLUENT_AT;
export const isStuck = (s?: Schedule) => !!s && s.stuckCount >= STUCK_AT;
