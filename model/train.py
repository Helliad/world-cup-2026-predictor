"""Train the Dixon-Coles model and serialise parameters (§4.3).

Reads ``data/results.csv``, validates it, fits with the hyperparameters from
``config.yaml``, attaches per-team data-confidence flags, and writes
``model/params.json`` — the committed artifact the simulator/pipeline load.

Usage:
  python -m model.train
  python -m model.train --config config.yaml --out model/params.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from config import config_hash, load_config, resolve_path
from model.dixon_coles import DixonColesModel
from model.ratings import (
    data_confidence_labels,
    load_aliases,
    load_team_confederation,
    recent_match_counts,
)
from scripts.validate_data import load_aliases as load_validation_aliases
from scripts.validate_data import validate_results


def load_training_frame(cfg: dict) -> pd.DataFrame:
    path = resolve_path(cfg["data"]["snapshot_path"])
    df = pd.read_csv(path, encoding="utf-8")
    rep = validate_results(df, aliases=load_validation_aliases())
    if not rep.ok:
        print(rep.render(), file=sys.stderr)
        raise SystemExit("Refusing to train: data validation failed.")
    # apply the training-window floor; time-decay does the rest of the work
    df = df[df["date"] >= cfg["data"]["min_date"]].copy()
    return df


def train(cfg: dict) -> DixonColesModel:
    df = load_training_frame(cfg)
    m = cfg["model"]
    aliases = load_aliases()
    confederations = load_team_confederation(aliases=aliases)

    model = DixonColesModel(max_goals=m["max_goals"]).fit(
        df,
        xi=m["xi"],
        l2=m["l2"],
        pooling=m["confederation_pooling"],
        confederations=confederations,
        competitive_weight=m["competitive_weight"],
        max_iter=m["optimizer"]["max_iter"],
        tol=m["optimizer"]["tol"],
    )

    # data-confidence flags (§4.4) from recent match counts
    played = df[df["home_score"].notna() & df["away_score"].notna()]
    ref_date = pd.to_datetime(played["date"]).max()
    counts = recent_match_counts(played, model.teams, ref_date)
    labels = data_confidence_labels(
        counts, m["min_matches_high_confidence"], m["min_matches_medium_confidence"]
    )
    model.meta["data_confidence"] = labels
    model.meta["recent_match_counts"] = counts
    model.meta["model_version"] = m["version"]
    model.meta["config_hash"] = config_hash(cfg)
    return model


def report(model: DixonColesModel) -> None:
    print("=" * 60)
    print(f"Dixon-Coles fit  (version {model.meta.get('model_version')})")
    print("=" * 60)
    meta = model.meta
    print(
        f"teams={meta['n_teams']}  matches={meta['n_matches']}  "
        f"converged={meta['optimizer_success']} in {meta['optimizer_iterations']} iters"
    )
    print(
        f"home advantage gamma = {model.gamma:.3f}  "
        f"(xG x{np.exp(model.gamma):.2f} for the home side)"
    )
    print(f"low-score rho        = {model.rho:.3f}")
    hl = meta["half_life_days"]
    print(
        f"time-decay xi        = {model.xi}  (half-life ~{hl:.0f} days = ~{hl / 30.4:.1f} months)"
    )
    print(f"L2={model.l2}  confederation_pooling={model.pooling}")

    order = np.argsort(model.attack)[::-1]
    print("\nTop 10 by attack strength:")
    for i in order[:10]:
        conf = model.meta["data_confidence"].get(model.teams[i], "?")
        print(
            f"  {model.teams[i]:24} alpha={model.attack[i]:+.2f}  beta={model.defence[i]:+.2f}  [{conf}]"
        )

    lows = [t for t, lbl in model.meta["data_confidence"].items() if lbl == "low"]
    print(f"\nLow data-confidence teams: {len(lows)} (e.g. {sorted(lows)[:8]})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fit Dixon-Coles and save params.json.")
    ap.add_argument("--config", default=None, help="Path to config.yaml")
    ap.add_argument("--out", default=None, help="Output params path (default from config).")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    model = train(cfg)
    out = Path(args.out) if args.out else resolve_path(cfg["output"]["params_path"])
    model.save(out)
    report(model)
    print(f"\nSaved -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
