import { useMemo } from "react";
import { Explainer } from "../components/Explainer";
import { MatchOdds } from "../components/MatchOdds";
import { useStore } from "../store/store";
import type { Fixture } from "../types";

// All 72 group-stage fixtures with each result's probability.
export function Fixtures() {
  const predictions = useStore((s) => s.predictions)!;
  const fixtures = predictions.fixtures ?? [];

  const byGroup = useMemo(() => {
    const map = new Map<string, Fixture[]>();
    for (const f of fixtures) {
      (map.get(f.group) ?? map.set(f.group, []).get(f.group)!).push(f);
    }
    for (const list of map.values()) list.sort((a, b) => a.date.localeCompare(b.date));
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [fixtures]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <h1 className="text-step-4 font-extrabold">Fixtures &amp; match odds</h1>
      <p className="mt-1 text-muted">
        Every group-stage match and the model's chance of each result — home win, draw, or away win
        — at the scheduled venue.
      </p>

      <div className="mt-4">
        <Explainer title="How these odds are calculated">
          <p>
            For each fixture the model turns both teams' attack and defence ratings into the expected
            number of goals each side scores (shown as <strong>xG</strong>), then adds up the
            probability of every possible scoreline to get the chance of a home win, a draw, or an
            away win. The three always sum to 100%.
          </p>
          <p>
            <strong>Home advantage</strong> only applies to a co-host (USA, Canada, Mexico) playing in
            its <em>own</em> country, and even then it's a reduced effect — World Cup home advantage is
            real but smaller than in club football. Every other match is treated as neutral, so being
            the nominal “home” team confers nothing. Co-hosts at home are tagged{" "}
            <span className="uppercase text-accent">host</span>.
          </p>
          <p>
            These are single-match probabilities. A team's odds of <em>advancing</em> or{" "}
            <em>winning the tournament</em> come from simulating all the matches together — see the{" "}
            Groups, Bracket, and Title Race views.
          </p>
        </Explainer>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        {byGroup.map(([letter, list]) => (
          <section key={letter}>
            <h2 className="mb-2 text-step-2 font-bold">Group {letter}</h2>
            <div className="space-y-2">
              {list.map((f, i) => (
                <div key={i}>
                  <div className="mb-1 text-[0.7rem] uppercase tracking-wide text-muted">{f.date}</div>
                  <MatchOdds fixture={f} />
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
