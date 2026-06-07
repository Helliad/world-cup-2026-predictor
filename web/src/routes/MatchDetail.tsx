import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { Explainer } from "../components/Explainer";
import { StatCallout } from "../components/StatCallout";
import { TeamBadge } from "../components/TeamBadge";
import { pct } from "../lib/format";
import { makePredictor } from "../lib/predict";
import { ROUND_LABEL, formatDate, isKnockout, matchSides, venueText } from "../lib/schedule";
import { useStore } from "../store/store";
import type { ScheduleMatch } from "../types";

// Per-match prediction page (/match/:match): the full breakdown for one fixture —
// 1X2 + expected goals, the most-likely scorelines, who advances (knockout), and
// the actual result once it's played.
export function MatchDetail() {
  const { match } = useParams();
  const predictions = useStore((s) => s.predictions)!;
  const predictor = useMemo(() => makePredictor(predictions), [predictions]);

  const no = Number(match);
  const m = predictions.schedule?.find((x) => x.match === no);

  if (!m) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10">
        Unknown match.{" "}
        <Link className="text-accent underline" to="/schedule">
          Back to the Match Center
        </Link>
        .
      </div>
    );
  }

  const s = matchSides(m);
  const played = m.status === "played" && m.score;
  const hostAdv = m.host && m.host === m.home ? predictor.hostAdvantage : 0;
  const canPredict = s.bothKnown && predictor.known(s.homeTeam!, s.awayTeam!);

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <Link to="/schedule" className="text-sm text-muted hover:text-text">
        ← Match Center
      </Link>

      <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h1 className="text-step-4 font-extrabold tracking-tight">
          {ROUND_LABEL[m.round]}
          {m.group ? ` · Group ${m.group}` : ""}
        </h1>
        <span className="text-muted">Match {m.match}</span>
      </div>
      <p className="mt-1 text-muted">
        {formatDate(m.date)} · {venueText(m)}
      </p>

      {/* Matchup header */}
      <div className="mt-5 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
        <TeamHead team={s.homeTeam} label={s.homeLabel} host={m.host === m.home} winner={!!played && m.winner === s.homeTeam} />
        <div className="text-center">
          {played ? (
            <div className="text-step-5 font-extrabold tabular-nums">
              {m.score!.home}–{m.score!.away}
            </div>
          ) : (
            <div className="text-step-3 font-bold text-muted">v</div>
          )}
        </div>
        <TeamHead team={s.awayTeam} label={s.awayLabel} host={false} winner={!!played && m.winner === s.awayTeam} alignRight />
      </div>

      {played && (
        <p className="mt-3 text-center text-sm text-muted">
          Full time{m.decided_by && m.decided_by !== "regulation" ? (
            <> — {m.winner} won {m.decided_by === "penalties" ? "on penalties" : "after extra time"}</>
          ) : null}
          .
        </p>
      )}

      {canPredict ? (
        <Forecast m={m} predictor={predictor} hostAdv={hostAdv} played={!!played} />
      ) : (
        <TbdNote m={m} />
      )}

      {m.host === m.home && m.home && (
        <p className="mt-4 text-[0.75rem] text-muted">
          {m.home} carry a reduced co-host home advantage at this venue — World Cup home advantage is
          real but smaller than in club football. Every other match is treated as neutral.
        </p>
      )}
      {predictions.meta.provisional && isKnockout(m.round) && (
        <p className="mt-2 text-[0.75rem] text-muted">
          Knockout participants and projections are provisional until the official third-place
          allocation is confirmed.
        </p>
      )}
    </div>
  );
}

function TeamHead({
  team,
  label,
  host,
  winner,
  alignRight,
}: {
  team: string | null;
  label: string;
  host: boolean;
  winner: boolean;
  alignRight?: boolean;
}) {
  const align = alignRight ? "items-end text-right" : "items-start text-left";
  if (!team) {
    return (
      <div className={`flex flex-col gap-1 ${align}`}>
        <span className="grid h-12 w-12 place-items-center rounded-md border border-border bg-surface-2 text-muted">
          ?
        </span>
        <span className="text-sm italic text-muted">{label}</span>
      </div>
    );
  }
  return (
    <Link to={`/team/${encodeURIComponent(team)}`} className={`flex flex-col gap-1 hover:text-accent ${align}`}>
      <TeamBadge team={team} className="h-12 w-12" />
      <span className={`text-step-1 ${winner ? "font-extrabold" : "font-bold"}`}>
        {team}
        {host && <span className="ml-1 align-middle text-[0.6rem] uppercase text-accent">host</span>}
      </span>
    </Link>
  );
}

function Forecast({
  m,
  predictor,
  hostAdv,
  played,
}: {
  m: ScheduleMatch;
  predictor: ReturnType<typeof makePredictor>;
  hostAdv: number;
  played: boolean;
}) {
  const home = m.home!;
  const away = m.away!;
  const o = predictor.outcome(home, away, hostAdv);
  const knockout = isKnockout(m.round);
  const advance = knockout ? predictor.knockoutWinProb(home, away) : null;
  const scorelines = predictor.topScorelines(home, away, hostAdv, 6);
  const maxP = scorelines[0]?.prob ?? 1;

  return (
    <div className="mt-6">
      <h2 className="text-sm font-bold uppercase tracking-wide text-muted">
        {played ? "Pre-match model forecast" : "Model forecast"}
      </h2>

      <div className="mt-2 grid grid-cols-3 gap-3">
        <StatCallout label={`${home} win`} value={pct(o.homeWin)} />
        <StatCallout label="Draw" value={pct(o.draw)} sub={knockout ? "→ extra time" : undefined} />
        <StatCallout label={`${away} win`} value={pct(o.awayWin)} />
      </div>

      <div className="mt-3 flex h-2.5 overflow-hidden rounded-full" aria-hidden="true">
        <div className="bg-prob-fill" style={{ width: `${o.homeWin * 100}%` }} />
        <div className="bg-muted/40" style={{ width: `${o.draw * 100}%` }} />
        <div className="bg-prob-fill/45" style={{ width: `${o.awayWin * 100}%` }} />
      </div>
      <p className="mt-2 text-sm text-muted">
        Expected goals: <span className="tabular-nums text-text">{o.expHome.toFixed(2)}</span> –{" "}
        <span className="tabular-nums text-text">{o.expAway.toFixed(2)}</span>
      </p>

      {advance !== null && (
        <div className="mt-4">
          <h3 className="text-sm font-bold">Who advances</h3>
          <p className="text-[0.75rem] text-muted">
            A knockout tie can't end level, so this folds in extra time and penalties.
          </p>
          <div className="mt-2 grid grid-cols-2 gap-3">
            <StatCallout label={`${home} advance`} value={pct(advance)} />
            <StatCallout label={`${away} advance`} value={pct(1 - advance)} />
          </div>
        </div>
      )}

      <div className="mt-5">
        <h3 className="text-sm font-bold">Most likely scorelines</h3>
        <div className="mt-2 space-y-1.5">
          {scorelines.map((sl) => (
            <div key={`${sl.home}-${sl.away}`} className="flex items-center gap-3">
              <span className="w-12 shrink-0 text-sm font-semibold tabular-nums">
                {sl.home}–{sl.away}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
                <div className="h-full rounded-full bg-prob-fill" style={{ width: `${(sl.prob / maxP) * 100}%` }} />
              </div>
              <span className="w-12 shrink-0 text-right text-xs tabular-nums text-muted">
                {pct(sl.prob)}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5">
        <Explainer title="How these numbers are calculated">
          <p>
            The model turns each team's attack and defence rating into an expected goal count, then
            adds up the probability of every scoreline to get the chance of each result. For knockout
            ties it then plays out extra time (at reduced scoring rates) and a near-coin-flip shootout
            to decide who goes through.
          </p>
          <p>
            These are single-match odds. A team's chance of going all the way comes from simulating
            the whole tournament — see the Title Race and Bracket views.
          </p>
        </Explainer>
      </div>
    </div>
  );
}

function TbdNote({ m }: { m: ScheduleMatch }) {
  return (
    <div className="mt-6 rounded-xl border border-border bg-surface-2/40 px-4 py-4">
      <h2 className="text-sm font-bold">Teams to be decided</h2>
      <p className="mt-1 text-sm text-muted">
        This match will be contested by <span className="text-text">{m.top_label}</span> and{" "}
        <span className="text-text">{m.bottom_label}</span>. The prediction appears here once earlier
        results decide who's involved. In the meantime, the{" "}
        <Link to="/bracket" className="text-accent underline">
          projected bracket
        </Link>{" "}
        shows the most-likely team in each slot.
      </p>
    </div>
  );
}
