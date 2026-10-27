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

export type Request =
  | { type: 'check'; setups: string[]; reference: string; answer: string; options?: CheckOptions }
  | { type: 'validate'; setups: string[]; reference: string; traps: string[]; options?: CheckOptions }
  | { type: 'parts'; line: string };

export interface ResultOf {
  check: CheckResult;
  validate: string[];
  parts: PartsResult;
}

export type RequestType = Request['type'];

export type Phase = 'loading' | 'running';

export type WorkerIn = Request & { id: number };

export type WorkerOut =
  | { id: number; type: 'status'; phase: Phase }
  | { id: number; type: 'result'; result: unknown }
  | { id: number; type: 'error'; message: string };
