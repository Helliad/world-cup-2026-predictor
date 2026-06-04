"""Evaluation CLI (§4.6.6): backtest, metrics report, reliability plots, gates.

Emits a machine-readable ``metrics.json`` and a human-readable markdown table,
plus reliability-diagram PNGs. Checks the acceptance gates (§4.6.2) and exits
non-zero if the model fails the Floor tier, so CI can enforce "does not ship as
good until it clears its gates".

Usage:
  python -m model.evaluate                 # full walk-forward backtest
  python -m model.evaluate --quick          # last few blocks only (fast)
  python -m model.evaluate --no-plots
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from config import load_config, resolve_path
from model.evaluation.backtest import run_walk_forward
from model.evaluation.metrics import reliability_table
from model.ratings import load_aliases, load_team_confederation


def check_gates(test_model: dict, ece: float, gates: dict, ece_max: float) -> dict:
    rps, acc = test_model["rps"], test_model["accuracy"]
    tiers = {}
    for tier, g in gates.items():
        tiers[tier] = bool(rps <= g["rps_max"] and acc >= g["accuracy_min"])
    tiers["ece_ok"] = bool(ece <= ece_max)
    if tiers["stretch"]:
        achieved = "stretch"
    elif tiers["target"]:
        achieved = "target"
    elif tiers["floor"]:
        achieved = "floor"
    else:
        achieved = "below_floor"
    tiers["achieved"] = achieved
    return tiers


def render_markdown(results: dict, gates: dict) -> str:
    t = results["test"]
    lines = ["# Model evaluation — held-out test block", ""]
    lines.append(
        f"Config: ξ={results['config']['xi']}, L2={results['config']['l2']}, "
        f"pooling={results['config']['pooling']}, "
        f"holdout={results['config']['test_holdout_months']}mo"
    )
    lines.append("")
    lines.append("| Method | RPS ↓ | Brier ↓ | LogLoss ↓ | Top-pick acc ↑ | n |")
    lines.append("|--------|------:|--------:|----------:|---------------:|--:|")
    order = ["model", "double_poisson", "base_rate", "uniform"]
    label = {
        "model": "**Dixon-Coles (ours)**",
        "double_poisson": "Double-Poisson",
        "base_rate": "Base rate",
        "uniform": "Uniform",
    }
    for k in order:
        mt = t[k]
        lines.append(
            f"| {label[k]} | {mt['rps']:.4f} | {mt['brier']:.4f} | "
            f"{mt['log_loss']:.4f} | {mt['accuracy']:.3f} | {mt['n']} |"
        )
    lines.append("")
    cal = results["calibration"]
    lines.append(
        f"**Calibration** ({cal['method']}): test ECE {cal['test_ece_before']:.4f} → "
        f"{cal['test_metrics_after']['ece']:.4f} after; "
        f"params={cal['params']}"
    )
    lines.append("")
    gres = results["gates"]
    lines.append(f"**Acceptance gates** (§4.6.2): achieved tier = **{gres['achieved'].upper()}**")
    lines.append("")
    lines.append("| Tier | RPS ≤ | Acc ≥ | Pass |")
    lines.append("|------|------:|------:|:----:|")
    for tier in ("floor", "target", "stretch"):
        g = gates[tier]
        lines.append(
            f"| {tier} | {g['rps_max']} | {g['accuracy_min']} | {'✅' if gres[tier] else '❌'} |"
        )
    lines.append("")
    if results["pooled_dev"]:
        pd_ = results["pooled_dev"]
        lines.append(
            f"Walk-forward pooled (dev): RPS={pd_['rps']:.4f}, acc={pd_['accuracy']:.3f}, "
            f"n={pd_['n']} across {len(results['blocks'])} blocks."
        )
    return "\n".join(lines) + "\n"


def make_plots(results: dict, out_dir: Path) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    probs = results["_test_probs_cal"]
    out = results["_test_out"]
    paths = []

    # reliability diagram (all three classes)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="#888", label="perfect")
    for k, name, color in [(0, "home", "#2563eb"), (1, "draw", "#9333ea"), (2, "away", "#dc2626")]:
        rt = reliability_table(probs, out, k)
        if rt["predicted"]:
            ax.plot(rt["predicted"], rt["observed"], "o-", color=color, label=name)
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Observed frequency")
    ax.set_title("Reliability (calibrated, test block)")
    ax.legend()
    ax.set_aspect("equal")
    p = out_dir / "reliability.png"
    fig.savefig(p, dpi=120, bbox_inches="tight")
    plt.close(fig)
    paths.append(str(p))

    # per-block RPS over time
    if results["blocks"]:
        fig, ax = plt.subplots(figsize=(7, 3.2))
        xs = [b["period"].split("..")[0] for b in results["blocks"]]
        ys = [b["rps"] for b in results["blocks"]]
        ax.plot(range(len(xs)), ys, "o-", color="#2563eb")
        ax.axhline(0.215, ls="--", color="#16a34a", label="target 0.215")
        ax.axhline(0.230, ls="--", color="#dc2626", label="floor 0.230")
        ax.set_xticks(range(0, len(xs), max(1, len(xs) // 8)))
        ax.set_xticklabels(
            [xs[i] for i in range(0, len(xs), max(1, len(xs) // 8))],
            rotation=45,
            ha="right",
            fontsize=7,
        )
        ax.set_ylabel("RPS")
        ax.set_title("Walk-forward RPS per block")
        ax.legend(fontsize=8)
        p = out_dir / "walkforward_rps.png"
        fig.savefig(p, dpi=120, bbox_inches="tight")
        plt.close(fig)
        paths.append(str(p))
    return paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backtest + metrics report + gates.")
    ap.add_argument("--config", default=None)
    ap.add_argument(
        "--quick", action="store_true", help="Only the most recent few walk-forward blocks."
    )
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args(argv)

    # Ensure UTF-8 console output (Windows defaults to cp1252 and chokes on ξ/↓).
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_config(args.config)
    df = pd.read_csv(resolve_path(cfg["data"]["snapshot_path"]), encoding="utf-8")
    df = df[df["date"] >= cfg["data"]["min_date"]]
    confederations = load_team_confederation(aliases=load_aliases())

    print("Running walk-forward backtest...")
    results = run_walk_forward(df, cfg, confederations, quick=args.quick)

    ev = cfg["evaluation"]
    results["gates"] = check_gates(
        results["test"]["model"],
        results["calibration"]["test_metrics_after"]["ece"],
        ev["gates"],
        ev["ece_max"],
    )

    metrics_path = resolve_path(cfg["output"]["metrics_path"])
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {k: v for k, v in results.items() if not k.startswith("_")}
    metrics_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

    md = render_markdown(results, ev["gates"])
    (metrics_path.parent / "metrics.md").write_text(md, encoding="utf-8")
    print("\n" + md)

    if not args.no_plots:
        try:
            paths = make_plots(results, metrics_path.parent / "plots")
            print(f"Plots: {paths}")
        except Exception as e:  # noqa: BLE001
            print(f"(plotting skipped: {e})")

    achieved = results["gates"]["achieved"]
    print(f"\nGate result: {achieved.upper()}")
    if achieved == "below_floor":
        print("MODEL BELOW FLOOR — does not ship as 'good'.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
