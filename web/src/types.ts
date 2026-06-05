// Types for the predictions.json contract emitted by scripts/run_pipeline.py (§8.1).

export type DataConfidence = "high" | "medium" | "low";

export interface Meta {
  n_simulations: number;
  quick: boolean;
  seed: number;
  model_version: string;
  data_snapshot: string;
  data_checksum: string;
  data_rows: number;
  git_commit: string;
  config_hash: string;
  provisional: boolean;
  generated_at: string;
  home_advantage_gamma: number;
  cohost_multiplier: number;
  half_life_days: number | null;
  se_note: string;
  model_metrics: { rps_test: number; accuracy_test: number; achieved_tier: string } | null;
  libraries: Record<string, string>;
}

export interface TeamPrediction {
  team: string;
  group: string;
  data_confidence: DataConfidence;
  p_advance: number;
  p_r16: number;
  p_qf: number;
  p_sf: number;
  p_final: number;
  p_win: number;
  se_win: number;
  alpha: number;
  beta: number;
}

export interface GroupRow {
  team: string;
  p_advance: number;
  exp_points: number;
  data_confidence: DataConfidence;
}

export interface Matchup {
  home_win: number;
  draw: number;
  away_win: number;
}

export interface Fixture {
  group: string;
  date: string;
  home: string;
  away: string;
  home_win: number;
  draw: number;
  away_win: number;
  exp_home: number;
  exp_away: number;
  host: string | null; // home team name if it has co-host home advantage, else null
}

export interface Predictions {
  meta: Meta;
  groups: Record<string, GroupRow[]>;
  teams: TeamPrediction[];
  matchups: Record<string, Matchup>;
  fixtures: Fixture[];
}

// Stage probabilities a team can be shown at (ordered furthest → nearest).
export type StageKey = "advance" | "r16" | "qf" | "sf" | "final" | "win";

export interface StageProbs {
  advance: number;
  r16: number;
  qf: number;
  sf: number;
  final: number;
  win: number;
}

export const STAGE_LABELS: Record<StageKey, string> = {
  advance: "Advance",
  r16: "Round of 16",
  qf: "Quarter-final",
  sf: "Semi-final",
  final: "Final",
  win: "Champion",
};
