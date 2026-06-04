import { Link } from "react-router-dom";
import { ContentPage } from "../components/ContentPage";
import { useStore } from "../store/store";

export function FAQ() {
  const meta = useStore((s) => s.predictions!.meta);
  const m = meta.model_metrics;

  return (
    <ContentPage
      title="Frequently asked questions"
      lead="What this is, how to read it, and what it definitely isn't."
    >
      <h2>Is this a prediction of who will win?</h2>
      <p>
        No. It's a set of <em>probabilities</em> from a statistical model — a structured opinion
        about how the tournament might go, not a forecast of what will happen. The favourite winning
        is the exception, not the rule: even the top team is well under 1-in-5 to lift the trophy.
      </p>

      <h2>Is this betting or gambling advice?</h2>
      <p>
        <strong>No.</strong> Nothing on this site is betting, gambling, financial, investment, or
        professional advice of any kind, and it is not a recommendation to place any wager. It is an
        educational project. Please read the <Link to="/terms">Terms</Link>. If you choose to gamble,
        you do so entirely at your own risk and responsibility.
      </p>

      <h2>How accurate is the model?</h2>
      <p>
        On matches it had never seen, it scores a Ranked Probability Score of{" "}
        <strong>{m ? m.rps_test.toFixed(3) : "~0.16"}</strong> and gets the outcome right as its top
        pick about <strong>{m ? `${(m.accuracy_test * 100).toFixed(0)}%` : "60%"}</strong> of the
        time, beating every simple baseline. Accuracy is measured at the <em>match</em> level over
        many games — that's the honest scoreboard, not whether the eventual champion was our
        favourite. More detail on the <Link to="/about">How it's made</Link> page.
      </p>

      <h2>Why does my favourite team have such low odds?</h2>
      <p>
        There are 48 teams and a long knockout run to survive. Winning seven (or eight) matches in a
        row — some decided by penalty shootouts that are close to a coin flip — is genuinely hard, so
        even elite teams sit in the low double digits. Small probabilities are spread across many
        credible contenders.
      </p>

      <h2>What does "provisional" mean?</h2>
      <p>
        FIFA publishes a lookup table that decides which knockout slot each qualifying third-placed
        team fills. Until that official 2026 table is encoded, we use a documented stand-in, so
        bracket-dependent odds may shift slightly once it's finalised. Group memberships themselves
        are official. The footer flags this on every page.
      </p>

      <h2>What is "What if" mode?</h2>
      <p>
        Pin an outcome (tap a team in the <Link to="/bracket">Bracket</Link> or a group on the{" "}
        <Link to="/groups">Groups</Link> page) and every number recomputes assuming that happens.
        It's exact: the site simply counts the stored simulations in which your scenario occurred.
        Your pinned scenario is saved in the page URL, so you can share it as a link.
      </p>

      <h2>Why are some teams marked "low data confidence"?</h2>
      <p>
        Teams with thin recent international records have noisier ratings. We flag them and lean their
        ratings toward a regional baseline so a handful of games can't produce a wild number — and we
        label it honestly rather than hide it.
      </p>

      <h2>How often is it updated?</h2>
      <p>
        The pipeline can be re-run after each matchday once the tournament is underway; the change
        history of the published predictions then becomes a public, auditable track record — misses
        included.
      </p>

      <h2>Why doesn't it match the bookmakers?</h2>
      <p>
        Bookmaker odds include a margin and a lot of information this model doesn't use (squad news,
        injuries, market money). We treat de-margined betting odds as an aspirational ceiling, not a
        target. Differences are expected and interesting, not errors.
      </p>

      <h2>Can I see the code?</h2>
      <p>
        Yes — it's fully open source (model, simulator, and this site), with the data snapshot and
        fitted parameters committed so you can reproduce these numbers exactly. See{" "}
        <Link to="/about">How it's made</Link> for the link.
      </p>
    </ContentPage>
  );
}
