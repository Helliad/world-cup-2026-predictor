// Client-side conditional-probability recompute (§7.6) — the "what if" engine.
//
// Pin conditions, filter the stored simulation sample to the matching subset, and
// recompute every team's stage probabilities as exact conditional frequencies.
// No model in the browser: this is pure counting over the precomputed sample, so
// it is instant and verifiably correct against a brute-force tally.

import type { Outcomes } from "./data";
import type { StageProbs } from "../types";

export type ConditionKind = "champion" | "final" | "sf" | "qf" | "r16" | "advance" | "group_winner";

export interface Condition {
  id: string; // stable key, e.g. "Brazil:champion"
  team: string;
  kind: ConditionKind;
  label: string; // human-readable, e.g. "Brazil win the title"
}

// Below this many matching sims, a conditional probability is too noisy to show
// as a precise number (§7.6 honesty guardrail).
export const MIN_SAMPLE = 200;

const STAGE_THRESHOLD: Record<Exclude<ConditionKind, "group_winner">, number> = {
  advance: 1,
  r16: 2,
  qf: 3,
  sf: 4,
  final: 5,
  champion: 6,
};

export function simSatisfies(o: Outcomes, conditions: Condition[], s: number): boolean {
  const T = o.teams.length;
  const base = s * T;
  for (const c of conditions) {
    const ti = o.teamIndex[c.team];
    if (ti === undefined) return false;
    if (c.kind === "group_winner") {
      if (o.groupRank[base + ti] !== 1) return false;
    } else if (o.stage[base + ti] < STAGE_THRESHOLD[c.kind]) {
      return false;
    }
  }
  return true;
}

export interface ConditionalResult {
  count: number; // matching sims
  total: number; // sample size
  /** team -> conditional stage probabilities over the matching subset. */
  byTeam: Record<string, StageProbs>;
  lowConfidence: boolean;
}

export function recompute(o: Outcomes, conditions: Condition[]): ConditionalResult {
  const T = o.teams.length;
  const tally = new Float64Array(T * 6); // per team: counts for >=r32,>=r16,>=qf,>=sf,>=final,==champ
  let count = 0;

  for (let s = 0; s < o.n; s++) {
    if (conditions.length > 0 && !simSatisfies(o, conditions, s)) continue;
    count++;
    const base = s * T;
    for (let t = 0; t < T; t++) {
      const c = o.stage[base + t];
      const tb = t * 6;
      if (c >= 1) tally[tb]++;
      if (c >= 2) tally[tb + 1]++;
      if (c >= 3) tally[tb + 2]++;
      if (c >= 4) tally[tb + 3]++;
      if (c >= 5) tally[tb + 4]++;
      if (c >= 6) tally[tb + 5]++;
    }
  }

  const d = count || 1;
  const byTeam: Record<string, StageProbs> = {};
  for (let t = 0; t < T; t++) {
    const tb = t * 6;
    byTeam[o.teams[t]] = {
      advance: tally[tb] / d,
      r16: tally[tb + 1] / d,
      qf: tally[tb + 2] / d,
      sf: tally[tb + 3] / d,
      final: tally[tb + 4] / d,
      win: tally[tb + 5] / d,
    };
  }
  return { count, total: o.n, byTeam, lowConfidence: count < MIN_SAMPLE };
}

// ---- URL (de)serialization so a pinned scenario is itself a shareable link ----

export function serializeConditions(conditions: Condition[]): string {
  return conditions.map((c) => `${c.team}:${c.kind}`).join(",");
}

const KIND_VERB: Record<ConditionKind, string> = {
  champion: "win the title",
  final: "reach the final",
  sf: "reach the semi-finals",
  qf: "reach the quarter-finals",
  r16: "reach the Round of 16",
  advance: "advance from the group",
  group_winner: "win their group",
};

export function makeCondition(team: string, kind: ConditionKind): Condition {
  return { id: `${team}:${kind}`, team, kind, label: `${team} ${KIND_VERB[kind]}` };
}

export function parseConditions(param: string | null, validTeams: Set<string>): Condition[] {
  if (!param) return [];
  const out: Condition[] = [];
  for (const tok of param.split(",")) {
    const [team, kind] = tok.split(":");
    if (validTeams.has(team) && kind in KIND_VERB) {
      out.push(makeCondition(team, kind as ConditionKind));
    }
  }
  return out;
}
