// Messages between client.ts (main thread) and worker.ts (Web Worker). See ARCHITECTURE.md section 8.

export interface CheckOptions {
  ignore_order?: boolean;
}

export type Blame = 'subject' | 'verb' | 'details' | 'landing' | 'effect' | 'assemble' | null;

export interface CheckResult {
  correct: boolean;
  stage: 'assemble' | 'run' | 'compare' | 'note';
  blame?: Blame;
  messages: string[];
  effects?: { reference: string[]; yours: string[] };
  /** "Works, but" advice on a correct answer (section 8); never changes `correct`. */
  style?: string[];
  setup_index?: number;
  /** Set by the client, never by Python: the 5 second limit stopped the line. */
  timedOut?: boolean;
}

export interface PartText {
  text: string | null;
  nested: Sentence | null;
}

export interface Sentence {
  subject: PartText | null;
  verb: string | null;
  details: PartText[];
}

export interface PartsResult extends Sentence {
  landing: { kind: string; text: string | null } | null;
}

export type PartName = 'subject' | 'verb' | 'details' | 'landing';

/** A JSON-safe picture of one object on the bench (checker.bench). */
export type Preview =
  | { kind: 'scalar'; value: string | number | boolean | null; special?: 'nan' | 'inf' | '-inf' }
  | { kind: 'list'; items: Preview[]; more: number }
  | { kind: 'dict'; items: { key: Preview; value: Preview }[]; more: number }
  | { kind: 'dataframe'; shape: [number, number]; columns: string[]; index: Preview[]; rows: Preview[][]; more: number }
  | { kind: 'series'; length: number; items: { index: Preview; value: Preview }[]; more: number }
  | { kind: 'ndarray'; shape: number[]; values: Preview[]; more: number }
  | { kind: 'model'; cls: string; fitted: boolean }
  | { kind: 'other'; text: string };

export interface BenchState {
  names: { name: string; key: string }[];
  objects: { key: string; type: string; preview: Preview; changed: boolean }[];
}

export interface BenchResult {
  before: BenchState;
  after: BenchState;
  error: { type: string; message: string } | null;
  stdout: string;
}

export interface BlankResult {
  blanked: string;
  part: PartName;
  /** The removed text. Held for tests; the UI judges the filled line with the checker, never by comparing this. */
  answer: string;
}

export interface RefEffects {
  effects: string[];
  rebound: string[];
  mutated: string[];
  error: string | null;
}

export type Request =
  | { type: 'check'; setups: string[]; reference: string; answer: string; options?: CheckOptions }
  | { type: 'validate'; setups: string[]; reference: string; traps: string[]; options?: CheckOptions }
  | { type: 'parts'; line: string }
  | { type: 'bench'; setup: string; line: string }
  | { type: 'blank'; line: string; part: PartName }
  | { type: 'effects'; setup: string; reference: string };

export interface ResultOf {
  check: CheckResult;
  validate: string[];
  parts: PartsResult;
  bench: BenchResult;
  blank: BlankResult | null;
  effects: RefEffects;
}

export type RequestType = Request['type'];

export type Phase = 'loading' | 'running';

export type WorkerIn = Request & { id: number };

export type WorkerOut =
  | { id: number; type: 'status'; phase: Phase }
  | { id: number; type: 'result'; result: unknown }
  | { id: number; type: 'error'; message: string };
