import { Link, useParams } from "react-router-dom";
import { Bar } from "../components/Bar";
import { ProbabilityValue } from "../components/ProbabilityValue";
import { StatCallout } from "../components/StatCallout";
import { TeamBadge } from "../components/TeamBadge";
import { CONFIDENCE_TEXT, pct } from "../lib/format";
import { type ConditionKind, makeCondition } from "../lib/recompute";
import { useStore } from "../store/store";
import { useProbabilities } from "../store/useProbabilities";
import { STAGE_LABELS, type StageKey } from "../types";

const STAGE_ORDER: StageKey[] = ["advance", "r16", "qf", "sf", "final", "win"];
const STAGE_KIND: Record<StageKey, ConditionKind> = {
  advance: "advance",
  r16: "r16",
  qf: "qf",
  sf: "sf",
  final: "final",
  win: "champion",
};

export function TeamDetail() {
  const { id } = useParams();
  const team = decodeURIComponent(id ?? "");
  const predictions = useStore((s) => s.predictions)!;
  const conditions = useStore((s) => s.conditions);
  const add = useStore((s) => s.addCondition);
  const remove = useStore((s) => s.removeCondition);
  const dp = useProbabilities();

  const info = predictions.teams.find((t) => t.team === team);
  if (!info) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        Unknown team.{" "}
        <Link className="text-accent underline" to="/">
          Back to the title race
        </Link>
        .
      </div>
    );
  }

  const probs = dp.byTeam[team] ?? {
    advance: info.p_advance,
    r16: info.p_r16,
    qf: info.p_qf,
    sf: info.p_sf,
    final: info.p_final,
    win: info.p_win,
  };
  const marginal: Record<StageKey, number> = {
    advance: info.p_advance,
    r16: info.p_r16,
    qf: info.p_qf,
    sf: info.p_sf,
    final: info.p_final,
    win: info.p_win,
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <Link to="/" className="text-sm text-muted hover:text-text">
        ← Title race
      </Link>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
        <TeamBadge team={team} className="h-9 w-12" />
        <h1 className="text-step-5 font-extrabold tracking-tight">{team}</h1>
        <span className="text-muted">Group {info.group}</span>
        {info.data_confidence !== "high" && (
          <span className="rounded border border-warning/40 px-1.5 py-0.5 text-xs text-warning">
            {CONFIDENCE_TEXT[info.data_confidence]}
          </span>
        )}
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3">
        <StatCallout label="Win title" value={pct(probs.win)} />
        <StatCallout label="Reach final" value={pct(probs.final)} />
        <StatCallout label="Advance" value={pct(probs.advance)} />
      </div>

      <h2 className="mt-8 mb-2 flex items-center gap-2 text-step-2 font-bold">
        Stage-by-stage {dp.active && <span className="text-sm font-normal text-accent">· conditional</span>}
      </h2>
      <ul className="divide-y divide-border rounded-xl border border-border bg-surface">
        {STAGE_ORDER.map((stage) => {
          const cond = makeCondition(team, STAGE_KIND[stage]);
          const pinned = conditions.some((c) => c.id === cond.id);
          const p = probs[stage];
          const d = dp.active ? p - marginal[stage] : undefined;
          return (
            <li key={stage} className="flex items-center gap-3 px-4 py-2.5">
              <span className="w-28 shrink-0 text-sm text-muted">{STAGE_LABELS[stage]}</span>
              <div className="flex-1">
                <Bar value={p} ariaLabel={`${team} ${STAGE_LABELS[stage]}: ${pct(p)}`} />
              </div>
              {d !== undefined && Math.abs(d) >= 0.005 && (
                <span className={`text-[0.7rem] tabular-nums ${d > 0 ? "text-prob-fill" : "text-warning"}`}>
                  {d > 0 ? "▲" : "▼"}
                  {pct(Math.abs(d), 0)}
                </span>
              )}
              <ProbabilityValue p={p} className="w-14 text-right font-semibold" />
              <button
                type="button"
                onClick={() => (pinned ? remove(cond.id) : add(cond))}
                aria-pressed={pinned}
                title={`Assume ${team} ${STAGE_LABELS[stage].toLowerCase()}`}
                className={`shrink-0 rounded border px-1.5 py-0.5 text-[0.65rem] font-medium ${
                  pinned ? "border-accent text-accent" : "border-border text-muted hover:text-text"
                }`}
              >
                {pinned ? "pinned" : "what if"}
              </button>
            </li>
          );
        })}
      </ul>

      <h2 className="mt-8 mb-2 text-step-2 font-bold">Model strength</h2>
      <div className="grid grid-cols-2 gap-3">
        <StatCallout
          label="Attack (α)"
          value={info.alpha >= 0 ? `+${info.alpha.toFixed(2)}` : info.alpha.toFixed(2)}
          sub="higher = stronger attack"
        />
        <StatCallout
          label="Defence (β)"
          value={info.beta >= 0 ? `+${info.beta.toFixed(2)}` : info.beta.toFixed(2)}
          sub="lower = tighter defence"
        />
      </div>
      <p className="mt-3 text-xs text-muted">
        α and β are the team’s fitted Dixon-Coles attack and defence parameters (mean-centred attack,
        Σα = 0). Expected goals for a fixture are exp(α<sub>home</sub> + β<sub>away</sub> + home term).
      </p>
    </div>
  );
}
