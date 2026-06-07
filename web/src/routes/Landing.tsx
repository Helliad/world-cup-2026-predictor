import { type ReactNode, useEffect, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import { CountUp, Reveal } from "../components/Reveal";
import { TeamBadge } from "../components/TeamBadge";
import { pct } from "../lib/format";
import { ROUND_SHORT, formatDateShort, matchSides } from "../lib/schedule";
import { AUTHOR, REPO_URL } from "../lib/site";
import { useStore } from "../store/store";

// The landing story (route "/"): a scroll-driven introduction that explains what
// the site is and walks through each view with a live mini-preview built from the
// real model output. The dashboard itself lives at /title.
export function Landing() {
  const predictions = useStore((s) => s.predictions)!;
  const meta = predictions.meta;
  const teams = predictions.teams; // already sorted by p_win, desc
  const m = meta.model_metrics;

  const pWinOf = useMemo(() => {
    const map: Record<string, number> = {};
    for (const t of teams) map[t.team] = t.p_win;
    return map;
  }, [teams]);

  // Marquee group: the one whose two strongest teams have the highest combined
  // title odds (the "group of death" makes the best advertisement).
  const marqueeGroup = useMemo(() => {
    let best = "";
    let bestScore = -1;
    for (const [letter, rows] of Object.entries(predictions.groups)) {
      const score = rows
        .map((r) => pWinOf[r.team] ?? 0)
        .sort((a, b) => b - a)
        .slice(0, 2)
        .reduce((s, v) => s + v, 0);
      if (score > bestScore) {
        bestScore = score;
        best = letter;
      }
    }
    return best;
  }, [predictions.groups, pWinOf]);

  // Marquee fixture: the most evenly poised group game (both sides genuinely live).
  const marqueeFixture = useMemo(
    () =>
      [...predictions.fixtures].sort(
        (a, b) => Math.min(b.home_win, b.away_win) - Math.min(a.home_win, a.away_win),
      )[0],
    [predictions.fixtures],
  );

  // Projected final: the two teams most likely to reach it.
  const finalists = useMemo(
    () => [...teams].sort((a, b) => b.p_final - a.p_final).slice(0, 2),
    [teams],
  );

  const scheduleRows = useMemo(() => {
    const byNo = (n: number) => predictions.schedule.find((s) => s.match === n);
    return [byNo(1), byNo(73), byNo(104)].filter(Boolean) as typeof predictions.schedule;
  }, [predictions.schedule]);

  // In-page scroll (HashRouter owns the URL hash, so href="#story" can't anchor).
  const scrollToStory = () =>
    document.getElementById("story")?.scrollIntoView({ behavior: "smooth", block: "start" });

  return (
    <div className="overflow-clip">
      <ScrollProgress />

      {/* ---- Hero ---- */}
      <section className="relative isolate flex min-h-[86vh] items-center overflow-hidden px-4">
        <Aurora />
        <div className="mx-auto max-w-3xl py-20 text-center">
          <Reveal>
            <p className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-accent">
              2026 FIFA World Cup · 48 teams · 104 matches
            </p>
          </Reveal>
          <Reveal delay={80}>
            <h1 className="mt-4 text-step-6 font-extrabold leading-[1.05] tracking-tight">
              Who <span className="text-accent">actually</span> wins the World Cup?
            </h1>
          </Reveal>
          <Reveal delay={160}>
            <p className="mx-auto mt-5 max-w-xl text-step-1 text-muted">
              Not pundits, not vibes. A statistical model plays the entire tournament 100,000 times
              and counts how often each nation lifts the trophy.
            </p>
          </Reveal>
          <Reveal delay={240}>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link
                to="/title"
                className="rounded-full bg-accent px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-accent/20 transition-transform hover:scale-[1.03]"
              >
                Explore the predictor →
              </Link>
              <button
                type="button"
                onClick={scrollToStory}
                className="rounded-full border border-border px-6 py-3 text-sm font-semibold text-muted transition-colors hover:text-text"
              >
                See how it works
              </button>
            </div>
          </Reveal>
        </div>
        <button
          type="button"
          onClick={scrollToStory}
          aria-label="Scroll to the story"
          className="bob absolute bottom-6 left-1/2 -translate-x-1/2 text-muted hover:text-text"
        >
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M19 12l-7 7-7-7" />
          </svg>
        </button>
      </section>

      {/* ---- Premise / the model ---- */}
      <section id="story" className="border-t border-border bg-surface-2/30 px-4 py-20 sm:py-28">
        <div className="mx-auto max-w-3xl">
          <Reveal>
            <h2 className="text-step-4 font-extrabold tracking-tight">
              It starts with a century of football.
            </h2>
          </Reveal>
          <Reveal delay={80}>
            <p className="mt-4 text-step-1 text-muted">
              A <strong className="text-text">Dixon-Coles</strong> model rates every nation's attack
              and defence from decades of real results. A simulator then plays all 104 matches of the
              2026 World Cup, over and over, turning those ratings into the probability of every
              outcome: who tops each group, who survives the bracket, who wins it all.
            </p>
          </Reveal>

          <div className="mt-10 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { value: meta.data_rows, fmt: (n: number) => `${Math.round(n / 1000)}k`, label: "matches trained on" },
              { value: 48, fmt: (n: number) => Math.round(n).toString(), label: "teams" },
              { value: 104, fmt: (n: number) => Math.round(n).toString(), label: "matches simulated" },
              { value: meta.n_simulations, fmt: (n: number) => `${Math.round(n / 1000)}k`, label: "tournaments run" },
            ].map((s, i) => (
              <Reveal key={s.label} delay={i * 70}>
                <div className="rounded-xl border border-border bg-surface px-4 py-5 text-center">
                  <div className="text-step-4 font-extrabold tabular-nums leading-none text-accent">
                    <CountUp to={s.value} format={s.fmt} />
                  </div>
                  <div className="mt-1.5 text-[0.72rem] text-muted">{s.label}</div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ---- Beats: one per view, with a live preview ---- */}
      <Beat
        index={1}
        kicker="The headline"
        title="The Title Race"
        to="/title"
        cta="See all 48 teams"
        text={
          <>
            Every nation's chance of being crowned champion, straight from the {meta.n_simulations.toLocaleString()}{" "}
            simulations. The favourite still loses far more often than it wins, so the odds spread
            across a wide field.
          </>
        }
        visual={<TitleRacePreview rows={teams.slice(0, 6).map((t) => ({ team: t.team, value: t.p_win }))} />}
      />

      <Beat
        index={2}
        kicker="The first hurdle"
        title="Groups"
        to="/groups"
        cta="Open the group tables"
        tint
        text={
          <>
            Twelve groups of four. The model gives each team its chance of advancing and its expected
            points. Here is <strong className="text-text">Group {marqueeGroup}</strong>, one of the
            tightest in the draw.
          </>
        }
        visual={<GroupPreview letter={marqueeGroup} rows={predictions.groups[marqueeGroup] ?? []} />}
      />

      <Beat
        index={3}
        kicker="The whole calendar"
        title="Match Center"
        to="/schedule"
        cta="Browse all 104 matches"
        text={
          <>
            Every match from the opener to the final at MetLife Stadium, by date. As real results
            come in they are <strong className="text-text">pinned into the simulation</strong>, and
            the whole forecast re-conditions on what actually happened.
          </>
        }
        visual={<SchedulePreview rows={scheduleRows} />}
      />

      <Beat
        index={4}
        kicker="Match by match"
        title="Fixtures & odds"
        to="/fixtures"
        cta="See every match's odds"
        tint
        text={
          <>
            The chance of a home win, draw, or away win for each game, with expected goals. A toss-up
            like this one is where the tournament turns.
          </>
        }
        visual={marqueeFixture ? <FixturePreview f={marqueeFixture} /> : null}
      />

      <Beat
        index={5}
        kicker="All the way to the trophy"
        title="Bracket & what-if"
        to="/bracket"
        cta="Open the projected bracket"
        text={
          <>
            The most likely team in every knockout slot. Pin a what-if (say, your team reaches the
            final) and every number recomputes from only the simulations where it came true.
          </>
        }
        visual={<BracketPreview champion={teams[0]?.team} finalists={finalists} />}
      />

      {/* ---- Honesty ---- */}
      <section className="border-t border-border bg-surface-2/30 px-4 py-20 sm:py-28">
        <div className="mx-auto max-w-2xl text-center">
          <Reveal>
            <h2 className="text-step-4 font-extrabold tracking-tight">A model, not a prophecy.</h2>
          </Reveal>
          <Reveal delay={80}>
            <p className="mt-4 text-step-1 text-muted">
              A 15% favourite is far more likely to <em>not</em> win than to win. One tournament can
              never prove a probability right or wrong. Honesty lives in the long run:
              {m ? (
                <>
                  {" "}across a held-out test set the model scores an RPS of{" "}
                  <strong className="text-text">{m.rps_test.toFixed(3)}</strong> with{" "}
                  <strong className="text-text">{(m.accuracy_test * 100).toFixed(0)}%</strong>{" "}
                  top-pick accuracy, beating every baseline.
                </>
              ) : (
                " the model is scored at the match level over many games, not on any single result."
              )}
            </p>
          </Reveal>
          <Reveal delay={160}>
            <p className="mt-3 text-sm text-muted">
              Built for education and curiosity. Not betting advice.
            </p>
          </Reveal>
        </div>
      </section>

      {/* ---- Outro / CTA + attribution ---- */}
      <section className="relative isolate overflow-hidden px-4 py-24 text-center">
        <Aurora />
        <div className="mx-auto max-w-2xl">
          <Reveal>
            <h2 className="text-step-5 font-extrabold tracking-tight">Ready to dig in?</h2>
          </Reveal>
          <Reveal delay={80}>
            <p className="mt-3 text-step-1 text-muted">
              Start with the title race, then chase your team through the groups and into the bracket.
            </p>
          </Reveal>
          <Reveal delay={160}>
            <Link
              to="/title"
              className="mt-7 inline-block rounded-full bg-accent px-7 py-3.5 text-sm font-semibold text-white shadow-lg shadow-accent/20 transition-transform hover:scale-[1.03]"
            >
              Explore the predictor →
            </Link>
          </Reveal>
          <Reveal delay={220}>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-sm text-muted">
              <Link to="/title" className="hover:text-text">Title Race</Link>
              <Link to="/groups" className="hover:text-text">Groups</Link>
              <Link to="/schedule" className="hover:text-text">Schedule</Link>
              <Link to="/fixtures" className="hover:text-text">Fixtures</Link>
              <Link to="/bracket" className="hover:text-text">Bracket</Link>
              <Link to="/about" className="hover:text-text">How it's made</Link>
            </div>
          </Reveal>
          <Reveal delay={280}>
            <p className="mt-8 text-sm text-muted">
              Built by{" "}
              <a href={AUTHOR.url} target="_blank" rel="noopener noreferrer" className="font-semibold text-text underline underline-offset-2 hover:text-accent">
                {AUTHOR.name}
              </a>
              {" · "}
              <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 hover:text-text">
                Source code
              </a>
            </p>
          </Reveal>
        </div>
      </section>
    </div>
  );
}

// ---------- layout + chrome ----------

function ScrollProgress() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const h = document.documentElement;
        const max = h.scrollHeight - h.clientHeight;
        const p = max > 0 ? (h.scrollTop / max) * 100 : 0;
        if (ref.current) ref.current.style.width = `${p}%`;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => {
      window.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);
  return (
    <div className="fixed inset-x-0 top-0 z-50 h-[3px] bg-transparent" aria-hidden="true">
      <div ref={ref} className="h-full bg-accent" style={{ width: 0 }} />
    </div>
  );
}

function Aurora() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div className="aurora absolute -left-1/4 top-[-20%] h-[60vh] w-[60vh] rounded-full bg-accent/20 blur-[100px]" />
      <div className="aurora absolute right-[-15%] top-[10%] h-[50vh] w-[50vh] rounded-full bg-prob-fill/15 blur-[120px]" style={{ animationDelay: "-8s" }} />
    </div>
  );
}

function Beat({
  index,
  kicker,
  title,
  text,
  visual,
  to,
  cta,
  tint,
}: {
  index: number;
  kicker: string;
  title: string;
  text: ReactNode;
  visual: ReactNode;
  to: string;
  cta: string;
  tint?: boolean;
}) {
  const reverse = index % 2 === 0;
  return (
    <section className={`border-t border-border px-4 py-20 sm:py-24 ${tint ? "bg-surface-2/30" : ""}`}>
      <div className="mx-auto grid max-w-5xl items-center gap-8 md:grid-cols-2">
        <Reveal className={reverse ? "md:order-2" : ""}>
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-accent">
            {String(index).padStart(2, "0")} · {kicker}
          </p>
          <h2 className="mt-2 text-step-4 font-extrabold tracking-tight">{title}</h2>
          <p className="mt-3 text-step-1 leading-relaxed text-muted">{text}</p>
          <Link
            to={to}
            className="mt-5 inline-flex items-center gap-1 text-sm font-semibold text-accent hover:underline"
          >
            {cta} →
          </Link>
        </Reveal>
        <Reveal delay={120} className={reverse ? "md:order-1" : ""}>
          <div className="rounded-2xl border border-border bg-surface p-4 shadow-xl shadow-black/5 sm:p-5">
            {visual}
          </div>
        </Reveal>
      </div>
    </section>
  );
}

// ---------- live mini-previews (real model data) ----------

function TitleRacePreview({ rows }: { rows: { team: string; value: number }[] }) {
  const max = Math.max(...rows.map((r) => r.value), 0.0001);
  return (
    <div>
      <div className="mb-3 text-[0.7rem] font-semibold uppercase tracking-wide text-muted">
        Championship odds
      </div>
      <div className="space-y-2.5">
        {rows.map((r, i) => (
          <div key={r.team} className="flex items-center gap-2.5">
            <span className="w-4 text-right text-xs tabular-nums text-muted">{i + 1}</span>
            <TeamBadge team={r.team} className="h-5 w-5 text-[0.55rem]" />
            <span className="w-24 truncate text-sm font-medium">{r.team}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
              <div className="h-full rounded-full bg-prob-fill" style={{ width: `${(r.value / max) * 100}%` }} />
            </div>
            <span className="w-12 text-right text-xs font-semibold tabular-nums">{pct(r.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function GroupPreview({ letter, rows }: { letter: string; rows: { team: string; p_advance: number; exp_points: number }[] }) {
  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between">
        <span className="text-sm font-bold">Group {letter}</span>
        <span className="text-[0.7rem] uppercase tracking-wide text-muted">P(advance)</span>
      </div>
      <div className="space-y-2.5">
        {[...rows].sort((a, b) => b.p_advance - a.p_advance).map((r) => (
          <div key={r.team} className="flex items-center gap-2.5">
            <TeamBadge team={r.team} className="h-5 w-5 text-[0.55rem]" />
            <span className="w-24 truncate text-sm font-medium">{r.team}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2">
              <div className="h-full rounded-full bg-prob-fill" style={{ width: `${r.p_advance * 100}%` }} />
            </div>
            <span className="w-10 text-right text-xs font-semibold tabular-nums">{pct(r.p_advance)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SchedulePreview({ rows }: { rows: { match: number; round: "group" | "r32" | "r16" | "qf" | "sf" | "third" | "final"; date: string; home: string | null; away: string | null; top_label: string | null; bottom_label: string | null }[] }) {
  return (
    <div className="space-y-2">
      <div className="mb-1 text-[0.7rem] font-semibold uppercase tracking-wide text-muted">
        104 matches, by date
      </div>
      {rows.map((mm) => {
        const s = matchSides(mm as never);
        return (
          <div key={mm.match} className="rounded-lg border border-border bg-surface-2/40 px-3 py-2">
            <div className="mb-1 flex justify-between text-[0.65rem] uppercase tracking-wide text-muted">
              <span>{ROUND_SHORT[mm.round]} · {formatDateShort(mm.date)}</span>
              <span className="text-muted/70">#{mm.match}</span>
            </div>
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className={`truncate ${s.homeTeam ? "font-medium" : "italic text-muted"}`}>{s.homeLabel}</span>
              <span className="shrink-0 text-xs text-muted">v</span>
              <span className={`truncate text-right ${s.awayTeam ? "font-medium" : "italic text-muted"}`}>{s.awayLabel}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function FixturePreview({ f }: { f: { home: string; away: string; home_win: number; draw: number; away_win: number; exp_home: number; exp_away: number } }) {
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-sm font-medium">
          <TeamBadge team={f.home} className="h-5 w-5 text-[0.55rem]" />
          {f.home}
        </span>
        <span className="shrink-0 text-[0.65rem] tabular-nums text-muted">{f.exp_home.toFixed(1)}–{f.exp_away.toFixed(1)} xG</span>
        <span className="flex flex-row-reverse items-center gap-2 text-sm font-medium">
          <TeamBadge team={f.away} className="h-5 w-5 text-[0.55rem]" />
          {f.away}
        </span>
      </div>
      <div className="flex h-2.5 overflow-hidden rounded-full" aria-hidden="true">
        <div className="bg-prob-fill" style={{ width: `${f.home_win * 100}%` }} />
        <div className="bg-muted/40" style={{ width: `${f.draw * 100}%` }} />
        <div className="bg-prob-fill/45" style={{ width: `${f.away_win * 100}%` }} />
      </div>
      <div className="mt-1.5 flex justify-between text-[0.72rem] tabular-nums">
        <span className="font-semibold">{pct(f.home_win)} win</span>
        <span className="text-muted">{pct(f.draw)} draw</span>
        <span className="font-semibold">{pct(f.away_win)} win</span>
      </div>
    </div>
  );
}

function BracketPreview({ champion, finalists }: { champion?: string; finalists: { team: string; p_final: number }[] }) {
  return (
    <div className="text-center">
      <div className="mb-3 text-[0.7rem] font-semibold uppercase tracking-wide text-muted">
        Projected final
      </div>
      <div className="flex items-center justify-center gap-3">
        {finalists.map((t, i) => (
          <div key={t.team} className="flex items-center gap-2">
            {i === 1 && <span className="text-xs text-muted">vs</span>}
            <div className="flex flex-col items-center gap-1">
              <TeamBadge team={t.team} className="h-8 w-8" />
              <span className="text-xs font-medium">{t.team}</span>
              <span className="text-[0.65rem] tabular-nums text-muted">{pct(t.p_final)} reach</span>
            </div>
          </div>
        ))}
      </div>
      {champion && (
        <div className="mt-4 rounded-xl border border-accent/40 bg-accent/5 px-4 py-3">
          <div className="text-[0.65rem] uppercase tracking-wide text-muted">Most likely champion</div>
          <div className="mt-1 flex items-center justify-center gap-2 text-step-1 font-extrabold">
            <TeamBadge team={champion} className="h-6 w-6 text-[0.6rem]" />
            {champion}
          </div>
        </div>
      )}
    </div>
  );
}
