import { useMemo } from "react";
import { Explainer } from "../components/Explainer";
import { StatCallout } from "../components/StatCallout";
import { TeamRow } from "../components/TeamRow";
import { pct } from "../lib/format";
import { makeCondition } from "../lib/recompute";
import { useStore } from "../store/store";
import { useProbabilities } from "../store/useProbabilities";

// Landing view + share target (§7.2). First paint shows the headline title race.
export function TitleRace() {
  const predictions = useStore((s) => s.predictions)!;
  const conditions = useStore((s) => s.conditions);
  const add = useStore((s) => s.addCondition);
  const remove = useStore((s) => s.removeCondition);
  const dp = useProbabilities();

  const marginal = useMemo(() => {
    const m: Record<string, number> = {};
    for (const t of predictions.teams) m[t.team] = t.p_win;
    return m;
  }, [predictions]);

  const teams = useMemo(
    () =>
      predictions.teams
        .map((t) => ({ t, p: dp.byTeam[t.team]?.win ?? t.p_win }))
        .sort((a, b) => b.p - a.p),
    [predictions, dp],
  );

  const meta = predictions.meta;
  const fav = teams[0];

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-step-5 font-extrabold leading-tight tracking-tight">
        Who wins the 2026 World Cup?
      </h1>
      <p className="mt-2 text-step-1 text-muted">
        Championship probability from {meta.n_simulations.toLocaleString()} Monte-Carlo simulations of
        all 104 matches, driven by a Dixon-Coles statistical model.
      </p>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCallout label="Favourite" value={fav.t.team} sub={`${pct(fav.p)} to win`} />
        <StatCallout label="Teams" value="48" />
        <StatCallout label="Matches" value="104" />
        <StatCallout label="Simulations" value={(meta.n_simulations / 1000).toFixed(0) + "k"} />
      </div>

      <div className="mt-6">
        <Explainer title="What these percentages mean">
          <p>
            Each number is how often a team is champion across{" "}
            {meta.n_simulations.toLocaleString()} simulated tournaments — not a prediction of who{" "}
            <em>will</em> win. With 48 teams and seven knockout rounds to survive, even the favourite
            is far more likely to lose than to win, so the field is spread thin.
          </p>
          <p>
            Every figure carries a small Monte Carlo margin of error (about ±0.1% here), so a 12.1%
            vs 11.8% gap is noise, not a real ranking. Tap any team for its full stage-by-stage odds,
            or pin a “what if” (e.g. on the Bracket page) to see these numbers recompute — a{" "}
            <span className="text-prob-fill">▲</span>/<span className="text-warning">▼</span> then
            shows the change versus the unconditional value.
          </p>
        </Explainer>
      </div>

      <div className="mt-6">
        <h2 className="mb-2 flex items-center gap-2 text-step-2 font-bold">
          Title race
          {dp.active && <span className="text-sm font-normal text-accent">· conditional</span>}
        </h2>
        <ol className="divide-y divide-border rounded-xl border border-border bg-surface px-3">
          {teams.map(({ t, p }, i) => {
            const cond = makeCondition(t.team, "champion");
            const pinned = conditions.some((c) => c.id === cond.id);
            return (
              <li key={t.team}>
                <TeamRow
                  rank={i + 1}
                  team={t.team}
                  group={t.group}
                  prob={p}
                  confidence={t.data_confidence}
                  delta={dp.active ? p - marginal[t.team] : undefined}
                  pinned={pinned}
                  pinTitle={`Assume ${t.team} win the title`}
                  onPin={() => (pinned ? remove(cond.id) : add(cond))}
                />
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}
