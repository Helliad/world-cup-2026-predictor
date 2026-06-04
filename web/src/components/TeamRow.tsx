import { Link } from "react-router-dom";
import { pct } from "../lib/format";
import type { DataConfidence } from "../types";
import { Bar } from "./Bar";
import { ConfidenceTag } from "./ConfidenceTag";
import { ProbabilityValue } from "./ProbabilityValue";
import { TeamBadge } from "./TeamBadge";

interface TeamRowProps {
  rank?: number;
  team: string;
  group: string;
  prob: number;
  confidence?: DataConfidence;
  delta?: number; // change vs the unconditional value (what-if)
  onPin?: () => void;
  pinned?: boolean;
  pinTitle?: string;
}

export function TeamRow({
  rank,
  team,
  group,
  prob,
  confidence = "high",
  delta,
  onPin,
  pinned,
  pinTitle = "Pin this outcome",
}: TeamRowProps) {
  return (
    <div className="flex items-center gap-2">
      {rank !== undefined && (
        <span className="w-6 shrink-0 text-right text-step-0 tabular-nums text-muted">{rank}</span>
      )}
      <Link
        to={`/team/${encodeURIComponent(team)}`}
        className="-mx-1 flex min-w-0 flex-1 items-center gap-3 rounded-lg px-1 py-2 hover:bg-surface-2/60"
      >
        <TeamBadge team={team} className="h-8 w-8" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate font-semibold">{team}</span>
            <span className="text-xs text-muted">Grp {group}</span>
            <ConfidenceTag level={confidence} />
          </div>
          <div className="mt-1.5">
            <Bar value={prob} ariaLabel={`${team}: ${pct(prob)} chance`} />
          </div>
        </div>
        <div className="flex w-[4.5rem] items-center justify-end gap-1">
          {delta !== undefined && Math.abs(delta) >= 0.005 && (
            <span
              className={`text-[0.7rem] tabular-nums ${delta > 0 ? "text-prob-fill" : "text-warning"}`}
            >
              {delta > 0 ? "▲" : "▼"}
              {pct(Math.abs(delta), 0)}
            </span>
          )}
          <ProbabilityValue p={prob} className="font-bold" />
        </div>
      </Link>
      {onPin && (
        <button
          type="button"
          onClick={onPin}
          aria-pressed={pinned}
          title={pinTitle}
          className={`shrink-0 rounded-md border px-2 py-1 text-[0.7rem] font-semibold transition-colors ${
            pinned
              ? "border-accent bg-accent/10 text-accent"
              : "border-border text-muted hover:text-text"
          }`}
        >
          {pinned ? "Pinned" : "Pin"}
        </button>
      )}
    </div>
  );
}
