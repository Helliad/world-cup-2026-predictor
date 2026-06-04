"""Sensitivity analysis (§8.3): how much do title odds move with assumptions?

Several inputs are uncertain — the co-host home-advantage multiplier and the
penalty-shootout cap most of all. This re-runs the Monte Carlo across a small
grid of those values and reports how the top teams' championship probabilities
shift, so the effect of provisional assumptions is quantified, not hand-waved.
Publishing "top-4 ordering is stable; team X swings ±Y% with host advantage" is
rigor *and* content.

Usage:  python -m scripts.sensitivity            # host-multiplier sweep (launch-worthy)
        python -m scripts.sensitivity --full      # also sweep the penalty cap
"""

from __future__ import annotations

import argparse
import copy
import sys

from config import load_config
from model.dixon_coles import DixonColesModel
from simulation.knockout import KnockoutParams
from simulation.monte_carlo import run_simulations
from simulation.setup import load_sim_inputs

# Moderate N: enough to resolve title-odds shifts above the ~0.3% MC error.
SWEEP_N = 30000
TOP_K = 8


def _title_odds(model, sim_inputs, params, n, seed) -> dict[str, float]:
    sim = run_simulations(
        model, sim_inputs, params, n=n, seed=seed, whatif_sample_size=1, verbose=False
    )
    return {sim.teams[i]: float(sim.p_win[i]) for i in range(len(sim.teams))}


def run_grid(cfg: dict, axis: str, values: list[float]) -> dict[float, dict[str, float]]:
    model = DixonColesModel.load(cfg["output"]["params_path"])
    seed = cfg["simulation"]["master_seed"]
    out: dict[float, dict[str, float]] = {}
    for v in values:
        c = copy.deepcopy(cfg)
        if axis == "cohost_multiplier":
            c["home_advantage"]["cohost_multiplier"] = v
        elif axis == "penalty_cap":
            c["simulation"]["knockout"]["penalty_cap"] = v
        sim_inputs = load_sim_inputs(c, model)  # re-resolves host advantage from γ
        params = KnockoutParams.from_config(c)
        out[v] = _title_odds(model, sim_inputs, params, SWEEP_N, seed)
    return out


def report(axis: str, grid: dict[float, dict[str, float]]) -> None:
    values = list(grid)
    base = grid[values[len(values) // 2]]
    leaders = sorted(base, key=lambda t: -base[t])[:TOP_K]

    print(f"\n=== Title odds vs {axis} (N={SWEEP_N:,}) ===")
    header = "team".ljust(14) + "".join(f"{v:>9}" for v in values) + f"{'swing':>9}"
    print(header)
    print("-" * len(header))
    for t in leaders:
        row = [grid[v].get(t, 0.0) for v in values]
        swing = max(row) - min(row)
        print(t.ljust(14) + "".join(f"{p * 100:>8.1f}%" for p in row) + f"{swing * 100:>8.1f}%")

    # ordering stability across the sweep
    orders = [tuple(sorted(g, key=lambda t: -g[t])[:4]) for g in grid.values()]
    stable = len(set(orders)) == 1
    print(f"\nTop-4 ordering stable across the sweep: {stable}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sensitivity sweep of title odds.")
    ap.add_argument("--full", action="store_true", help="Also sweep the penalty cap.")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_config()
    report("cohost_multiplier", run_grid(cfg, "cohost_multiplier", [0.0, 0.25, 0.5, 0.75]))
    if args.full:
        report("penalty_cap", run_grid(cfg, "penalty_cap", [0.50, 0.55, 0.60]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
