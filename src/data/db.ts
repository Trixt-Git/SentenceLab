// Dexie stores (ARCHITECTURE.md section 9). The pilot schedules with fixed gaps, so `schedule` is indexed by
// `dueDay` here; Phase 2 swaps in FSRS with a new version(n).upgrade() step, never by dropping data.
import Dexie, { type Table } from 'dexie';
import type { Store } from './store';
import type { Attempt, InboxItem, Pattern, Schedule } from './types';

export const SCHEMA_VERSION = 1;

export class LabDB extends Dexie {
  patterns!: Table<Pattern, string>;
  schedule!: Table<Schedule, string>;
  attempts!: Table<Attempt, number>;
  inbox!: Table<InboxItem, number>;
  settings!: Table<{ key: string; value: unknown }, string>;

  constructor(name = 'sentence-lab') {
    super(name);
    this.version(1).stores({
      patterns: 'id, deck, kind, source',
      schedule: 'patternId, dueDay',
      attempts: '++id, patternId, instanceId, at',
      settings: 'key',
      inbox: '++id, at, status',
    });
  }
}

export class DexieStore implements Store {
  constructor(private db: LabDB = new LabDB()) {}

  async patterns() {
    return (await this.db.patterns.toArray()).sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  }
  async putPatterns(patterns: Pattern[]) {
    await this.db.patterns.bulkPut(patterns);
  }
  schedules() {
    return this.db.schedule.toArray();
  }
  schedule(id: string) {
    return this.db.schedule.get(id);
  }
  async putSchedule(s: Schedule) {
    await this.db.schedule.put(s);
  }
  async addAttempt(a: Attempt) {
    await this.db.attempts.add(a);
  }
  attempts() {
    return this.db.attempts.toArray();
  }
  async addInbox(item: InboxItem) {
    await this.db.inbox.add(item);
  }
  inbox() {
    return this.db.inbox.orderBy('at').toArray();
  }
  async getSetting<T>(key: string) {
    return (await this.db.settings.get(key))?.value as T | undefined;
  }
  async setSetting(key: string, value: unknown) {
    await this.db.settings.put({ key, value });
  }
}

/** Ask the browser not to evict our data. Safe to call on every start; failure is not an error. */
export async function requestPersistence(): Promise<boolean> {
  try {
    return (await navigator.storage?.persist?.()) ?? false;
  } catch {
    return false;
  }
}
