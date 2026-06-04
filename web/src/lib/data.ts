// Data loading: fetch the static artifacts once and decode the compact what-if
// sample. No backend, no Python at runtime (§7).

import type { Predictions } from "../types";

const base = import.meta.env.BASE_URL;

export async function loadPredictions(): Promise<Predictions> {
  const res = await fetch(`${base}predictions.json`);
  if (!res.ok) throw new Error(`Failed to load predictions.json (HTTP ${res.status})`);
  return (await res.json()) as Predictions;
}

export interface Outcomes {
  n: number;
  teams: string[];
  teamIndex: Record<string, number>;
  stageCodes: Record<string, number>;
  /** stage[s * T + t] = furthest-stage code for team t in sim s. */
  stage: Uint8Array;
  /** groupRank[s * T + t] = team t's group finish (1..4) in sim s. */
  groupRank: Uint8Array;
  /** slots[s * 32 + j] = team index occupying Round-of-32 slot j in sim s. */
  slots: Uint8Array;
}

function decodeBase64(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

interface RawOutcomes {
  n: number;
  teams: string[];
  stage_codes: Record<string, number>;
  stage_b64: string;
  group_rank_b64: string;
  slots_b64: string;
}

export async function loadOutcomes(): Promise<Outcomes> {
  const res = await fetch(`${base}outcomes_sample.json`);
  if (!res.ok) throw new Error(`Failed to load outcomes_sample.json (HTTP ${res.status})`);
  const raw = (await res.json()) as RawOutcomes;
  const teamIndex: Record<string, number> = {};
  raw.teams.forEach((t, i) => (teamIndex[t] = i));
  return {
    n: raw.n,
    teams: raw.teams,
    teamIndex,
    stageCodes: raw.stage_codes,
    stage: decodeBase64(raw.stage_b64),
    groupRank: decodeBase64(raw.group_rank_b64),
    slots: decodeBase64(raw.slots_b64),
  };
}
