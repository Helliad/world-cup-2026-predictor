import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Explainer } from "../components/Explainer";
import { StatCallout } from "../components/StatCallout";
import { TeamBadge } from "../components/TeamBadge";
import type { ScoredMatch } from "../lib/accuracy";
import { buildScorecard } from "../lib/accuracy";
import { pct } from "../lib/format";
import { makePredictor } from "../lib/predict";
import { ROUND_SHORT, venueText } from "../lib/schedule";
import { useStore } from "../store/store";

// Scorecard: marks the model's homework. For every match that's been played we
// re-derive the forecast it would have made before kickoff and grade the
// probability it put on what actually happened — with proper scoring rules
// (RPS, Brier) benchmarked against a no-skill coin-flip, so the page is honest
// about hot and cold runs rather than cherry-picking the hits.

const GRADE_NOTE: Record<string, string> = {
  A: "Comfortably beating a blind guess.",
  B: "Clearly ahead of a coin-flip.",
  C: "Modestly ahead of a blind guess.",
  D: "Barely shading a coin-flip.",
  F: "Behind a blind 1/3 guess — a brutal, draw-heavy start.",
  "—": "No matches scored yet.",
};

function Mark({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-flex h-4 w-4 items-center justify-center rounded-full text-[0.6rem] font-bold ${
        ok ? "bg-emerald-500/15 text-emerald-500" : "bg-rose-500/15 text-rose-400"
      }`}
      aria-hidden="true"
    >
      {ok ? "✓" : "✗"}
    </span>
  );
}

const RESULT_LABEL: Record<ScoredMatch["actual"], (s: ScoredMatch) => string> = {
  home: (s) => `${s.home} win`,
  away: (s) => `${s.away} win`,
  draw: () => "Draw",
};

function ScoreRow({ s }: { s: ScoredMatch }) {
  const m = s.match;
  const score = m.score;
  return (
    <Link
      to={`/match/${m.match}`}
      className="block rounded-lg border border-border bg-surface px-3 py-2.5 transition-colors hover:border-accent/50"
    >
      <div className="mb-1.5 flex items-center justify-between text-[0.7rem] uppercase tracking-wide text-muted">
        <span>
          {ROUND_SHORT[m.round]}
          {m.group ? ` ${m.group}` : ""} · {venueText(m)}
        </span>
        <span className="flex items-center gap-1.5">
          {s.exact && (
            <span className="rounded bg-accent/15 px-1.5 py-0.5 text-[0.6rem] font-semibold text-accent">
              exact score
            </span>
          )}
          <Mark ok={s.correct} />
        </span>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <TeamBadge team={s.home} className="h-6 w-6 text-[0.6rem]" />
          <span className={`truncate text-sm ${m.winner === s.home ? "font-bold" : "font-medium"}`}>
            {s.home}
          </span>
        </div>
        <span className="shrink-0 rounded bg-surface-2 px-2 py-0.5 text-sm font-bold tabular-nums">
          {score ? `${score.home}–${score.away}` : "—"}
        </span>
        <div className="flex min-w-0 flex-row-reverse items-center gap-2 text-right">
          <TeamBadge team={s.away} className="h-6 w-6 text-[0.6rem]" />
          <span className={`truncate text-sm ${m.winner === s.away ? "font-bold" : "font-medium"}`}>
            {s.away}
          </span>
        </div>
      </div>

      {/* Pre-match 1X2 forecast the model would have made. */}
      <div className="mt-2">
        <div className="flex h-2 overflow-hidden rounded-full" aria-hidden="true">
          <div className="bg-prob-fill" style={{ width: `${s.pred.home * 100}%` }} />
          {s.kind === "1x2" && <div className="bg-muted/40" style={{ width: `${s.pred.draw * 100}%` }} />}
          <div className="bg-prob-fill/45" style={{ width: `${s.pred.away * 100}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-[0.7rem] tabular-nums text-muted">
          <span className={s.actual === "home" ? "font-semibold text-text" : ""}>
            {pct(s.pred.home)}
          </span>
          {s.kind === "1x2" && (
            <span className={s.actual === "draw" ? "font-semibold text-text" : ""}>
              {pct(s.pred.draw)} draw
            </span>
          )}
          <span className={s.actual === "away" ? "font-semibold text-text" : ""}>
            {pct(s.pred.away)}
          </span>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border pt-2 text-[0.7rem] text-muted">
        <span>
          Called: <span className="text-text">{RESULT_LABEL[s.topPick](s)}</span>
        </span>
        <span>
          Actual: <span className="text-text">{RESULT_LABEL[s.actual](s)}</span>
        </span>
        <span className="ml-auto tabular-nums">
          gave it <span className="font-semibold text-text">{pct(s.pActual, 0)}</span> · RPS{" "}
          <span className={s.rps <= s.baselineRps ? "text-emerald-500" : "text-rose-400"}>
            {s.rps.toFixed(3)}
          </span>
        </span>
      </div>
    </Link>
  );
}

export function Scorecard() {
  const predictions = useStore((s) => s.predictions)!;
  const card = useMemo(
    () => buildScorecard(predictions.schedule ?? [], makePredictor(predictions)),
    [predictions],
  );
  const backtest = predictions.meta.model_metrics?.rps_test ?? null;

  if (card.n === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <h1 className="text-step-4 font-extrabold">Scorecard</h1>
        <p className="mt-2 text-muted">
          No matches have been played yet. Once the tournament kicks off on 11 June 2026, this page
          marks the model's homework — grading the forecast it made before each game against what
          actually happened.
        </p>
      </div>
    );
  }

  const beatsBaseline = card.skill >= 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-step-4 font-extrabold">Scorecard</h1>
      <p className="mt-1 text-muted">
        How accurate has the model been? For each of the {card.n} matches played so far, we re-derive
        the forecast it would have made before kickoff and grade the probability it placed on the
        actual result — no cherry-picking, proper scoring rules only.
      </p>

      {/* Headline grade. */}
      <div className="mt-5 flex items-stretch gap-4 rounded-2xl border border-border bg-surface-2/40 p-4">
        <div className="flex flex-col items-center justify-center rounded-xl bg-surface px-5 py-3">
          <div
            className={`font-display text-step-6 font-extrabold leading-none ${
              beatsBaseline ? "text-accent" : "text-rose-400"
            }`}
          >
            {card.grade}
          </div>
          <div className="mt-1 text-[0.7rem] uppercase tracking-wide text-muted">grade</div>
        </div>
        <div className="flex flex-col justify-center">
          <div className="text-step-2 font-bold tabular-nums">{card.score}/100 foresight</div>
          <p className="mt-1 text-sm text-muted">{GRADE_NOTE[card.grade]}</p>
          <p className="mt-0.5 text-[0.7rem] text-muted">
            Skill vs a blind 1/3 guess:{" "}
            <span className={beatsBaseline ? "text-emerald-500" : "text-rose-400"}>
              {card.skill >= 0 ? "+" : ""}
              {(card.skill * 100).toFixed(0)}%
            </span>
          </p>
        </div>
      </div>

      {/* Stat grid. */}
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCallout
          label="Winner called"
          value={pct(card.decisiveAccuracy, 0)}
          sub={`on ${card.decisiveN} decisive game${card.decisiveN === 1 ? "" : "s"}`}
        />
        <StatCallout
          label="Top pick correct"
          value={pct(card.accuracy, 0)}
          sub={`${card.draws} of ${card.n} were draws`}
        />
        <StatCallout
          label="Mean RPS"
          value={card.meanRps.toFixed(3)}
          sub={`coin-flip: ${card.baselineRps.toFixed(3)}`}
        />
        <StatCallout
          label="Exact scores"
          value={card.exactScores}
          sub={backtest != null ? `backtest RPS ${backtest.toFixed(3)}` : "likeliest scoreline hit"}
        />
      </div>

      <div className="mt-5">
        <Explainer title="How the scoring works">
          <p>
            The model never gets to peek. predictions.json ships each team's attack and defence
            ratings, so we can reproduce the <strong>exact 1X2 forecast it would have made before
            kickoff</strong> and compare it to the result — the same forecast you'd have seen on the
            Match Center page the morning of the game.
          </p>
          <p>
            <strong>Winner called</strong> asks the fair question — on games that produced a winner,
            did the model lean to the right team? <strong>Top pick correct</strong> is stricter: it
            counts a draw as a miss unless <em>draw</em> was the single most likely outcome, which it
            almost never is for any forecaster. So a draw-heavy run punishes it hard.
          </p>
          <p>
            <strong>RPS</strong> (Ranked Probability Score) and <strong>Brier</strong> grade the whole
            probability vector, not just the top pick — a confident wrong call (an 85% favourite that
            draws) costs far more than a hedged one. Lower is better. We benchmark against a no-skill
            <em> 1/3-1/3-1/3</em> guess: green RPS beat the coin-flip on that game, red didn't. The
            grade is the model's RPS skill over that baseline across all games.
          </p>
          {backtest != null && (
            <p>
              For reference, on its historical backtest the model scored an RPS of{" "}
              <strong>{backtest.toFixed(3)}</strong>. Live tournament football — especially a cluster
              of opening-round draws — is a tougher test than the average historical fixture.
            </p>
          )}
        </Explainer>
      </div>

      <div className="mt-5 space-y-2">
        <h2 className="text-sm font-bold text-muted">Every graded match</h2>
        {card.scored.map((s) => (
          <ScoreRow key={s.match.match} s={s} />
        ))}
      </div>

      <p className="mt-4 text-[0.7rem] text-muted">
        Scores update automatically as more results come in. A handful of games is a small sample —
        one tournament can't separate a good model from a lucky one, which is exactly why the proper
        scoring rules above matter more than the win/loss tally.
      </p>
    </div>
  );
}
