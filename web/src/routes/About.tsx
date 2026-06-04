import { Link } from "react-router-dom";
import { ContentPage } from "../components/ContentPage";
import { useStore } from "../store/store";

// "How this was made" — the methodology, written for a general audience but
// honest about the technical detail. Live numbers come from the run manifest.
export function About() {
  const meta = useStore((s) => s.predictions!.meta);
  const m = meta.model_metrics;
  const halfLifeMonths = meta.half_life_days ? Math.round(meta.half_life_days / 30.4) : null;

  return (
    <ContentPage
      title="How this was made"
      lead="A statistical model, a tournament simulator, and a website — built in the open as an educational project."
    >
      <p>
        This site answers one question — <em>how likely is each team to win the 2026 World Cup?</em>{" "}
        — by combining a statistical model of football matches with a simulator that plays the whole
        tournament {meta.n_simulations.toLocaleString()} times. Everything is open source and
        reproducible; nothing here is a prediction you should bet on (see the{" "}
        <Link to="/terms">Terms</Link>).
      </p>

      <h2>1. The data</h2>
      <p>
        The model is trained on <strong>{meta.data_rows.toLocaleString()} historical men's
        international matches</strong> going back to the 19th century (the open{" "}
        <a href="https://github.com/martj42/international_results">martj42/international_results</a>{" "}
        dataset, snapshot {meta.data_snapshot}). Recent matches matter far more than old ones, so
        each match is weighted by age with a half-life of about{" "}
        {halfLifeMonths ? `${halfLifeMonths} months` : "a year"} — a result from two years ago counts
        roughly half as much as one from today.
      </p>

      <h2>2. The model — Dixon-Coles</h2>
      <p>
        Each team gets an <strong>attack</strong> rating and a <strong>defence</strong> rating, plus
        a global <strong>home-advantage</strong> term. The number of goals a side scores is modelled
        as a Poisson process whose average depends on its attack and the opponent's defence. We use
        the classic <strong>Dixon-Coles (1997)</strong> refinement, which corrects the rate of
        low-scoring results (0-0, 1-0, 0-1, 1-1) that a plain model gets wrong. The output is a full
        grid of scoreline probabilities for any fixture, fit by maximum likelihood.
      </p>
      <p>
        Teams with thin records are pulled toward their confederation's average so they don't get
        absurd ratings from a handful of games, and each team carries a data-confidence flag.
      </p>

      <h2>3. How we know it's any good</h2>
      <p>
        A model isn't "done" when it fits — it's done when it predicts well on matches it has never
        seen. We use a <strong>walk-forward backtest</strong>: train on everything up to a date,
        predict the next block of matches, roll forward, repeat. (Ordinary random cross-validation
        would leak the future into the past and is invalid for something that drifts over time like
        football.)
      </p>
      {m && (
        <ul>
          <li>
            <strong>Ranked Probability Score {m.rps_test.toFixed(3)}</strong> on the held-out test
            block — the field-standard accuracy measure for football (lower is better).
          </li>
          <li>
            <strong>{(m.accuracy_test * 100).toFixed(0)}%</strong> of matches had the correct
            outcome as the model's top pick.
          </li>
          <li>
            It beats every simple baseline (a coin-flip, historical averages, and a plain
            double-Poisson model), reaching the <strong>{m.achieved_tier}</strong> tier of our
            published targets.
          </li>
        </ul>
      )}
      <p>
        We also check <em>calibration</em>: when the model says "30%", does it happen about 30% of
        the time? The full report (with reliability plots) lives in the repository.
      </p>

      <h2>4. The simulator</h2>
      <p>
        The model only knows about single matches; the simulator knows the 2026 format exactly — 12
        groups of 4, the strict tiebreakers, the eight best third-placed teams advancing, and a
        32-team knockout where ties go to extra time and then penalties. It plays the whole thing{" "}
        {meta.n_simulations.toLocaleString()} times and counts how often each team reaches each
        stage. Because it runs so many times, every probability comes with a small margin of error
        (about ±0.1% here), which we show rather than hide.
      </p>

      <h2>5. The "what if" feature</h2>
      <p>
        On the <Link to="/bracket">Bracket</Link> and <Link to="/groups">Groups</Link> pages you can
        pin outcomes — "assume Brazil reach the final" — and every probability instantly recomputes
        as a <em>conditional</em> probability. This isn't the model re-running; it's the website
        filtering the stored simulations to just the ones where your scenario happened. Exact, and
        instant.
      </p>

      <h2>6. Open and reproducible</h2>
      <p>
        The Python model and simulator, the React site, the data snapshot, and the fitted parameters
        are all committed, so anyone can clone the repository and reproduce these exact numbers. Each
        run records its data checksum, configuration, and random seed. Code is MIT-licensed; the
        underlying match data is CC BY-NC-SA.
      </p>

      <h2>7. What it is — and isn't</h2>
      <p>
        This is a probabilistic <em>model</em>, not a prophecy. A 15% favourite is far more likely to
        lose than to win, and a single tournament can never prove a probability right or wrong. It is
        built for curiosity, learning, and discussion — not for any kind of betting, financial, or
        professional decision. See the <Link to="/faq">FAQ</Link> and <Link to="/terms">Terms</Link>.
      </p>
    </ContentPage>
  );
}
