import { Link } from "react-router-dom";
import { pct } from "../lib/format";
import type { Predictor } from "../lib/predict";
import { ROUND_SHORT, matchSides, venueText } from "../lib/schedule";
import type { ScheduleMatch } from "../types";
import { TeamBadge } from "./TeamBadge";

// One row in the Schedule list: the matchup (real teams once known, otherwise the
// official slot descriptor), and either the final score or a compact model
// prediction. Links through to the per-match detail page.
function Side({
  team,
  label,
  host,
  align,
  winner,
}: {
  team: string | null;
  label: string;
  host: boolean;
  align: "left" | "right";
  winner: boolean;
}) {
  const dir = align === "right" ? "flex-row-reverse text-right" : "";
  if (!team) {
    return (
      <div className={`flex min-w-0 items-center gap-2 ${dir}`}>
        <span className="truncate text-sm italic text-muted">{label}</span>
      </div>
    );
  }
  return (
    <div className={`flex min-w-0 items-center gap-2 ${dir}`}>
      <TeamBadge team={team} className="h-6 w-6 text-[0.6rem]" />
      <span className={`truncate text-sm ${winner ? "font-bold" : "font-medium"}`}>
        {team}
        {host && <span className="ml-1 text-[0.6rem] uppercase text-accent">host</span>}
      </span>
    </div>
  );
}

export function ScheduleMatchRow({
  match,
  predictor,
}: {
  match: ScheduleMatch;
  predictor: Predictor;
}) {
  const s = matchSides(match);
  const played = match.status === "played" && match.score;
  const hostAdv = match.host && match.host === match.home ? predictor.hostAdvantage : 0;
  const canPredict = s.bothKnown && predictor.known(s.homeTeam!, s.awayTeam!);

  return (
    <Link
      to={`/match/${match.match}`}
      className="block rounded-lg border border-border bg-surface px-3 py-2.5 transition-colors hover:border-accent/50"
    >
      <div className="mb-1.5 flex items-center justify-between text-[0.7rem] uppercase tracking-wide text-muted">
        <span>
          {ROUND_SHORT[match.round]}
          {match.group ? ` ${match.group}` : ""} · {venueText(match)}
        </span>
        {played ? (
          <span className="font-semibold text-accent">FT</span>
        ) : (
          <span className="text-muted/70">#{match.match}</span>
        )}
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <Side
          team={s.homeTeam}
          label={s.homeLabel}
          host={match.host === match.home}
          align="left"
          winner={!!played && match.winner === s.homeTeam}
        />
        {played ? (
          <span className="shrink-0 rounded bg-surface-2 px-2 py-0.5 text-sm font-bold tabular-nums">
            {match.score!.home}–{match.score!.away}
          </span>
        ) : (
          <span className="shrink-0 text-xs text-muted">v</span>
        )}
        <Side
          team={s.awayTeam}
          label={s.awayLabel}
          host={false}
          align="right"
          winner={!!played && match.winner === s.awayTeam}
        />
      </div>

      {!played && canPredict && <Prediction match={match} predictor={predictor} hostAdv={hostAdv} />}
      {!played && !canPredict && (
        <div className="mt-1.5 text-center text-[0.7rem] text-muted">
          teams decided by earlier results
        </div>
      )}
      {played && match.decided_by && match.decided_by !== "regulation" && (
        <div className="mt-1.5 text-center text-[0.7rem] text-muted">
          {match.winner} won {match.decided_by === "penalties" ? "on penalties" : "after extra time"}
        </div>
      )}
    </Link>
  );
}

// Compact 1X2 bar for both group games and decided knockout ties (where a draw
// rolls into extra time / penalties, so we also surface who advances).
function Prediction({
  match,
  predictor,
  hostAdv,
}: {
  match: ScheduleMatch;
  predictor: Predictor;
  hostAdv: number;
}) {
  const home = match.home!;
  const away = match.away!;
  const o = predictor.outcome(home, away, hostAdv);
  const advance =
    match.round !== "group" ? predictor.knockoutWinProb(home, away) : null;

  return (
    <div className="mt-2">
      <div className="flex h-2 overflow-hidden rounded-full" aria-hidden="true">
        <div className="bg-prob-fill" style={{ width: `${o.homeWin * 100}%` }} />
        <div className="bg-muted/40" style={{ width: `${o.draw * 100}%` }} />
        <div className="bg-prob-fill/45" style={{ width: `${o.awayWin * 100}%` }} />
      </div>
      <div className="mt-1 flex justify-between text-[0.7rem] tabular-nums text-muted">
        <span className="font-semibold text-text">{pct(o.homeWin)}</span>
        <span>{pct(o.draw)} draw</span>
        <span className="font-semibold text-text">{pct(o.awayWin)}</span>
      </div>
      {advance !== null && (
        <div className="mt-0.5 text-center text-[0.7rem] text-muted">
          to advance: <span className="text-text">{home} {pct(advance)}</span> ·{" "}
          <span className="text-text">{away} {pct(1 - advance)}</span>
        </div>
      )}
    </div>
  );
}
