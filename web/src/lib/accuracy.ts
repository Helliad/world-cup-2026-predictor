// Scores the model's pre-match calls against results as they come in.
//
// The rule is deliberately simple: for each match the model "calls" whichever
// outcome it gave the highest probability — a home win, a draw, or an away win.
// If that outcome happens, it's a hit. We don't grade the scoreline, just the
// call. predictions.json ships each team's Dixon-Coles ratings, so makePredictor
// reproduces the exact forecast the model would have made before kickoff,
// independent of which results have since been pinned into the simulation.

import type { Predictor } from "./predict";
import type { ScheduleMatch } from "../types";

export type Result = "home" | "draw" | "away";

export interface ScoredMatch {
  match: ScheduleMatch;
  home: string;
  away: string;
  /** Model's pre-match probabilities. For knockout ties, draw is 0. */
  pred: { home: number; draw: number; away: number };
  /** What actually happened. */
  actual: Result;
  /** The outcome the model gave the highest probability — its call. */
  topPick: Result;
  /** The probability behind that call. */
  topProb: number;
  /** Did the called outcome happen? */
  correct: boolean;
}

export interface Scorecard {
  scored: ScoredMatch[];
  n: number;
  correct: number;
  wrong: number;
  /** Share of matches the model called right. */
  accuracy: number;
  grade: string;
}

function classifyScore(s: { home: number; away: number }): Result {
  if (s.home > s.away) return "home";
  if (s.home < s.away) return "away";
  return "draw";
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
    const topProb = Math.max(...probs);
    const topPick = order[probs.indexOf(topProb)];
    return { match: m, home, away, pred, actual, topPick, topProb, correct: topPick === actual };
  }

  // Knockout: a tie can't end level, so the call is simply who advances.
  if (!m.winner) return null;
  const pHome = predictor.knockoutWinProb(home, away);
  const pred = { home: pHome, draw: 0, away: 1 - pHome };
  const actual: Result = m.winner === home ? "home" : "away";
  const topPick: Result = pHome >= 0.5 ? "home" : "away";
  return {
    match: m,
    home,
    away,
    pred,
    actual,
    topPick,
    topProb: Math.max(pHome, 1 - pHome),
    correct: topPick === actual,
  };
}

function gradeFor(accuracy: number): string {
  if (accuracy >= 0.7) return "A";
  if (accuracy >= 0.55) return "B";
  if (accuracy >= 0.45) return "C";
  if (accuracy >= 0.33) return "D";
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
  const correct = scored.filter((s) => s.correct).length;
  const accuracy = n > 0 ? correct / n : 0;

  return {
    scored,
    n,
    correct,
    wrong: n - correct,
    accuracy,
    grade: n > 0 ? gradeFor(accuracy) : "—",
  };
}
