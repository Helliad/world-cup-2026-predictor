import { Link } from "react-router-dom";
import { pct } from "../lib/format";
import type { Fixture } from "../types";
import { TeamBadge } from "./TeamBadge";

// One group-stage fixture with its 1X2 match probabilities. The segmented bar
// reinforces magnitude; the numbers are always shown as text (§7.4).
export function MatchOdds({ fixture: f }: { fixture: Fixture }) {
  const teamLink = (team: string, host: boolean) => (
    <Link
      to={`/team/${encodeURIComponent(team)}`}
      className="flex min-w-0 items-center gap-2 hover:text-accent"
    >
      <TeamBadge team={team} className="h-6 w-6 text-[0.6rem]" />
      <span className="truncate text-sm font-medium">
        {team}
        {host && <span className="ml-1 text-[0.6rem] uppercase text-accent">host</span>}
      </span>
    </Link>
  );

  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        {teamLink(f.home, f.host === f.home)}
        <span className="shrink-0 text-[0.65rem] tabular-nums text-muted">
          {f.exp_home.toFixed(1)}–{f.exp_away.toFixed(1)} xG
        </span>
        <div className="flex min-w-0 flex-row-reverse">{teamLink(f.away, false)}</div>
      </div>

      <div
        className="mt-2 flex h-2 overflow-hidden rounded-full"
        role="img"
        aria-label={`${f.home} win ${pct(f.home_win)}, draw ${pct(f.draw)}, ${f.away} win ${pct(f.away_win)}`}
      >
        <div className="bg-prob-fill" style={{ width: `${f.home_win * 100}%` }} />
        <div className="bg-muted/40" style={{ width: `${f.draw * 100}%` }} />
        <div className="bg-prob-fill/45" style={{ width: `${f.away_win * 100}%` }} />
      </div>

      <div className="mt-1 flex justify-between text-[0.7rem] tabular-nums">
        <span className="font-semibold">{pct(f.home_win)} win</span>
        <span className="text-muted">{pct(f.draw)} draw</span>
        <span className="font-semibold">{pct(f.away_win)} win</span>
      </div>
    </div>
  );
}
