"""Rolling-origin (walk-forward) backtest (§4.6.4).

Football strength is non-stationary, so random k-fold CV leaks the future into
the past and is invalid. Instead: train on everything up to time T, predict the
next block, advance T, repeat. A final block (most recent ``test_holdout_months``)
is held out untouched as a true test set, never seen during tuning. Calibration
is fit on a validation slice of the development set, never on the test block.

Each block is evaluated only on matches where both teams appear in that block's
training slice, so every method (model + baselines) predicts the same fixtures.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from model.dixon_coles import DixonColesModel
from model.evaluation import baselines as bl
from model.evaluation.calibrate import Calibrator
from model.evaluation.metrics import all_metrics

# Older matches carry negligible time-decay weight; capping the training window
# bounds per-fit cost without changing results (weight at 12y ≈ 3e-4).
_TRAIN_WINDOW_DAYS = 365 * 12


def _months(ts: pd.Timestamp, m: int) -> pd.Timestamp:
    return ts - pd.DateOffset(months=m)


def _fit_slice(
    played: pd.DataFrame,
    dates: pd.Series,
    ref: pd.Timestamp,
    cfg: dict,
    confederations: dict[str, str] | None,
) -> DixonColesModel:
    m = cfg["model"]
    lo = ref - pd.Timedelta(days=_TRAIN_WINDOW_DAYS)
    train = played[(dates < ref) & (dates >= lo)]
    return DixonColesModel(max_goals=m["max_goals"]).fit(
        train,
        xi=m["xi"],
        l2=m["l2"],
        pooling=m["confederation_pooling"],
        confederations=confederations,
        competitive_weight=m["competitive_weight"],
        ref_date=ref,
    )


def _eval_block(model: DixonColesModel, block: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Restrict to fixtures both of whose teams the model knows, then predict."""
    known = block["home_team"].isin(model.team_index) & block["away_team"].isin(model.team_index)
    sub = block[known]
    if len(sub) == 0:
        return np.empty((0, 3)), np.empty((0,), dtype=np.int64)
    return bl.model_predictions(model, sub), bl.outcome_labels(sub)


def run_walk_forward(
    df: pd.DataFrame,
    cfg: dict,
    confederations: dict[str, str] | None = None,
    quick: bool = False,
    verbose: bool = True,
) -> dict:
    played = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    dates = pd.to_datetime(played["date"])
    played = played.assign(_d=dates).sort_values("_d")
    dates = played["_d"]

    ev = cfg["evaluation"]
    max_date = dates.max()
    test_start = _months(max_date, ev["test_holdout_months"])
    block_months = ev["walk_forward_block_months"]
    min_train_months = ev["walk_forward_min_train_months"]

    dev = played[dates < test_start]
    dev_dates = dates[dates < test_start]
    test = played[dates >= test_start]

    # walk-forward over the development set: start once enough training history
    # has accumulated, then advance one block at a time up to the test block.
    first_eval = dev_dates.min() + pd.DateOffset(months=min_train_months)
    if quick:
        # only the most recent few blocks, for fast iteration / smoke runs
        first_eval = _months(test_start, block_months * 3)

    blocks: list[dict] = []
    dev_probs_all, dev_out_all = [], []
    t = first_eval
    while t < test_start:
        block_end = t + pd.DateOffset(months=block_months)
        block = dev[(dev_dates >= t) & (dev_dates < block_end)]
        if len(block) > 0:
            model = _fit_slice(played, dates, t, cfg, confederations)
            probs, out = _eval_block(model, block)
            if len(out) > 0:
                blocks.append(
                    {"period": f"{t.date()}..{block_end.date()}", **all_metrics(probs, out)}
                )
                dev_probs_all.append(probs)
                dev_out_all.append(out)
                if verbose:
                    print(
                        f"  block {t.date()}..{block_end.date()}: "
                        f"RPS={blocks[-1]['rps']:.4f} acc={blocks[-1]['accuracy']:.3f} n={blocks[-1]['n']}"
                    )
        t = block_end

    dev_probs = np.vstack(dev_probs_all) if dev_probs_all else np.empty((0, 3))
    dev_out = np.concatenate(dev_out_all) if dev_out_all else np.empty((0,), dtype=np.int64)

    # --- final held-out test block: train on everything before test_start ---
    final_model = _fit_slice(played, dates, test_start, cfg, confederations)
    test_probs, test_out = _eval_block(final_model, test)

    # baselines on the SAME test fixtures (both teams known to final_model)
    known = test["home_team"].isin(final_model.team_index) & test["away_team"].isin(
        final_model.team_index
    )
    test_known = test[known]
    train_for_baselines = played[dates < test_start]
    base = {
        "model": all_metrics(test_probs, test_out),
        "uniform": all_metrics(bl.uniform_predictions(len(test_out)), test_out),
        "base_rate": all_metrics(
            bl.base_rate_predictions(train_for_baselines, len(test_out)), test_out
        ),
        "double_poisson": all_metrics(
            bl.double_poisson_predictions(
                train_for_baselines, test_known, cfg["model"]["l2"], test_start
            ),
            test_out,
        ),
    }

    # --- calibration: fit on a validation slice of dev, report test ECE before/after ---
    cal_method = cfg["calibration"]["method"]
    calibrator = (
        Calibrator(cal_method).fit(dev_probs, dev_out) if len(dev_out) else Calibrator("none")
    )
    test_probs_cal = calibrator.transform(test_probs)
    calibration = {
        "method": cal_method,
        "params": calibrator.describe(),
        "test_ece_before": base["model"]["ece"],
        "test_metrics_after": all_metrics(test_probs_cal, test_out),
    }

    return {
        "config": {
            "xi": cfg["model"]["xi"],
            "l2": cfg["model"]["l2"],
            "pooling": cfg["model"]["confederation_pooling"],
            "test_holdout_months": ev["test_holdout_months"],
            "block_months": block_months,
        },
        "blocks": blocks,
        "pooled_dev": all_metrics(dev_probs, dev_out) if len(dev_out) else None,
        "test": base,
        "calibration": calibration,
        "_test_probs": test_probs,
        "_test_probs_cal": test_probs_cal,
        "_test_out": test_out,
    }
