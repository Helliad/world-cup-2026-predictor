import { teamAbbr } from "../lib/format";

// Neutral initials badge — no flags or stadium kitsch (§7.1). Decorative only;
// the team name is the accessible label wherever this appears.
export function TeamBadge({ team, className = "h-8 w-8" }: { team: string; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-md border border-border bg-surface-2 text-[0.7rem] font-bold tracking-wide text-muted ${className}`}
      aria-hidden="true"
    >
      {teamAbbr(team)}
    </span>
  );
}
