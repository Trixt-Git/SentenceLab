// Building a session (ARCHITECTURE.md section 7, pilot subset): due reviews, then new patterns whose prerequisites
// are met, up to the session size. Retries are inserted later, as misses happen.
import type { Format, Pattern, Schedule } from '../data/types';

export const NEW_PER_DAY = 5;
export const SESSION_SIZE = 20;
export const RETRY_GAP = 5;

export interface QueueItem {
  patternId: string;
  kind: 'review' | 'new' | 'retry';
  /** Retries keep the instance and format of the miss and use a different wording. */
  instanceId?: string;
  format?: Format;
  avoidIntent?: number;
}

export interface SessionOptions {
  newPerDay?: number;
  sessionSize?: number;
}

export function buildQueue(
  patterns: Pattern[],
  schedules: Schedule[],
  today: string,
  { newPerDay = NEW_PER_DAY, sessionSize = SESSION_SIZE }: SessionOptions = {},
): QueueItem[] {
  const byId = new Map(schedules.map((s) => [s.patternId, s]));
  const order = new Map(patterns.map((p, i) => [p.id, i]));

  const due = schedules
    .filter((s) => s.dueDay <= today && order.has(s.patternId))
    .sort((a, b) => a.dueDay.localeCompare(b.dueDay) || order.get(a.patternId)! - order.get(b.patternId)!)
    .map<QueueItem>((s) => ({ patternId: s.patternId, kind: 'review' }));

  const introducedToday = schedules.filter((s) => s.introducedDay === today).length;
  const room = Math.max(0, newPerDay - introducedToday);
  const unlocked = (p: Pattern) => p.requires.every((r) => (byId.get(r)?.correctCount ?? 0) >= 1);
  const fresh = patterns
    .filter((p) => !byId.has(p.id) && unlocked(p))
    .slice(0, room)
    .map<QueueItem>((p) => ({ patternId: p.id, kind: 'new' }));

  return [...due, ...fresh].slice(0, sessionSize);
}

/** After a miss the retry goes back 5 cards later, or last if fewer than 5 remain. */
export function insertRetry(queue: QueueItem[], retry: QueueItem): QueueItem[] {
  const at = Math.min(RETRY_GAP, queue.length);
  return [...queue.slice(0, at), retry, ...queue.slice(at)];
}
