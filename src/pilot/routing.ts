// Help after a miss in the pilot (ARCHITECTURE.md section 13, "Help after a miss in the pilot"). The full build
// routes some misses to L2 and L3; the pilot has neither, so every row here uses only L4, the effect gate's
// toggles, the basic bench and the checker's messages. The answer is never revealed by any of these.
import type { Blame, PartName } from '../python/protocol';
import type { StuckReason } from '../data/types';

export const PART_ROTATION: PartName[] = ['subject', 'verb', 'details', 'landing'];

export type Help =
  | { kind: 'done' }
  /** Syntax miss, first time on this card: the learner's own line stays in the input and they try again. */
  | { kind: 'fix' }
  | { kind: 'l4'; part: PartName | 'rotate' }
  /** "What should this line change?", then the bench says it in words. */
  | { kind: 'effect-prompt'; then: 'l4-verb' | 'l5' }
  | { kind: 'verb-hint' }
  /** Nothing more to offer on this card: a retry reveals the reference once answered. */
  | { kind: 'end' };

export interface CardProgress {
  /** Syntax misses on this card, counting the one being routed. */
  assembleMisses: number;
  l4Missed: boolean;
  /** Parts already blanked on this card. */
  blanked: PartName[];
}

export function routeMiss(blame: Blame | undefined, p: CardProgress): Help {
  switch (blame) {
    case 'assemble':
      return p.assembleMisses <= 1 ? { kind: 'fix' } : { kind: 'l4', part: 'rotate' };
    case 'subject':
    case 'verb':
    case 'details':
    case 'landing':
      return { kind: 'l4', part: blame };
    case 'effect':
      return { kind: 'effect-prompt', then: 'l4-verb' };
    default:
      return { kind: 'l4', part: 'rotate' };
  }
}

export function routeStuck(reason: StuckReason): Help {
  switch (reason) {
    case 'verb':
      return { kind: 'verb-hint' };
    case 'assemble':
      return { kind: 'l4', part: 'rotate' };
    case 'effect':
      return { kind: 'effect-prompt', then: 'l5' };
  }
}

/** The order to try parts in: the wanted one first, then the rotation from `start`, parts already blanked last. */
export function partOrder(want: PartName | 'rotate', start: number, blanked: PartName[]): PartName[] {
  const rotated = PART_ROTATION.map((_, i) => PART_ROTATION[(start + i) % PART_ROTATION.length]);
  const fresh = rotated.filter((x) => !blanked.includes(x));
  const used = rotated.filter((x) => blanked.includes(x));
  const rest = [...fresh, ...used];
  return want === 'rotate' ? rest : [want, ...rest.filter((x) => x !== want)];
}
