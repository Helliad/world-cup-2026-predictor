import { flagUrl } from "../lib/flags";
import { teamAbbr } from "../lib/format";

// A small country flag, or — for any unmapped name such as a TBD/playoff
// placeholder — a neutral initials badge as a fallback. Decorative only
// (the flag img is aria-hidden); the team name is the accessible label
// wherever this appears. object-cover fills the box at any aspect ratio.
export function TeamBadge({ team, className = "h-8 w-8" }: { team: string; className?: string }) {
  const flag = flagUrl(team);

  if (flag) {
    return (
      <img
        src={flag}
        alt=""
        aria-hidden="true"
        loading="lazy"
        className={`shrink-0 rounded-md border border-border object-cover ${className}`}
      />
    );
  }

  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-md border border-border bg-surface-2 text-[0.7rem] font-bold tracking-wide text-muted ${className}`}
      aria-hidden="true"
    >
      {teamAbbr(team)}
    </span>
  );
}
