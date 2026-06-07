// Client-side Dixon-Coles match predictor (a faithful port of
// model/dixon_coles.py + simulation/knockout.py). The model has no backend, but
// predictions.json ships each team's attack (α) and defence (β) plus γ, ρ,
// max_goals and the knockout knobs in meta — enough to reproduce the exact
// scoreline distribution for ANY pairing, including knockout matchups whose teams
// are only known once results come in. Pure functions, no React.
//
//   log λ (home xG) = α_home + β_away + γ·hostFlag
//   log μ (away xG) = α_away + β_home
//   P(x,y) = τ(x,y;λ,μ,ρ) · Poisson(x;λ) · Poisson(y;μ)   (τ on the 4 low scores)

import type { Predictions } from "../types";

export interface Outcome {
  homeWin: number;
  draw: number;
  awayWin: number;
  expHome: number;
  expAway: number;
}

export interface Scoreline {
  home: number;
  away: number;
  prob: number;
}

export interface Predictor {
  /** Whether both teams have ratings (a TBD/playoff placeholder has none). */
  known: (home: string, away: string) => boolean;
  /** Co-host home advantage to pass for a host playing in its own country. */
  hostAdvantage: number;
  /** 1X2 + expected goals for a single match. */
  outcome: (home: string, away: string, homeAdv?: number) => Outcome;
  /** The n most-likely exact scorelines, highest first. */
  topScorelines: (home: string, away: string, homeAdv?: number, n?: number) => Scoreline[];
  /** Staged knockout P(a advances over b) at a neutral venue. */
  knockoutWinProb: (a: string, b: string) => number;
}

/** Poisson pmf vector for k = 0..g, built iteratively (no factorials/gammaln). */
function poissonVec(lam: number, g: number): number[] {
  const v = new Array<number>(g + 1);
  v[0] = Math.exp(-lam);
  for (let k = 1; k <= g; k++) v[k] = (v[k - 1] * lam) / k;
  return v;
}

/** (G+1)×(G+1) scoreline matrix P[x][y], τ-adjusted and renormalised. */
function scorelineMatrix(
  lam: number,
  mu: number,
  rho: number,
  g: number,
): { P: number[][]; lam: number; mu: number } {
  const px = poissonVec(lam, g);
  const py = poissonVec(mu, g);
  const P: number[][] = Array.from({ length: g + 1 }, (_, x) =>
    Array.from({ length: g + 1 }, (_, y) => px[x] * py[y]),
  );
  // Dixon-Coles τ on the four lowest scorelines.
  P[0][0] *= 1 - lam * mu * rho;
  P[0][1] *= 1 + lam * rho;
  P[1][0] *= 1 + mu * rho;
  P[1][1] *= 1 - rho;

  let total = 0;
  for (let x = 0; x <= g; x++)
    for (let y = 0; y <= g; y++) {
      if (P[x][y] < 0) P[x][y] = 0; // extreme mismatches can push a τ cell negative
      total += P[x][y];
    }
  if (total > 0)
    for (let x = 0; x <= g; x++) for (let y = 0; y <= g; y++) P[x][y] /= total;
  return { P, lam, mu };
}

function wdl(P: number[][]): { home: number; draw: number; away: number } {
  let home = 0;
  let draw = 0;
  let away = 0;
  const g = P.length - 1;
  for (let x = 0; x <= g; x++)
    for (let y = 0; y <= g; y++) {
      if (x > y) home += P[x][y];
      else if (x === y) draw += P[x][y];
      else away += P[x][y];
    }
  return { home, draw, away };
}

const SHOOTOUT_GAP_SCALE = 1.0; // matches simulation/knockout._SHOOTOUT_GAP_SCALE

export function makePredictor(pred: Predictions): Predictor {
  const { meta, teams } = pred;
  const g = meta.max_goals;
  const rho = meta.rho;
  const ratings: Record<string, { a: number; b: number }> = {};
  for (const t of teams) ratings[t.team] = { a: t.alpha, b: t.beta };

  const lambdas = (home: string, away: string, homeAdv: number) => {
    const h = ratings[home];
    const a = ratings[away];
    return { lam: Math.exp(h.a + a.b + homeAdv), mu: Math.exp(a.a + h.b) };
  };

  const known = (home: string, away: string) =>
    !!home && !!away && home in ratings && away in ratings;

  const outcome = (home: string, away: string, homeAdv = 0): Outcome => {
    const { lam, mu } = lambdas(home, away, homeAdv);
    const { P } = scorelineMatrix(lam, mu, rho, g);
    const { home: hw, draw, away: aw } = wdl(P);
    let expHome = 0;
    let expAway = 0;
    for (let x = 0; x <= g; x++)
      for (let y = 0; y <= g; y++) {
        expHome += x * P[x][y];
        expAway += y * P[x][y];
      }
    return { homeWin: hw, draw, awayWin: aw, expHome, expAway };
  };

  const topScorelines = (home: string, away: string, homeAdv = 0, n = 6): Scoreline[] => {
    const { lam, mu } = lambdas(home, away, homeAdv);
    const { P } = scorelineMatrix(lam, mu, rho, g);
    const all: Scoreline[] = [];
    for (let x = 0; x <= g; x++)
      for (let y = 0; y <= g; y++) all.push({ home: x, away: y, prob: P[x][y] });
    all.sort((p, q) => q.prob - p.prob);
    return all.slice(0, n);
  };

  // Staged knockout (regulation → extra time → shootout), neutral venue, matching
  // simulation/knockout.knockout_win_prob.
  const knockoutWinProb = (a: string, b: string): number => {
    const k = meta.knockout;
    const { lam, mu } = lambdas(a, b, 0);
    const reg = wdl(scorelineMatrix(lam, mu, rho, g).P);
    if (k.mode === "coinflip") return reg.home + 0.5 * reg.draw;
    // extra time: plain double-Poisson at scaled rates, no τ correction.
    const et = wdl(scorelineMatrix(lam * k.extra_time_fraction, mu * k.extra_time_fraction, 0, g).P);
    let shootout = 0.5;
    if (k.penalty_skill_tilt) {
      const ra = ratings[a];
      const rb = ratings[b];
      const gap = (ra.a - ra.b - (rb.a - rb.b)) / SHOOTOUT_GAP_SCALE;
      shootout = 0.5 + (k.penalty_cap - 0.5) * Math.tanh(gap);
    }
    return reg.home + reg.draw * (et.home + et.draw * shootout);
  };

  return {
    known,
    hostAdvantage: meta.cohost_multiplier * meta.home_advantage_gamma,
    outcome,
    topScorelines,
    knockoutWinProb,
  };
}
