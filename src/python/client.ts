// Typed client for the Python worker. One request runs at a time, so each timer measures one request.
//
// Two clocks (ARCHITECTURE.md section 8): package loading has its own 60 second limit, and the run itself
// gets 5 seconds, covering all of a note's setups. On a timeout the worker is terminated and a fresh one
// started; Pyodide reloads on the next request, which is the accepted cost of not using the interrupt buffer.
import type {
  CheckResult,
  Phase,
  Request,
  RequestType,
  ResultOf,
  WorkerIn,
  WorkerOut,
} from './protocol';

export const TIMED_OUT_MESSAGE = 'Your line ran too long and was stopped.';

export interface WorkerLike {
  postMessage(msg: WorkerIn): void;
  terminate(): void;
  onmessage: ((ev: { data: WorkerOut }) => void) | null;
  onerror: ((ev: { message?: string }) => void) | null;
}

export interface ClientOptions {
  createWorker?: () => WorkerLike;
  loadTimeoutMs?: number;
  checkTimeoutMs?: number;
  validateTimeoutMs?: number;
  /** Called when the Python worker's phase changes, so the bench can show "Loading Python…". */
  onPhase?: (phase: Phase | 'idle') => void;
  /** Called after a timeout or a crash replaced the worker. */
  onRestart?: (reason: 'timeout' | 'restart' | 'crash') => void;
}

export class PythonTimeoutError extends Error {
  constructor(message = TIMED_OUT_MESSAGE) {
    super(message);
    this.name = 'PythonTimeoutError';
  }
}

interface Pending {
  id: number;
  req: Request;
  resolve: (v: unknown) => void;
  reject: (e: Error) => void;
}

const defaultWorker = (): WorkerLike =>
  new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' }) as unknown as WorkerLike;

export class PythonClient {
  private worker: WorkerLike;
  private nextId = 1;
  private queue: Pending[] = [];
  private current: Pending | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private readonly o: Required<Pick<ClientOptions, 'createWorker' | 'loadTimeoutMs' | 'checkTimeoutMs' | 'validateTimeoutMs'>> &
    ClientOptions;

  constructor(options: ClientOptions = {}) {
    this.o = {
      createWorker: defaultWorker,
      loadTimeoutMs: 60_000,
      checkTimeoutMs: 5_000,
      validateTimeoutMs: 15_000,
      ...options,
    };
    this.worker = this.spawn();
  }

  check(req: Omit<Extract<Request, { type: 'check' }>, 'type'>): Promise<CheckResult> {
    return this.send({ type: 'check', ...req }) as Promise<CheckResult>;
  }

  validate(req: Omit<Extract<Request, { type: 'validate' }>, 'type'>): Promise<string[]> {
    return this.send({ type: 'validate', ...req }) as Promise<string[]>;
  }

  parts(line: string): Promise<ResultOf['parts']> {
    return this.send({ type: 'parts', line }) as Promise<ResultOf['parts']>;
  }

  /** Start from a clean interpreter. Called at the start of every session to clear module-level state. */
  restart(): void {
    this.replaceWorker('restart', new Error('The Python worker was restarted.'));
  }

  dispose(): void {
    this.clearTimer();
    this.worker.terminate();
    this.failAll(new Error('The Python client was disposed.'));
  }

  private spawn(): WorkerLike {
    const w = this.o.createWorker();
    w.onmessage = (ev) => this.onMessage(ev.data);
    w.onerror = (ev) => {
      if (this.current) this.replaceWorker('crash', new Error(ev.message || 'The Python worker crashed.'));
    };
    return w;
  }

  private send<T extends RequestType>(req: Extract<Request, { type: T }>): Promise<unknown> {
    return new Promise((resolve, reject) => {
      this.queue.push({ id: this.nextId++, req, resolve, reject });
      this.pump();
    });
  }

  private pump(): void {
    if (this.current || this.queue.length === 0) return;
    const p = this.queue.shift()!;
    this.current = p;
    this.arm(this.o.loadTimeoutMs, 'loading');
    this.worker.postMessage({ ...p.req, id: p.id });
  }

  private onMessage(m: WorkerOut): void {
    const p = this.current;
    if (!p || m.id !== p.id) return;
    if (m.type === 'status') {
      this.o.onPhase?.(m.phase);
      if (m.phase === 'running') this.arm(this.runLimit(p.req), 'running');
      return;
    }
    this.clearTimer();
    this.current = null;
    this.o.onPhase?.('idle');
    if (m.type === 'result') p.resolve(m.result);
    else p.reject(new Error(m.message));
    this.pump();
  }

  private runLimit(req: Request): number {
    return req.type === 'validate' ? this.o.validateTimeoutMs : this.o.checkTimeoutMs;
  }

  private arm(ms: number, phase: Phase): void {
    this.clearTimer();
    this.timer = setTimeout(() => this.onTimeout(phase), ms);
  }

  private clearTimer(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }

  private onTimeout(phase: Phase): void {
    const p = this.current;
    if (!p) return;
    this.current = null;
    this.restartWorker('timeout');
    if (phase === 'running' && p.req.type === 'check') {
      const result: CheckResult = {
        correct: false,
        stage: 'run',
        blame: null,
        messages: [TIMED_OUT_MESSAGE],
        timedOut: true,
      };
      p.resolve(result);
    } else {
      p.reject(
        new PythonTimeoutError(phase === 'loading' ? 'Python took too long to load.' : TIMED_OUT_MESSAGE),
      );
    }
    this.pump();
  }

  /** Replace the worker; the in-flight request and everything queued behind it fail with `err`. */
  private replaceWorker(reason: 'restart' | 'crash', err: Error): void {
    this.failAll(err);
    this.restartWorker(reason);
  }

  private restartWorker(reason: 'timeout' | 'restart' | 'crash'): void {
    this.clearTimer();
    this.worker.terminate();
    this.worker = this.spawn();
    this.o.onPhase?.('idle');
    this.o.onRestart?.(reason);
  }

  private failAll(err: Error): void {
    this.clearTimer();
    const doomed = [...(this.current ? [this.current] : []), ...this.queue];
    this.current = null;
    this.queue = [];
    for (const p of doomed) p.reject(err);
  }
}
