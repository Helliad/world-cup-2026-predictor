"""Wall-clock + memory benchmark for the Monte Carlo (§6.6).

Times ``run_simulations`` for N in {1k, 10k, 100k} and reports peak Python heap
(tracemalloc) so the published numbers in the README are real and reproducible.

Usage:  python -m scripts.benchmark
"""

from __future__ import annotations

import sys
import time
import tracemalloc

from config import load_config
from model.dixon_coles import DixonColesModel
from simulation.knockout import KnockoutParams
from simulation.monte_carlo import run_simulations
from simulation.setup import load_sim_inputs


def main(argv: list[str] | None = None) -> int:
    ns = [int(x) for x in argv] if argv else [1000, 10000, 100000]
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_config()
    model = DixonColesModel.load(cfg["output"]["params_path"])
    sim_inputs = load_sim_inputs(cfg, model)
    params = KnockoutParams.from_config(cfg)
    seed = cfg["simulation"]["master_seed"]

    def once(n: int) -> None:
        run_simulations(
            model,
            sim_inputs,
            params,
            n=n,
            seed=seed,
            whatif_sample_size=min(8000, n),
            verbose=False,
        )

    print(f"{'N':>8} | {'wall (s)':>9} | {'sims/s':>10} | {'peak MB':>8}")
    print("-" * 44)
    for n in ns:
        # Wall-clock from a clean run (tracemalloc would inflate it ~3x)...
        t0 = time.perf_counter()
        once(n)
        dt = time.perf_counter() - t0
        # ...then a separate pass purely to measure peak Python heap.
        tracemalloc.start()
        once(n)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        tracemalloc.stop()
        print(f"{n:>8} | {dt:>9.2f} | {n / dt:>10.0f} | {peak:>8.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
