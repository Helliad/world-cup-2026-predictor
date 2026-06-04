"""Knockout resolution and bracket folding (§6.3, §6.4).

A knockout tie is resolved in three explicit stages — regulation (90'), extra
time (30', goal rates scaled to ~1/3 of a full match), then a penalty shootout
(near coin-flip with a small, capped skill tilt). Collapsing these into one coin
flip systematically under-rewards strong teams; staging keeps title odds honest.

Both a *sampled* resolver (``play_knockout_match``) and a closed-form *win
probability* (``knockout_win_prob``) are provided and kept consistent, so the
Monte Carlo can precompute a 48×48 win-probability matrix instead of sampling
every knockout goal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.special import gammaln

# Strength-gap scale (in α−β units) for the shootout skill tilt.
_SHOOTOUT_GAP_SCALE = 1.0


@dataclass(frozen=True)
class KnockoutParams:
    """Knockout knobs resolved from config (§6.7)."""

    mode: str = "staged"  # "staged" | "coinflip"
    extra_time_fraction: float = 1.0 / 3.0
    penalty_skill_tilt: bool = True
    penalty_cap: float = 0.55

    @classmethod
    def from_config(cls, cfg: dict) -> KnockoutParams:
        k = cfg["simulation"]["knockout"]
        return cls(
            mode=k["mode"],
            extra_time_fraction=k["extra_time_fraction"],
            penalty_skill_tilt=k["penalty_skill_tilt"],
            penalty_cap=k["penalty_cap"],
        )


def _poisson_matrix(lam: float, mu: float, max_goals: int) -> np.ndarray:
    """Plain double-Poisson scoreline matrix (no DC τ) — used for extra time."""
    ks = np.arange(max_goals + 1)
    log_fact = gammaln(ks + 1.0)
    px = np.exp(ks * math.log(lam) - lam - log_fact)
    py = np.exp(ks * math.log(mu) - mu - log_fact)
    P = np.outer(px, py)
    return P / P.sum()


def _wdl(P: np.ndarray) -> tuple[float, float, float]:
    """(home/a win, draw, away/b win) from a scoreline matrix."""
    return float(np.tril(P, -1).sum()), float(np.trace(P)), float(np.triu(P, 1).sum())


def sample_scoreline(
    model, home: str, away: str, home_adv: float, rng: np.random.Generator
) -> tuple[int, int]:
    """Sample one (home_goals, away_goals) from the DC scoreline distribution."""
    P = model.predict_scoreline_matrix(home, away, home_advantage=home_adv)
    flat = P.ravel()
    flat = flat / flat.sum()
    idx = rng.choice(flat.size, p=flat)
    ncols = P.shape[1]
    x, y = divmod(int(idx), ncols)
    return x, y


def _shootout_prob_a(model, a: str, b: str, params: KnockoutParams) -> float:
    """P(a wins the shootout): 0.5, or a capped tanh tilt in the strength gap."""
    if not params.penalty_skill_tilt:
        return 0.5
    ia, ib = model.team_index[a], model.team_index[b]
    strength_a = model.attack[ia] - model.defence[ia]
    strength_b = model.attack[ib] - model.defence[ib]
    gap = (strength_a - strength_b) / _SHOOTOUT_GAP_SCALE
    amp = params.penalty_cap - 0.5
    return 0.5 + amp * math.tanh(gap)


def knockout_win_prob(model, a: str, b: str, params: KnockoutParams) -> float:
    """Closed-form P(a beats b) under the configured resolution mode."""
    reg = model.predict_scoreline_matrix(a, b, home_advantage=0.0)
    a_reg, draw_reg, _ = _wdl(reg)
    if params.mode == "coinflip":
        return a_reg + 0.5 * draw_reg

    lam, mu = model.expected_goals(a, b, home_advantage=0.0)
    et = _poisson_matrix(
        lam * params.extra_time_fraction, mu * params.extra_time_fraction, model.max_goals
    )
    a_et, draw_et, _ = _wdl(et)
    ps = _shootout_prob_a(model, a, b, params)
    return a_reg + draw_reg * (a_et + draw_et * ps)


def play_knockout_match(
    team_a: str, team_b: str, model, rng: np.random.Generator, params: KnockoutParams
) -> str:
    """Sampled staged resolution; returns the winner's name. Never returns a draw."""
    # 1. Regulation
    x, y = sample_scoreline(model, team_a, team_b, 0.0, rng)
    if x > y:
        return team_a
    if y > x:
        return team_b
    if params.mode == "coinflip":
        return team_a if rng.random() < 0.5 else team_b

    # 2. Extra time (scaled rates, plain Poisson)
    lam, mu = model.expected_goals(team_a, team_b, home_advantage=0.0)
    et = _poisson_matrix(
        lam * params.extra_time_fraction, mu * params.extra_time_fraction, model.max_goals
    )
    flat = et.ravel()
    idx = rng.choice(flat.size, p=flat)
    xa, yb = divmod(int(idx), et.shape[1])
    if xa > yb:
        return team_a
    if yb > xa:
        return team_b

    # 3. Penalty shootout
    p_a = _shootout_prob_a(model, team_a, team_b, params)
    return team_a if rng.random() < p_a else team_b


def build_winprob_matrix(model, params: KnockoutParams, teams: list[str]) -> np.ndarray:
    """Precompute W[i, j] = P(teams[i] beats teams[j]) for the Monte Carlo."""
    n = len(teams)
    W = np.full((n, n), 0.5)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            W[i, j] = knockout_win_prob(model, teams[i], teams[j], params)
    return W
