// The one door to storage. The engine talks to this interface; Dexie backs it in the app and a Map backs it in tests.
import type { Attempt, InboxItem, Pattern, Schedule } from './types';

export interface Store {
  patterns(): Promise<Pattern[]>;
  putPatterns(patterns: Pattern[]): Promise<void>;
  schedules(): Promise<Schedule[]>;
  schedule(patternId: string): Promise<Schedule | undefined>;
  putSchedule(s: Schedule): Promise<void>;
  addAttempt(a: Attempt): Promise<void>;
  attempts(): Promise<Attempt[]>;
  addInbox(item: InboxItem): Promise<void>;
  inbox(): Promise<InboxItem[]>;
  getSetting<T>(key: string): Promise<T | undefined>;
  setSetting(key: string, value: unknown): Promise<void>;
}

export class MemoryStore implements Store {
  private p = new Map<string, Pattern>();
  private s = new Map<string, Schedule>();
  private a: Attempt[] = [];
  private i: InboxItem[] = [];
  private kv = new Map<string, unknown>();

  async patterns() {
    return [...this.p.values()].sort((x, y) => (x.order ?? 0) - (y.order ?? 0));
  }
  async putPatterns(patterns: Pattern[]) {
    for (const p of patterns) this.p.set(p.id, structuredClone(p));
  }
  async schedules() {
    return [...this.s.values()].map((x) => structuredClone(x));
  }
  async schedule(id: string) {
    const x = this.s.get(id);
    return x && structuredClone(x);
  }
  async putSchedule(s: Schedule) {
    this.s.set(s.patternId, structuredClone(s));
  }
  async addAttempt(a: Attempt) {
    this.a.push({ ...a, id: this.a.length + 1 });
  }
  async attempts() {
    return this.a.map((x) => ({ ...x }));
  }
  async addInbox(item: InboxItem) {
    this.i.push({ ...item, id: this.i.length + 1 });
  }
  async inbox() {
    return this.i.map((x) => ({ ...x }));
  }
  async getSetting<T>(key: string) {
    return this.kv.get(key) as T | undefined;
  }
  async setSetting(key: string, value: unknown) {
    this.kv.set(key, value);
  }
}
