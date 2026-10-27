import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PythonClient, PythonTimeoutError, TIMED_OUT_MESSAGE, type WorkerLike } from './client';
import type { WorkerIn, WorkerOut } from './protocol';

class FakeWorker implements WorkerLike {
  static all: FakeWorker[] = [];
  onmessage: WorkerLike['onmessage'] = null;
  onerror: WorkerLike['onerror'] = null;
  received: WorkerIn[] = [];
  terminated = false;
  constructor() {
    FakeWorker.all.push(this);
  }
  postMessage(msg: WorkerIn) {
    this.received.push(msg);
  }
  terminate() {
    this.terminated = true;
  }
  say(m: WorkerOut) {
    this.onmessage?.({ data: m });
  }
}

const checkReq = { setups: ['x = 1', 'x = 2'], reference: 'y = x', answer: 'y = x' };
const ok = { correct: true, stage: 'compare', messages: [] };

describe('PythonClient', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeWorker.all = [];
  });
  afterEach(() => vi.useRealTimers());

  const make = (extra = {}) => new PythonClient({ createWorker: () => new FakeWorker(), ...extra });

  it('sends typed requests and resolves the worker result', async () => {
    const c = make();
    const p = c.check(checkReq);
    const w = FakeWorker.all[0];
    expect(w.received[0]).toMatchObject({ type: 'check', id: 1, answer: 'y = x' });
    w.say({ id: 1, type: 'status', phase: 'running' });
    w.say({ id: 1, type: 'result', result: ok });
    await expect(p).resolves.toMatchObject({ correct: true });
  });

  it('stops a check after 5 seconds of running, restarts the worker and reports it', async () => {
    const onRestart = vi.fn();
    const c = make({ onRestart });
    const p = c.check(checkReq);
    FakeWorker.all[0].say({ id: 1, type: 'status', phase: 'running' });
    await vi.advanceTimersByTimeAsync(4999);
    expect(FakeWorker.all[0].terminated).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    const r = await p;
    expect(r).toMatchObject({ correct: false, timedOut: true, messages: [TIMED_OUT_MESSAGE] });
    expect(FakeWorker.all[0].terminated).toBe(true);
    expect(FakeWorker.all).toHaveLength(2);
    expect(onRestart).toHaveBeenCalledWith('timeout');
  });

  it('does not count package loading against the 5 second limit', async () => {
    const c = make();
    const p = c.check(checkReq);
    const w = FakeWorker.all[0];
    w.say({ id: 1, type: 'status', phase: 'loading' });
    await vi.advanceTimersByTimeAsync(30_000);
    expect(w.terminated).toBe(false);
    w.say({ id: 1, type: 'status', phase: 'running' });
    w.say({ id: 1, type: 'result', result: ok });
    await expect(p).resolves.toMatchObject({ correct: true });
  });

  it('gives loading its own 60 second limit', async () => {
    const c = make();
    const assertion = expect(c.check(checkReq)).rejects.toBeInstanceOf(PythonTimeoutError);
    await vi.advanceTimersByTimeAsync(60_000);
    await assertion;
    expect(FakeWorker.all).toHaveLength(2);
  });

  it('runs queued requests on the fresh worker after a timeout', async () => {
    const c = make();
    const first = c.check(checkReq);
    const second = c.check({ ...checkReq, answer: 'y = 2' });
    FakeWorker.all[0].say({ id: 1, type: 'status', phase: 'running' });
    await vi.advanceTimersByTimeAsync(5000);
    await first;
    const fresh = FakeWorker.all[1];
    expect(fresh.received[0]).toMatchObject({ id: 2, answer: 'y = 2' });
    fresh.say({ id: 2, type: 'status', phase: 'running' });
    fresh.say({ id: 2, type: 'result', result: ok });
    await expect(second).resolves.toMatchObject({ correct: true });
  });

  it('restart() fails pending work and starts a clean worker', async () => {
    const onRestart = vi.fn();
    const c = make({ onRestart });
    const assertion = expect(c.parts('x = 1')).rejects.toThrow('restarted');
    c.restart();
    await assertion;
    expect(FakeWorker.all[0].terminated).toBe(true);
    expect(FakeWorker.all).toHaveLength(2);
    expect(onRestart).toHaveBeenCalledWith('restart');
  });

  it('turns a Python-side error into a rejection', async () => {
    const c = make();
    const p = c.parts('a = 1; b = 2');
    FakeWorker.all[0].say({ id: 1, type: 'error', message: 'ValueError: parts() takes exactly one statement' });
    await expect(p).rejects.toThrow('exactly one statement');
  });
});
