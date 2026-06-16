import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Explainer } from "../components/Explainer";
import { TeamBadge } from "../components/TeamBadge";
import type { ScoredMatch } from "../lib/accuracy";
import { buildScorecard } from "../lib/accuracy";
import { pct } from "../lib/format";
import { makePredictor } from "../lib/predict";
import { ROUND_SHORT, venueText } from "../lib/schedule";
import { useStore } from "../store/store";

// Scorecard: marks the model's homework. For every match that's been played we
// re-derive the call it would have made before kickoff — the single outcome it
// gave the highest probability — and check whether that outcome happened.

const GRADE_NOTE: Record<string, string> = {
  A: "Calling matches at an elite clip.",
  B: "Reading the tournament well.",
  C: "Getting more right than not.",
  D: "Roughly a coin-flip so far.",
  F: "A cold, draw-heavy start.",
  "—": "No matches scored yet.",
};

const RESULT_LABEL: Record<ScoredMatch["actual"], (s: ScoredMatch) => string> = {
  home: (s) => `${s.home} win`,
  away: (s) => `${s.away} win`,
  draw: () => "Draw",
};

type Filter = "all" | "correct" | "wrong";

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

function ScoreRow({ s }: { s: ScoredMatch }) {
  const m = s.match;
  const score = m.score;
  // Highlight the side the model called (home/away); draws have no side.
  const calledHome = s.topPick === "home";
  const calledAway = s.topPick === "away";
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
        <Mark ok={s.correct} />
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

      {/* Pre-match probabilities; the called segment is emphasised. */}
      <div className="mt-2">
        <div className="flex h-2 overflow-hidden rounded-full" aria-hidden="true">
          <div
            className={calledHome ? "bg-prob-fill" : "bg-prob-fill/40"}
            style={{ width: `${s.pred.home * 100}%` }}
          />
          {s.pred.draw > 0 && (
            <div
              className={s.topPick === "draw" ? "bg-muted/70" : "bg-muted/30"}
              style={{ width: `${s.pred.draw * 100}%` }}
            />
          )}
          <div
            className={calledAway ? "bg-prob-fill" : "bg-prob-fill/40"}
            style={{ width: `${s.pred.away * 100}%` }}
          />
        </div>
        <div className="mt-1 flex justify-between text-[0.7rem] tabular-nums text-muted">
          <span className={calledHome ? "font-semibold text-text" : ""}>{pct(s.pred.home)}</span>
          {s.pred.draw > 0 && (
            <span className={s.topPick === "draw" ? "font-semibold text-text" : ""}>
              {pct(s.pred.draw)} draw
            </span>
          )}
          <span className={calledAway ? "font-semibold text-text" : ""}>{pct(s.pred.away)}</span>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-border pt-2 text-[0.7rem] text-muted">
        <span>
          Called:{" "}
          <span className="text-text">
            {RESULT_LABEL[s.topPick](s)} ({pct(s.topProb, 0)})
          </span>
        </span>
        <span className="ml-auto">
          Actual: <span className="text-text">{RESULT_LABEL[s.actual](s)}</span>
        </span>
      </div>
    </Link>
  );
}

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "correct", label: "Correct" },
  { key: "wrong", label: "Wrong" },
];

export function Scorecard() {
  const predictions = useStore((s) => s.predictions)!;
  const [filter, setFilter] = useState<Filter>("all");
  const card = useMemo(
    () => buildScorecard(predictions.schedule ?? [], makePredictor(predictions)),
    [predictions],
  );

  if (card.n === 0) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6">
        <h1 className="text-step-4 font-extrabold">Scorecard</h1>
        <p className="mt-2 text-muted">
          No matches have been played yet. Once the tournament kicks off on 11 June 2026, this page
          marks the model's homework — checking whether the outcome it called for each game (home
          win, draw, or away win) is the one that happened.
        </p>
      </div>
    );
  }

  const shown = card.scored.filter((s) =>
    filter === "all" ? true : filter === "correct" ? s.correct : !s.correct,
  );
  const counts: Record<Filter, number> = { all: card.n, correct: card.correct, wrong: card.wrong };

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-step-4 font-extrabold">Scorecard</h1>
      <p className="mt-1 text-muted">
        How accurate has the model been? For each of the {card.n} matches played so far, it "calls"
        the outcome it gave the highest chance — a home win, a draw, or an away win. If that's what
        happened, it's a hit.
      </p>

      {/* Headline: call accuracy + grade. */}
      <div className="mt-5 flex items-stretch gap-4 rounded-2xl border border-border bg-surface-2/40 p-4">
        <div className="flex flex-col items-center justify-center rounded-xl bg-surface px-5 py-3">
          <div
            className={`font-display text-step-6 font-extrabold leading-none ${
              card.accuracy >= 0.5 ? "text-accent" : "text-rose-400"
            }`}
          >
            {card.grade}
          </div>
          <div className="mt-1 text-[0.7rem] uppercase tracking-wide text-muted">grade</div>
        </div>
        <div className="flex flex-col justify-center">
          <div className="text-step-3 font-extrabold tabular-nums">{pct(card.accuracy, 0)} called right</div>
          <p className="mt-1 text-sm text-muted">
            <span className="font-semibold text-text">{card.correct}</span> of {card.n} matches —{" "}
            {GRADE_NOTE[card.grade]}
          </p>
        </div>
      </div>

      <div className="mt-4">
        <Explainer title="How the scoring works">
          <p>
            The model never gets to peek. predictions.json ships each team's attack and defence
            ratings, so we reproduce the <strong>exact forecast it would have made before
            kickoff</strong> — the same home/draw/away split you'd have seen on the Match Center page
            the morning of the game.
          </p>
          <p>
            Its <strong>call</strong> is simply the outcome with the highest probability. The call is
            a hit if that outcome happens, a miss otherwise — the scoreline itself doesn't matter,
            only home win vs draw vs away win.
          </p>
          <p>
            One honest caveat: a draw is rarely any forecaster's single most likely outcome, so a run
            of drawn games is hard on the tally — not because the model rated a draw impossible, but
            because some other result always edged it. Use the filters to see exactly which calls
            landed and which didn't.
          </p>
        </Explainer>
      </div>

      {/* Correct / wrong filters. */}
      <div className="mt-5 flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFilter(f.key)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === f.key
                ? "bg-accent text-white"
                : "border border-border text-muted hover:text-text"
            }`}
          >
            {f.label} ({counts[f.key]})
          </button>
        ))}
      </div>

      <div className="mt-4 space-y-2">
        {shown.map((s) => (
          <ScoreRow key={s.match.match} s={s} />
        ))}
        {shown.length === 0 && (
          <p className="text-muted">
            No {filter === "correct" ? "correct" : "wrong"} calls{filter === "wrong" ? " — yet" : ""}.
          </p>
        )}
      </div>

      <p className="mt-4 text-[0.7rem] text-muted">
        Scores update automatically as more results come in. A handful of games is a small sample —
        one tournament can't fully separate a sharp model from a lucky one.
      </p>
    </div>
  );
}
