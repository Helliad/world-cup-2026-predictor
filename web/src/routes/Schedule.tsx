import { useMemo, useState } from "react";
import { Explainer } from "../components/Explainer";
import { ScheduleMatchRow } from "../components/ScheduleMatchRow";
import { makePredictor } from "../lib/predict";
import { ROUND_LABEL, byDate } from "../lib/schedule";
import { useStore } from "../store/store";
import type { MatchRound } from "../types";

type Filter = "all" | MatchRound;

const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "group", label: "Groups" },
  { key: "r32", label: "Round of 32" },
  { key: "r16", label: "Round of 16" },
  { key: "qf", label: "Quarter-finals" },
  { key: "sf", label: "Semis" },
  { key: "third", label: "3rd place" },
  { key: "final", label: "Final" },
];

// Match Center: every one of the 104 matches by date, with the actual result once
// played or the model's prediction until then. The single page the user keeps
// returning to as the tournament unfolds.
export function Schedule() {
  const predictions = useStore((s) => s.predictions)!;
  const [filter, setFilter] = useState<Filter>("all");
  const predictor = useMemo(() => makePredictor(predictions), [predictions]);

  const schedule = predictions.schedule ?? [];
  const days = useMemo(() => {
    const subset = filter === "all" ? schedule : schedule.filter((m) => m.round === filter);
    return byDate(subset);
  }, [schedule, filter]);

  const played = schedule.filter((m) => m.status === "played").length;

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-step-4 font-extrabold">Match Center</h1>
      <p className="mt-1 text-muted">
        All 104 matches of the 2026 World Cup — from the opener to the final at MetLife Stadium.
        Each match shows the model's prediction until it's played, then the result.{" "}
        {played > 0 ? (
          <span className="text-text">{played} played so far.</span>
        ) : (
          <span>The tournament kicks off on 11 June 2026.</span>
        )}
      </p>

      <div className="mt-4">
        <Explainer title="How this page updates as teams progress">
          <p>
            Group games show the chance of a home win, draw, or away win. Knockout games appear with
            their official slot — “Winner Group A”, “best third-placed team”, “Winner of Match 73” —
            and fill in with real teams as earlier results decide who's there.
          </p>
          <p>
            When a result is recorded it's <strong>pinned into the simulation</strong> and the whole
            forecast is re-run: standings, the bracket, and every team's title odds re-condition on
            what has actually happened. So a shock result doesn't just update one line — it ripples
            through the Groups, Bracket, and Title Race views too.
          </p>
          <p>
            Knockout ties can't end level: the “to advance” figure folds in extra time and penalties,
            so it differs from the plain win/draw/loss split.
          </p>
        </Explainer>
      </div>

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
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-5 space-y-6">
        {days.map((day) => (
          <section key={day.date}>
            <h2 className="sticky top-14 z-10 -mx-4 bg-surface/90 px-4 py-1.5 text-sm font-bold backdrop-blur">
              {day.label}
            </h2>
            <div className="mt-2 space-y-2">
              {day.matches.map((m) => (
                <ScheduleMatchRow key={m.match} match={m} predictor={predictor} />
              ))}
            </div>
          </section>
        ))}
        {days.length === 0 && (
          <p className="text-muted">No matches in {ROUND_LABEL[filter as MatchRound]}.</p>
        )}
      </div>
    </div>
  );
}
