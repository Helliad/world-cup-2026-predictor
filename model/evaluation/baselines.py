"""Mandatory baselines for the evaluation (§4.6.3).

All baselines emit ``(n_test, 3)`` probability arrays in [home, draw, away] order
on the *same* test fixtures as the model, so the comparison is apples-to-apples.
If Dixon-Coles + time-decay does not beat plain double-Poisson, that is reported
honestly, not hidden.

The bookmaker-implied baseline (de-margined odds) is an *aspirational ceiling*,
not a baseline to beat; it is omitted here because the open results dataset ships
no odds. The hook is documented so it can be added if an odds feed is wired in.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from model.dixon_coles import DixonColesModel


def outcome_labels(df: pd.DataFrame) -> np.ndarray:
    """Map full-time scores to outcome labels: 0 home win, 1 draw, 2 away win."""
    h = df["home_score"].to_numpy(dtype=np.float64)
    a = df["away_score"].to_numpy(dtype=np.float64)
    labels = np.where(h > a, 0, np.where(h == a, 1, 2))
    return labels.astype(np.int64)


def uniform_predictions(n: int) -> np.ndarray:
    """1/3 each — the absolute floor."""
    return np.full((n, 3), 1.0 / 3.0)


def base_rate_predictions(train_df: pd.DataFrame, n_test: int) -> np.ndarray:
    """Historical home/draw/away marginals from the training slice, broadcast to
    every test match. Surprisingly hard to beat."""
    train_labels = outcome_labels(train_df)
    rates = np.array([(train_labels == k).mean() for k in (0, 1, 2)])
    rates = rates / rates.sum()
    return np.tile(rates, (n_test, 1))


def double_poisson_predictions(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    l2: float,
    ref_date: pd.Timestamp,
) -> np.ndarray:
    """Plain double-Poisson: no DC low-score correction (ρ=0) and no time decay
    (ξ=0). Proves the refinements earn their complexity (§4.6.3)."""
    model = DixonColesModel().fit(
        train_df, xi=0.0, l2=l2, pooling=0.0, ref_date=ref_date, fit_rho=False
    )
    return model_predictions(model, test_df)


def model_predictions(model: DixonColesModel, test_df: pd.DataFrame) -> np.ndarray:
    """Predict (home, draw, away) for each test fixture, applying the fitted home
    term only at non-neutral venues. Unknown teams fall back to uniform."""
    out = np.empty((len(test_df), 3))
    neutral = test_df["neutral"].astype(str).str.upper().eq("TRUE").to_numpy()
    homes = test_df["home_team"].to_numpy()
    aways = test_df["away_team"].to_numpy()
    for i in range(len(test_df)):
        h, a = homes[i], aways[i]
        if h not in model.team_index or a not in model.team_index:
            out[i] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
            continue
        ha = 0.0 if neutral[i] else model.gamma
        o = model.predict_outcome(h, a, home_advantage=ha)
        out[i] = (o["home_win"], o["draw"], o["away_win"])
    return out
