// Shapes stored in IndexedDB and read from content/decks/*.json (ARCHITECTURE.md section 9).

export interface Instance {
  id: string;
  role: 'practice' | 'cold';
  intents: string[];
  setups: string[];
  reference: string;
  traps: string[];
}

export interface Pattern {
  id: string;
  kind: 'line';
  deck: string;
  pattern: string;
  rule: string;
  returns: 'new' | 'none_after_mutating' | 'same_after_mutating';
  contrast: string | null;
  requires: string[];
  options: { ignore_order?: boolean };
  distractors: { tile: string; imitates: string }[];
  tiles: string[] | null;
  tags: string[];
  source: string;
  version: number;
  instances: Instance[];
  /** Position in the seed decks; "among unlocked new patterns the order is the deck file's order". */
  order?: number;
}

export interface DeckFile {
  deck: string;
  schemaVersion: number;
  patterns: Pattern[];
}

/** One per pattern. The pilot schedules with fixed gaps; FSRS replaces `dueDay` and `gapIndex` in Phase 2. */
export interface Schedule {
  patternId: string;
  /** Local day (4am boundary) this pattern was first shown, "YYYY-MM-DD". */
  introducedDay: string;
  dueDay: string;
  /** Index into GAPS of the gap the pattern is on. */
  gapIndex: number;
  /** Correct first L5 attempts, ever. */
  correctCount: number;
  /** Correct first attempts in a row; 3 means fluent. */
  fluentStreak: number;
  /** Correct effect picks in a row; 3 turns the gate off. */
  gateStreak: number;
  /** Reviews whose first L5 attempt was a miss; 5 marks the pattern stuck. */
  stuckCount: number;
  recentInstanceIds: string[];
  /** Last intent wording shown per instance, so the same wording never comes twice in a row. */
  lastIntent: Record<string, number>;
  coldUsed: string[];
  /** Where the L4 part rotation continues (subject, verb, details, landing). */
  blankNext: number;
}

export type Format = 'english' | 'notebook' | 'cold';
export type Level = 'L5' | 'L4' | 'prompt';
export type StuckReason = 'verb' | 'assemble' | 'effect';

export interface Attempt {
  id?: number;
  patternId: string;
  instanceId: string;
  /** Milliseconds since the epoch. */
  at: number;
  format: Format;
  level: Level;
  /** True only for the very first L5 attempt of a review (the one scheduling sees). */
  first: boolean;
  /** Enter checks as sure, Shift+Enter as unsure. Null where it doesn't apply. */
  sure: boolean | null;
  stuckReason: StuckReason | null;
  intentIndex: number;
  effectPicked: string[] | null;
  effectCorrect: boolean | null;
  answer: string;
  correct: boolean;
  stage: string;
  blame: string | null;
  setupIndex: number | null;
  msToFirstKey: number | null;
  msToAnswer: number | null;
}

export interface InboxItem {
  id?: number;
  at: number;
  intent: string;
  attempt?: string;
  status: 'new' | 'carded' | 'dropped';
  patternId?: string;
}
