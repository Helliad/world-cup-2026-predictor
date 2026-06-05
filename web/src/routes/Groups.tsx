import { Link } from "react-router-dom";
import { Explainer } from "../components/Explainer";
import { GroupTable } from "../components/GroupTable";
import { useStore } from "../store/store";

export function Groups() {
  const predictions = useStore((s) => s.predictions)!;
  const letters = Object.keys(predictions.groups).sort();
  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <h1 className="text-step-4 font-extrabold">Groups</h1>
      <p className="mt-1 text-muted">
        Probability each team reaches the knockout stage. Tap <span className="text-text">top</span>{" "}
        to pin a "what if", or see{" "}
        <Link className="text-accent underline" to="/fixtures">
          every match's odds
        </Link>
        .
      </p>

      <div className="mt-4">
        <Explainer title="How qualification works">
          <p>
            Each group plays a round-robin (every team faces the other three once). The{" "}
            <strong>top two of each group</strong> advance automatically, and the{" "}
            <strong>eight best of the twelve third-placed teams</strong> also go through &mdash; so 32
            of the 48 reach the knockout stage, and only four third-placed teams (plus all twelve
            bottom teams) go home.
          </p>
          <p>
            <strong>P(advance)</strong> is how often a team makes the knockouts across the simulated
            tournaments; <strong>exp points</strong> is its average group points. Ties are broken by
            goal difference, then goals scored, then head-to-head, exactly as in the real rules.
          </p>
        </Explainer>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {letters.map((l) => (
          <GroupTable key={l} letter={l} rows={predictions.groups[l]} />
        ))}
      </div>
    </div>
  );
}
