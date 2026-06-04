// Memoized selector: the probabilities to *display*. With no pinned conditions
// these are the precise marginals from predictions.json (100k sims); with
// conditions, they are exact conditional frequencies recomputed from the sample.

import { useMemo } from "react";
import { recompute } from "../lib/recompute";
import type { StageProbs } from "../types";
import { useStore } from "./store";

export interface DisplayProbs {
  active: boolean;
  count: number;
  total: number;
  lowConfidence: boolean;
  byTeam: Record<string, StageProbs>;
}

export function useProbabilities(): DisplayProbs {
  const predictions = useStore((s) => s.predictions);
  const outcomes = useStore((s) => s.outcomes);
  const conditions = useStore((s) => s.conditions);

  return useMemo<DisplayProbs>(() => {
    const marginal: Record<string, StageProbs> = {};
    if (predictions) {
      for (const t of predictions.teams) {
        marginal[t.team] = {
          advance: t.p_advance,
          r16: t.p_r16,
          qf: t.p_qf,
          sf: t.p_sf,
          final: t.p_final,
          win: t.p_win,
        };
      }
    }
    if (conditions.length === 0 || !outcomes) {
      return {
        active: false,
        count: outcomes?.n ?? 0,
        total: outcomes?.n ?? 0,
        lowConfidence: false,
        byTeam: marginal,
      };
    }
    const r = recompute(outcomes, conditions);
    return { active: true, count: r.count, total: r.total, lowConfidence: r.lowConfidence, byTeam: r.byTeam };
  }, [predictions, outcomes, conditions]);
}
