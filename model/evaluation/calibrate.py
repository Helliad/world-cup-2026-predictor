"""Post-hoc calibration (§4.6.5).

The Monte Carlo compounds per-match probabilities across seven rounds, so small
biases blow up — calibration matters. Both methods are fit on a *validation*
block and applied later, never fit on the test block.

- **Temperature scaling**: a single scalar T sharpens (T<1) or softens (T>1) the
  distribution via q_k ∝ p_k^(1/T). One parameter, robust, the default.
- **Isotonic**: per-class monotone remap via pool-adjacent-violators, then
  renormalise. More flexible, needs more validation data.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize_scalar

from model.evaluation.metrics import log_loss

_EPS = 1e-12


def _apply_temperature(probs: np.ndarray, t: float) -> np.ndarray:
    p = np.clip(probs, _EPS, 1.0)
    scaled = p ** (1.0 / t)
    return scaled / scaled.sum(axis=1, keepdims=True)


def fit_temperature(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Find T minimising log-loss on the validation set."""
    res = minimize_scalar(
        lambda t: log_loss(_apply_temperature(probs, t), outcomes),
        bounds=(0.3, 5.0),
        method="bounded",
    )
    return float(res.x)


def _pav(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Pool-adjacent-violators: fit a non-decreasing step function y~x."""
    order = np.argsort(x, kind="mergesort")
    y_ord, w_ord = y[order].astype(float), w[order].astype(float)
    # blocks of (value, weight)
    vals = list(y_ord)
    wts = list(w_ord)
    i = 0
    while i < len(vals) - 1:
        if vals[i] > vals[i + 1] + 1e-15:
            new_w = wts[i] + wts[i + 1]
            new_v = (vals[i] * wts[i] + vals[i + 1] * wts[i + 1]) / new_w
            vals[i : i + 2] = [new_v]
            wts[i : i + 2] = [new_w]
            if i > 0:
                i -= 1
        else:
            i += 1
    # expand back
    fitted = np.empty_like(y_ord)
    pos = 0
    for v, wt_count in zip(vals, _block_sizes(w_ord, wts), strict=False):
        fitted[pos : pos + wt_count] = v
        pos += wt_count
    inv = np.empty_like(fitted)
    inv[order] = fitted
    return inv


def _block_sizes(orig_w: np.ndarray, block_w: list[float]) -> list[int]:
    """Recover how many original points each merged block covers (weights are 1
    here, so block weight == element count)."""
    return [int(round(b)) for b in block_w]


class Calibrator:
    """Fitted calibration map. ``method`` in {none, temperature, isotonic}."""

    def __init__(self, method: str = "temperature") -> None:
        self.method = method
        self.temperature: float = 1.0
        self._iso: list[tuple[np.ndarray, np.ndarray]] = []

    def fit(self, probs: np.ndarray, outcomes: np.ndarray) -> Calibrator:
        if self.method == "none":
            return self
        if self.method == "temperature":
            self.temperature = fit_temperature(probs, outcomes)
            return self
        if self.method == "isotonic":
            for k in range(3):
                target = (np.asarray(outcomes) == k).astype(float)
                x = np.asarray(probs)[:, k]
                fitted = _pav(x, target, np.ones_like(target))
                order = np.argsort(x, kind="mergesort")
                self._iso.append((x[order], fitted[order]))
            return self
        raise ValueError(f"Unknown calibration method: {self.method}")

    def transform(self, probs: np.ndarray) -> np.ndarray:
        if self.method in ("none",):
            return np.asarray(probs, dtype=np.float64)
        if self.method == "temperature":
            return _apply_temperature(np.asarray(probs, dtype=np.float64), self.temperature)
        if self.method == "isotonic":
            p = np.asarray(probs, dtype=np.float64)
            out = np.empty_like(p)
            for k, (xs, ys) in enumerate(self._iso):
                out[:, k] = np.interp(p[:, k], xs, ys)
            row = out.sum(axis=1, keepdims=True)
            row[row == 0] = 1.0
            return out / row
        raise ValueError(f"Unknown calibration method: {self.method}")

    def describe(self) -> dict:
        return {"method": self.method, "temperature": self.temperature}
