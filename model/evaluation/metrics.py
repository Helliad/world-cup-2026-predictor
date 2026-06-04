"""Proper scoring rules for 3-outcome match prediction (§4.6.1).

Outcome convention everywhere: index 0 = home win, 1 = draw, 2 = away win, which
is the natural *order* RPS exploits (a draw sits between the two wins).

All functions take ``probs`` of shape (n, 3) and ``outcomes`` of shape (n,) with
integer labels in {0, 1, 2}. Lower is better for RPS / Brier / log-loss.
"""

from __future__ import annotations

import numpy as np

HOME, DRAW, AWAY = 0, 1, 2
_EPS = 1e-15


def _onehot(outcomes: np.ndarray) -> np.ndarray:
    e = np.zeros((outcomes.shape[0], 3))
    e[np.arange(outcomes.shape[0]), outcomes] = 1.0
    return e


def ranked_probability_score(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Mean RPS over matches (§4.6.1).

    RPS = 1/(r-1) · Σ_{i=1}^{r-1} ( Σ_{j≤i} (p_j - e_j) )².  r = 3.
    """
    p = np.asarray(probs, dtype=np.float64)
    e = _onehot(np.asarray(outcomes))
    cum_p = np.cumsum(p, axis=1)[:, :2]  # cumulative over home, home+draw
    cum_e = np.cumsum(e, axis=1)[:, :2]
    per_match = np.sum((cum_p - cum_e) ** 2, axis=1) / 2.0
    return float(per_match.mean())


def brier_score(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Multiclass Brier score: mean over matches of Σ_k (p_k - e_k)². Range [0, 2]."""
    p = np.asarray(probs, dtype=np.float64)
    e = _onehot(np.asarray(outcomes))
    return float(np.sum((p - e) ** 2, axis=1).mean())


def log_loss(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Mean negative log-likelihood (ignorance score). Punishes overconfidence."""
    p = np.clip(np.asarray(probs, dtype=np.float64), _EPS, 1.0)
    idx = np.arange(p.shape[0])
    return float(-np.log(p[idx, np.asarray(outcomes)]).mean())


def top_pick_accuracy(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Fraction of matches where the argmax-probability outcome is realised."""
    p = np.asarray(probs, dtype=np.float64)
    return float((p.argmax(axis=1) == np.asarray(outcomes)).mean())


def expected_calibration_error(probs: np.ndarray, outcomes: np.ndarray, n_bins: int = 10) -> float:
    """Top-label ECE (§4.6.5): bin by confidence (max prob), compare mean
    confidence to accuracy in each bin, weight by bin population."""
    p = np.asarray(probs, dtype=np.float64)
    conf = p.max(axis=1)
    pred = p.argmax(axis=1)
    correct = (pred == np.asarray(outcomes)).astype(np.float64)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = p.shape[0]
    for lo, hi in zip(bins[:-1], bins[1:], strict=True):
        mask = (conf > lo) & (conf <= hi) if lo > 0 else (conf >= lo) & (conf <= hi)
        if not mask.any():
            continue
        ece += (mask.sum() / n) * abs(correct[mask].mean() - conf[mask].mean())
    return float(ece)


def reliability_table(
    probs: np.ndarray, outcomes: np.ndarray, class_idx: int, n_bins: int = 10
) -> dict[str, list[float]]:
    """Per-class reliability data: predicted-probability bucket vs observed
    frequency for one outcome class (for reliability diagrams, §4.6.5)."""
    p = np.asarray(probs, dtype=np.float64)[:, class_idx]
    observed = (np.asarray(outcomes) == class_idx).astype(np.float64)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    pred_mean, obs_freq, counts = [], [], []
    for lo, hi in zip(bins[:-1], bins[1:], strict=True):
        mask = (p > lo) & (p <= hi) if lo > 0 else (p >= lo) & (p <= hi)
        if not mask.any():
            continue
        pred_mean.append(float(p[mask].mean()))
        obs_freq.append(float(observed[mask].mean()))
        counts.append(int(mask.sum()))
    return {"predicted": pred_mean, "observed": obs_freq, "count": counts}


def all_metrics(probs: np.ndarray, outcomes: np.ndarray) -> dict[str, float]:
    """The full reported metric trio + accuracy + ECE (§4.6 — report all)."""
    return {
        "rps": ranked_probability_score(probs, outcomes),
        "brier": brier_score(probs, outcomes),
        "log_loss": log_loss(probs, outcomes),
        "accuracy": top_pick_accuracy(probs, outcomes),
        "ece": expected_calibration_error(probs, outcomes),
        "n": int(np.asarray(outcomes).shape[0]),
    }
