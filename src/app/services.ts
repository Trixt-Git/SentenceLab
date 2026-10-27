// App-wide singletons: storage, the Python worker client and the seed decks.
import { useSyncExternalStore } from 'react';
import { DexieStore, requestPersistence, SCHEMA_VERSION } from '../data/db';
import { decksFromFiles, seedPatterns } from '../data/seed';
import type { DeckFile } from '../data/types';
import { PythonClient } from '../python/client';
import type { Phase } from '../python/protocol';

type PhaseOrIdle = Phase | 'idle';
let phase: PhaseOrIdle = 'idle';
const listeners = new Set<() => void>();

export const python = new PythonClient({
  onPhase: (p) => {
    phase = p;
    listeners.forEach((l) => l());
  },
});

export const store = new DexieStore();

const decks = import.meta.glob<DeckFile>('../../content/decks/*.json', { eager: true, import: 'default' });
export const seed = decksFromFiles(decks);

/** "Loading Python…" is shown wherever the bench is waiting on this. */
export function usePythonPhase(): PhaseOrIdle {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => phase,
  );
}

let booted: Promise<void> | null = null;

/** First run: import the seed decks, record the schema version and ask the browser to keep our data. */
export function boot(): Promise<void> {
  booted ??= (async () => {
    await seedPatterns(store, seed);
    await store.setSetting('schemaVersion', SCHEMA_VERSION);
    await requestPersistence();
  })();
  return booted;
}
