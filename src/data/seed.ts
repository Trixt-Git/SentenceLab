// Seed decks ship as JSON and are imported into the patterns store. A pattern is written again only when its
// seed `version` differs from the stored one, so a rerun never touches patterns that are already current.
import type { Store } from './store';
import type { DeckFile, Pattern } from './types';

const DECK_ORDER = ['core', 'pandas', 'sklearn'];

export function decksFromFiles(files: Record<string, DeckFile>): Pattern[] {
  const decks = Object.values(files).sort(
    (a, b) => DECK_ORDER.indexOf(a.deck) - DECK_ORDER.indexOf(b.deck) || a.deck.localeCompare(b.deck),
  );
  return decks.flatMap((d) => d.patterns).map((p, order) => ({ ...p, order }));
}

export async function seedPatterns(store: Store, seed: Pattern[]): Promise<number> {
  const have = new Map((await store.patterns()).map((p) => [p.id, p]));
  const fresh = seed.filter((p) => have.get(p.id)?.version !== p.version || have.get(p.id)?.order !== p.order);
  if (fresh.length) await store.putPatterns(fresh);
  return fresh.length;
}
