import { Link } from "react-router-dom";
import { pct } from "../lib/format";
import { makeCondition } from "../lib/recompute";
import { useStore } from "../store/store";
import { useProbabilities } from "../store/useProbabilities";
import type { GroupRow } from "../types";
import { Bar } from "./Bar";
import { ConfidenceTag } from "./ConfidenceTag";
import { ProbabilityValue } from "./ProbabilityValue";
import { TeamBadge } from "./TeamBadge";

// Compact group standings with advance probabilities (§7.2). Re-sorts live under
// "what if" conditions; "tops" pins "assume this team wins the group".
export function GroupTable({ letter, rows }: { letter: string; rows: GroupRow[] }) {
  const add = useStore((s) => s.addCondition);
  const conditions = useStore((s) => s.conditions);
  const dp = useProbabilities();

  const display = rows
    .map((r) => ({ ...r, p: dp.byTeam[r.team]?.advance ?? r.p_advance }))
    .sort((a, b) => b.p - a.p);

  return (
    <section className="rounded-xl border border-border bg-surface">
      <header className="flex items-center justify-between border-b border-border px-4 py-2">
        <h3 className="text-step-2 font-bold">Group {letter}</h3>
        <span className="text-[0.7rem] uppercase tracking-wide text-muted">P(advance)</span>
      </header>
      <ul className="divide-y divide-border">
        {display.map((r, i) => {
          const cond = makeCondition(r.team, "group_winner");
          const pinned = conditions.some((c) => c.id === cond.id);
          return (
            <li key={r.team} className="flex items-center gap-2 px-3 py-2">
              <span className="w-4 text-xs tabular-nums text-muted">{i + 1}</span>
              <Link
                to={`/team/${encodeURIComponent(r.team)}`}
                className="flex min-w-0 flex-1 items-center gap-2 rounded-md py-1 hover:bg-surface-2/60"
              >
                <TeamBadge team={r.team} className="h-7 w-7" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-medium">{r.team}</span>
                    <ConfidenceTag level={r.data_confidence} />
                  </div>
                  <div className="mt-1">
                    <Bar value={r.p} ariaLabel={`${r.team}: ${pct(r.p)} to advance`} />
                  </div>
                </div>
                <span className="w-12 shrink-0 text-right text-[0.7rem] tabular-nums text-muted">
                  {r.exp_points.toFixed(1)} pts
                </span>
                <ProbabilityValue p={r.p} className="w-11 shrink-0 text-right text-sm font-semibold" />
              </Link>
              <button
                type="button"
                onClick={() => add(cond)}
                aria-pressed={pinned}
                title={`Assume ${r.team} win Group ${letter}`}
                className={`shrink-0 rounded border px-1.5 py-0.5 text-[0.65rem] font-medium ${
                  pinned ? "border-accent text-accent" : "border-border text-muted hover:text-text"
                }`}
              >
                {pinned ? "✓ top" : "top"}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
