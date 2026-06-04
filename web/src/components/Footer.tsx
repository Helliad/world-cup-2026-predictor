import { useStore } from "../store/store";

// Honest footer: provisional banner, the "model not prophecy" framing (§9.3),
// the Monte Carlo error note (§6.6), and the full run manifest (§6.7).
export function Footer() {
  const meta = useStore((s) => s.predictions?.meta);
  if (!meta) return null;
  const m = meta.model_metrics;
  return (
    <footer className="mt-12 border-t border-border bg-surface-2/30">
      <div className="mx-auto max-w-5xl space-y-3 px-4 py-6 text-xs text-muted">
        {meta.provisional && (
          <p className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-warning">
            <strong>Provisional.</strong> The official FIFA third-place → bracket allocation table is
            not yet encoded, so bracket-dependent odds may shift once it is. Group memberships are
            official (from the published fixture list).
          </p>
        )}
        <p>
          <strong className="text-text">This is a model, not a prophecy.</strong> A 15% favourite
          losing does not make the model “wrong” — a single tournament can’t validate a
          probabilistic model. Validation lives at the match level
          {m && ` (test RPS ${m.rps_test.toFixed(3)}, ${(m.accuracy_test * 100).toFixed(0)}% top-pick accuracy, ${m.achieved_tier} tier)`}{" "}
          and in calibration over many matches.
        </p>
        <p>{meta.se_note}</p>
        <p className="border-t border-border pt-3 font-mono text-[0.68rem] leading-relaxed">
          N={meta.n_simulations.toLocaleString()} sims · seed {meta.seed} · model v
          {meta.model_version} · data {meta.data_snapshot} ({meta.data_rows.toLocaleString()} matches)
          · commit {meta.git_commit.slice(0, 7)} · config {meta.config_hash} ·{" "}
          {new Date(meta.generated_at).toUTCString()}
        </p>
        <p>
          Model: Dixon-Coles, time-weighted MLE (half-life ≈
          {meta.half_life_days ? ` ${Math.round(meta.half_life_days)} days` : " n/a"}). Data:{" "}
          <a
            className="text-accent underline"
            href="https://github.com/martj42/international_results"
          >
            martj42/international_results
          </a>{" "}
          (CC BY-NC-SA). Open source, MIT.
        </p>
      </div>
    </footer>
  );
}
