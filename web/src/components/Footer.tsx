import { Link } from "react-router-dom";
import { REPO_URL } from "../lib/site";
import { useStore } from "../store/store";

// Honest footer: site/info links, the provisional banner, the "model not
// prophecy" framing (§9.3), the Monte Carlo error note (§6.6), and the full run
// manifest (§6.7). The links render regardless of data-load state.
export function Footer() {
  const meta = useStore((s) => s.predictions?.meta);
  const m = meta?.model_metrics;
  return (
    <footer className="mt-12 border-t border-border bg-surface-2/30">
      <div className="mx-auto max-w-5xl px-4 py-6 text-xs text-muted">
        <nav className="mb-4 flex flex-wrap gap-x-4 gap-y-2 font-medium" aria-label="Site information">
          <Link className="hover:text-text" to="/about">
            How it's made
          </Link>
          <Link className="hover:text-text" to="/faq">
            FAQ
          </Link>
          <Link className="hover:text-text" to="/privacy">
            Privacy
          </Link>
          <Link className="hover:text-text" to="/terms">
            Terms
          </Link>
          <a className="hover:text-text" href={REPO_URL} target="_blank" rel="noopener noreferrer">
            Source code
          </a>
        </nav>

        <div className="space-y-3">
          {meta?.provisional && (
            <p className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-warning">
              <strong>Provisional.</strong> The official FIFA third-place → bracket allocation table
              is not yet encoded, so bracket-dependent odds may shift once it is. Group memberships
              are official (from the published fixture list).
            </p>
          )}
          {meta && (
            <p>
              <strong className="text-text">This is a model, not a prophecy</strong>, built for
              education and entertainment — not betting, financial, or any other advice (see{" "}
              <Link className="underline hover:text-text" to="/terms">
                Terms
              </Link>
              ). A 15% favourite losing does not make the model “wrong”; validation lives at the match
              level
              {m && ` (test RPS ${m.rps_test.toFixed(3)}, ${(m.accuracy_test * 100).toFixed(0)}% top-pick accuracy, ${m.achieved_tier} tier)`}{" "}
              and in calibration over many matches.
            </p>
          )}
          {meta && <p>{meta.se_note}</p>}
          {meta && (
            <p className="border-t border-border pt-3 font-mono text-[0.68rem] leading-relaxed">
              N={meta.n_simulations.toLocaleString()} sims · seed {meta.seed} · model v
              {meta.model_version} · data {meta.data_snapshot} (
              {meta.data_rows.toLocaleString()} matches) · commit {meta.git_commit.slice(0, 7)} ·
              config {meta.config_hash} · {new Date(meta.generated_at).toUTCString()}
            </p>
          )}
          <p>
            Independent project, not affiliated with FIFA or any team. Data:{" "}
            <a className="underline hover:text-text" href="https://github.com/martj42/international_results">
              martj42/international_results
            </a>{" "}
            (CC BY-NC-SA). Code MIT-licensed.
          </p>
        </div>
      </div>
    </footer>
  );
}
