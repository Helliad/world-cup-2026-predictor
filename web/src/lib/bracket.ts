// Bracket projection from the stored sample. Each sim's full knockout tree is
// reconstructed by folding the 32 Round-of-32 occupants: at every node the team
// that advanced is the one whose furthest-stage code reaches that round. Tallying
// occupants across the (optionally condition-filtered) sims gives, per bracket
// position, the most-likely team and the exact probability it lands there.

import type { Outcomes } from "./data";
import type { Condition } from "./recompute";
import { simSatisfies } from "./recompute";

export interface BracketNode {
  team: string | null;
  prob: number; // P(this team occupies this position | conditions)
}

export interface BracketProjection {
  // rounds[0]=R32 (32 nodes) … rounds[5]=Champion (1 node)
  rounds: BracketNode[][];
  count: number;
}

const ROUND_SIZES = [32, 16, 8, 4, 2, 1];
export const ROUND_NAMES = ["Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final", "Champion"];

export function projectBracket(o: Outcomes, conditions: Condition[]): BracketProjection {
  const T = o.teams.length;
  const tallies = ROUND_SIZES.map((sz) => Array.from({ length: sz }, () => new Int32Array(T)));
  let count = 0;

  let level = new Int32Array(32);
  for (let s = 0; s < o.n; s++) {
    if (conditions.length > 0 && !simSatisfies(o, conditions, s)) continue;
    count++;
    const sbase = s * 32;
    const stbase = s * T;
    for (let j = 0; j < 32; j++) {
      const t = o.slots[sbase + j];
      level[j] = t;
      tallies[0][j][t]++;
    }
    for (let r = 1; r <= 5; r++) {
      const next = new Int32Array(level.length / 2);
      for (let i = 0; i < next.length; i++) {
        const a = level[2 * i];
        const b = level[2 * i + 1];
        const adv = o.stage[stbase + a] >= r + 1 ? a : b; // the team that advanced
        next[i] = adv;
        tallies[r][i][adv]++;
      }
      level = next;
    }
  }

  const rounds = tallies.map((roundTallies) =>
    roundTallies.map((arr) => {
      let best = -1;
      let bestc = 0;
      for (let t = 0; t < T; t++) {
        if (arr[t] > bestc) {
          bestc = arr[t];
          best = t;
        }
      }
      return { team: best >= 0 ? o.teams[best] : null, prob: count ? bestc / count : 0 };
    }),
  );
  return { rounds, count };
}
