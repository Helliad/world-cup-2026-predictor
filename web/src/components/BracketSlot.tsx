import { Link } from "react-router-dom";
import type { BracketNode } from "../lib/bracket";
import { pct } from "../lib/format";
import { type ConditionKind, makeCondition } from "../lib/recompute";
import { useStore } from "../store/store";
import { TeamBadge } from "./TeamBadge";

// Round r occupant "winning their tie" means advancing to round r+1.
const ADVANCE_KIND: (ConditionKind | null)[] = ["r16", "qf", "sf", "final", "champion", null];

export function BracketSlot({ node, round }: { node: BracketNode; round: number }) {
  const add = useStore((s) => s.addCondition);
  const remove = useStore((s) => s.removeCondition);
  const conditions = useStore((s) => s.conditions);

  if (!node.team) {
    return (
      <div className="rounded-md border border-dashed border-border px-2 py-2 text-center text-xs text-muted">
        TBD
      </div>
    );
  }

  const kind = ADVANCE_KIND[round];
  const cond = kind ? makeCondition(node.team, kind) : null;
  const pinned = cond ? conditions.some((c) => c.id === cond.id) : false;

  return (
    <div
      className={`flex items-center gap-1.5 rounded-md border bg-surface px-2 py-1.5 ${
        pinned ? "border-accent" : "border-border"
      }`}
    >
      <Link
        to={`/team/${encodeURIComponent(node.team)}`}
        className="flex min-w-0 flex-1 items-center gap-1.5 hover:text-accent"
      >
        <TeamBadge team={node.team} className="h-5 w-5 text-[0.55rem]" />
        <span className="min-w-0 flex-1 truncate text-xs font-medium">{node.team}</span>
      </Link>
      <span className="shrink-0 text-[0.65rem] tabular-nums text-muted" title="Probability this team reaches this slot">
        {pct(node.prob, 0)}
      </span>
      {cond && (
        <button
          type="button"
          onClick={() => (pinned ? remove(cond.id) : add(cond))}
          aria-pressed={pinned}
          aria-label={`Assume ${node.team} advance from here`}
          title={pinned ? "Pinned — assume they advance" : "What if they advance?"}
          className={`shrink-0 text-sm leading-none ${pinned ? "text-accent" : "text-muted hover:text-text"}`}
        >
          {pinned ? "★" : "☆"}
        </button>
      )}
    </div>
  );
}
