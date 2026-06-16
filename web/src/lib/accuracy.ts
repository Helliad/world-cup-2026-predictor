// Scores the model's pre-match predictions against results as they come in.
//
// The key idea: predictions.json ships each team's Dixon-Coles ratings (α, β),
// so makePredictor() reproduces the *exact same 1X2 forecast the model would
// have made before kickoff* — independent of which results have since been
// pinned into the simulation. That lets us grade, after the fact, the
// probability the model assigned to what actually happened.
//
// Two proper scoring rules are used (both lower = better, both in [0, 1] so they
// average together across group and knockout games):
//   • RPS  — Ranked Probability Score, the same metric the model reports on its
//            historical backtest (meta.model_metrics.rps_test), so live and
//            backtest numbers are directly comparable.
//   • Brier — squared error of the full probability vector.
// Everything is benchmarked against a no-skill baseline (a blind 1/3-1/3-1/3
// guess), so "good" means "beat a coin-flip", not "got a low number".

import type { Predictor } from "./predict";
import type { ScheduleMatch } from "../types";

export type Result = "home" | "draw" | "away";

export interface ScoredMatch {
  match: ScheduleMatch;
  home: string;
  away: string;
  /** "1x2" for group games, "advance" for knockout ties (no draw outcome). */
  kind: "1x2" | "advance";
  /** Model's pre-match probabilities. For "advance", draw is 0. */
  pred: { home: number; draw: number; away: number };
  /** What happened: home/draw/away (advance games never resolve to "draw"). */
  actual: Result;
  /** The single outcome the model thought most likely. */
  topPick: Result;
  /** Did the most-likely outcome happen? */
  correct: boolean;
  /** Among decisive (non-draw) results, did the model lean to the right team? */
  calledWinner: boolean | null;
  /** Probability the model put on the outcome that actually occurred. */
  pActual: number;
  brier: number;
  rps: number;
  /** RPS of a blind 1/3 guess on this same game — the no-skill bar to clear. */
  baselineRps: number;
  /** Model's single most-likely exact scoreline (group games only). */
  topScore: { home: number; away: number } | null;
  /** Did that exact scoreline come in? */
  exact: boolean;
}

export interface Scorecard {
  scored: ScoredMatch[];
  n: number;
  /** Most-likely-outcome hit rate. */
  accuracy: number;
  /** Hit rate on decisive (non-draw) results only — the fair top-pick test, */
  /** since virtually no model ever makes a draw its single most likely call. */
  decisiveAccuracy: number;
  decisiveN: number;
  draws: number;
  meanRps: number;
  meanBrier: number;
  baselineRps: number;
  /** Mean probability the model placed on what actually happened. */
  foresight: number;
  /** Skill vs the coin-flip baseline: 1 − meanRps/baselineRps. >0 beats it. */
  skill: number;
  /** 0–100 headline: how much of the available foresight the model captured. */
  score: number;
  grade: string;
  exactScores: number;
}

function classifyScore(s: { home: number; away: number }): Result {
  if (s.home > s.away) return "home";
  if (s.home < s.away) return "away";
  return "draw";
}

/** RPS for ordered outcomes home ▸ draw ▸ away (group) or home ▸ away (knockout). */
function rps(pred: number[], actualIdx: number): number {
  let cumPred = 0;
  let cumAct = 0;
  let sum = 0;
  for (let i = 0; i < pred.length - 1; i++) {
    cumPred += pred[i];
    cumAct += i === actualIdx ? 1 : 0;
    sum += (cumPred - cumAct) ** 2;
  }
  return sum / (pred.length - 1);
}

function scoreMatch(m: ScheduleMatch, predictor: Predictor, hostAdv: number): ScoredMatch | null {
  const home = m.home;
  const away = m.away;
  if (!home || !away || !predictor.known(home, away)) return null;

  if (m.round === "group") {
    if (!m.score) return null;
    const o = predictor.outcome(home, away, hostAdv);
    const pred = { home: o.homeWin, draw: o.draw, away: o.awayWin };
    const actual = classifyScore(m.score);
    const order: Result[] = ["home", "draw", "away"];
    const probs = [pred.home, pred.draw, pred.away];
    const topPick = order[probs.indexOf(Math.max(...probs))];
    const actualIdx = order.indexOf(actual);
    const y = [0, 0, 0];
    y[actualIdx] = 1;
    const top = predictor.topScorelines(home, away, hostAdv, 1)[0];
    const topScore = top ? { home: top.home, away: top.away } : null;
    return {
      match: m,
      home,
      away,
      kind: "1x2",
      pred,
      actual,
      topPick,
      correct: topPick === actual,
      calledWinner:
        actual === "draw" ? null : (pred.home > pred.away ? "home" : "away") === actual,
      pActual: probs[actualIdx],
      brier: probs.reduce((s, p, i) => s + (p - y[i]) ** 2, 0),
      rps: rps(probs, actualIdx),
      baselineRps: rps([1 / 3, 1 / 3, 1 / 3], actualIdx),
      topScore,
      exact: !!topScore && topScore.home === m.score.home && topScore.away === m.score.away,
    };
  }

  // Knockout: a tie can't end level, so we grade who advanced (regulation +
  // extra time + penalties) rather than the 90-minute scoreline.
  if (!m.winner) return null;
  const pHome = predictor.knockoutWinProb(home, away);
  const pred = { home: pHome, draw: 0, away: 1 - pHome };
  const actual: Result = m.winner === home ? "home" : "away";
  const topPick: Result = pHome >= 0.5 ? "home" : "away";
  const actualIdx = actual === "home" ? 0 : 1;
  const probs = [pHome, 1 - pHome];
  const y = actual === "home" ? [1, 0] : [0, 1];
  return {
    match: m,
    home,
    away,
    kind: "advance",
    pred,
    actual,
    topPick,
    correct: topPick === actual,
    calledWinner: topPick === actual,
    pActual: probs[actualIdx],
    brier: probs.reduce((s, p, i) => s + (p - y[i]) ** 2, 0),
    rps: rps(probs, actualIdx),
    baselineRps: rps([0.5, 0.5], actualIdx),
    topScore: null,
    exact: false,
  };
}

function gradeFor(skill: number): string {
  if (skill >= 0.4) return "A";
  if (skill >= 0.25) return "B";
  if (skill >= 0.12) return "C";
  if (skill >= 0.0) return "D";
  return "F";
}

export function buildScorecard(schedule: ScheduleMatch[], predictor: Predictor): Scorecard {
  const scored = schedule
    .filter((m) => m.status === "played")
    .sort((a, b) => a.match - b.match)
    .map((m) => {
      const hostAdv = m.host && m.host === m.home ? predictor.hostAdvantage : 0;
      return scoreMatch(m, predictor, hostAdv);
    })
    .filter((s): s is ScoredMatch => s !== null);

  const n = scored.length;
  if (n === 0) {
    return {
      scored: [],
      n: 0,
      accuracy: 0,
      decisiveAccuracy: 0,
      decisiveN: 0,
      draws: 0,
      meanRps: 0,
      meanBrier: 0,
      baselineRps: 0,
      foresight: 0,
      skill: 0,
      score: 0,
      grade: "—",
      exactScores: 0,
    };
  }

  const mean = (f: (s: ScoredMatch) => number) => scored.reduce((a, s) => a + f(s), 0) / n;
  const decisive = scored.filter((s) => s.calledWinner !== null);
  const meanRps = mean((s) => s.rps);
  const baselineRps = mean((s) => s.baselineRps);
  const foresight = mean((s) => s.pActual);
  const skill = baselineRps > 0 ? 1 - meanRps / baselineRps : 0;

  return {
    scored,
    n,
    accuracy: scored.filter((s) => s.correct).length / n,
    decisiveAccuracy: decisive.length
      ? decisive.filter((s) => s.calledWinner).length / decisive.length
      : 0,
    decisiveN: decisive.length,
    draws: scored.filter((s) => s.actual === "draw").length,
    meanRps,
    meanBrier: mean((s) => s.brier),
    baselineRps,
    foresight,
    skill,
    // Foresight scaled so a blind 1/3 guess ≈ 0 and a perfect oracle = 100,
    // clamped to a friendly 0–100 band.
    score: Math.max(0, Math.min(100, Math.round(((foresight - 1 / 3) / (1 - 1 / 3)) * 100))),
    grade: gradeFor(skill),
    exactScores: scored.filter((s) => s.exact).length,
  };
}
