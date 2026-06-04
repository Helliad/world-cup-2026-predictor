"""The Dixon-Coles match model (§4).

Goals for each side are Poisson with means derived from attacking strength and
opponent defensive weakness, plus a global home term and the Dixon & Coles (1997)
low-score correction. Parameters are fit by **time-weighted maximum likelihood**
with an analytic gradient (so the walk-forward search is fast), an L2 ridge, and
partial pooling toward confederation means for sparse teams.

Parameterisation (§4.2), for home team *i* vs away team *j*:

    log λ (home xG) = α_i + β_j + γ·home_flag
    log μ (away xG) = α_j + β_i

where ``home_flag`` is 0 at neutral venues (so γ is identified only from matches
where home/away is meaningful, §8.2). Attack is mean-centred (Σα = 0) for
identifiability. The exact-scoreline probability is

    P(x, y) = τ(x, y; λ, μ, ρ) · Poisson(x; λ) · Poisson(y; μ)

with the Dixon-Coles τ adjustment on the four lowest scorelines.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln

# Soft floor for τ before taking logs, so a transient bad (λ, μ, ρ) during
# optimisation cannot produce -inf/NaN. Rarely active at the optimum.
_TAU_FLOOR = 1e-12
# Tiny ridge on the *raw* (uncentred) attack vector. The objective uses centred
# attack, leaving raw-attack shifts a flat direction; this pins Σα ≈ 0 without
# meaningfully biasing anything.
_ALPHA_SHIFT_RIDGE = 1e-8


def _design_from_matches(
    matches: pd.DataFrame,
    team_index: dict[str, int],
    xi: float,
    ref_date: pd.Timestamp,
    competitive_weight: float,
) -> dict[str, np.ndarray]:
    """Build the dense arrays the likelihood iterates over.

    Only played matches (non-null scores) involving known teams are kept. The
    time-decay weight is ``exp(-xi · age_days)``, optionally up-weighted for
    competitive (non-friendly) matches.
    """
    df = matches
    played = df["home_score"].notna() & df["away_score"].notna()
    df = df[played]
    known = df["home_team"].isin(team_index) & df["away_team"].isin(team_index)
    df = df[known]

    dates = pd.to_datetime(df["date"])
    age_days = (ref_date - dates).dt.days.to_numpy(dtype=np.float64)
    weights = np.exp(-xi * age_days)
    if competitive_weight != 1.0:
        is_competitive = (df["tournament"].astype(str).str.lower() != "friendly").to_numpy()
        weights = weights * np.where(is_competitive, competitive_weight, 1.0)

    hi = df["home_team"].map(team_index).to_numpy(dtype=np.int64)
    ai = df["away_team"].map(team_index).to_numpy(dtype=np.int64)
    x = df["home_score"].to_numpy(dtype=np.float64)
    y = df["away_score"].to_numpy(dtype=np.float64)
    # home_flag = 1 unless neutral venue (then γ applies to neither side).
    neutral = df["neutral"].astype(str).str.upper().eq("TRUE").to_numpy()
    home_flag = np.where(neutral, 0.0, 1.0)

    return {
        "hi": hi,
        "ai": ai,
        "x": x,
        "y": y,
        "w": weights,
        "home_flag": home_flag,
    }


def _neg_log_likelihood(
    theta: np.ndarray,
    design: dict[str, np.ndarray],
    n_teams: int,
    l2: float,
    pooling: float,
    confed_idx: np.ndarray | None,
) -> tuple[float, np.ndarray]:
    """Weighted negative log-likelihood + penalties, with analytic gradient.

    Returns ``(f, grad)`` for ``scipy.optimize.minimize``.
    """
    n = n_teams
    alpha = theta[:n]
    beta = theta[n : 2 * n]
    gamma = theta[2 * n]
    rho = theta[2 * n + 1]

    a = alpha - alpha.mean()  # centred attack (identifiability)

    hi = design["hi"]
    ai = design["ai"]
    x = design["x"]
    y = design["y"]
    w = design["w"]
    hf = design["home_flag"]

    log_lam = a[hi] + beta[ai] + gamma * hf
    log_mu = a[ai] + beta[hi]
    lam = np.exp(log_lam)
    mu = np.exp(log_mu)

    # --- Dixon-Coles τ on the four low scorelines ---
    m00 = (x == 0) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m10 = (x == 1) & (y == 0)
    m11 = (x == 1) & (y == 1)

    tau = np.ones_like(lam)
    tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
    tau[m01] = 1.0 + lam[m01] * rho
    tau[m10] = 1.0 + mu[m10] * rho
    tau[m11] = 1.0 - rho
    tau_safe = np.maximum(tau, _TAU_FLOOR)

    # log-likelihood per match (Poisson kernel; factorial constants omitted —
    # they do not affect the argmin or the gradient).
    ll = x * log_lam - lam + y * log_mu - mu + np.log(tau_safe)
    nll = -float(np.sum(w * ll))

    # --- gradient of the log-likelihood w.r.t. log_lam, log_mu, rho ---
    inv_tau = 1.0 / tau_safe
    # d τ / d λ and d τ / d μ (non-zero only on the low-score masks)
    dtau_dlam = np.zeros_like(lam)
    dtau_dmu = np.zeros_like(lam)
    dtau_drho = np.zeros_like(lam)
    dtau_dlam[m00] = -mu[m00] * rho
    dtau_dmu[m00] = -lam[m00] * rho
    dtau_drho[m00] = -lam[m00] * mu[m00]
    dtau_dlam[m01] = rho
    dtau_drho[m01] = lam[m01]
    dtau_dmu[m10] = rho
    dtau_drho[m10] = mu[m10]
    dtau_drho[m11] = -1.0

    # d log L / d log_lam = (x - λ) + (1/τ)·(dτ/dλ)·λ   (chain: d/dlogλ = λ d/dλ)
    g_loglam = (x - lam) + inv_tau * dtau_dlam * lam
    g_logmu = (y - mu) + inv_tau * dtau_dmu * mu
    g_rho = inv_tau * dtau_drho

    wl = w * g_loglam
    wm = w * g_logmu

    # scatter to per-team attack/defence (centred-attack space)
    dLL_da = np.bincount(hi, wl, minlength=n) + np.bincount(ai, wm, minlength=n)
    dLL_dbeta = np.bincount(ai, wl, minlength=n) + np.bincount(hi, wm, minlength=n)
    # project onto Σα = 0 (gradient of centred attack w.r.t. raw attack)
    dLL_dalpha = dLL_da - dLL_da.mean()
    dLL_dgamma = float(np.sum(wl * hf))
    dLL_drho = float(np.sum(w * g_rho))

    grad_alpha = -dLL_dalpha
    grad_beta = -dLL_dbeta
    grad_gamma = -dLL_dgamma
    grad_rho = -dLL_drho

    # --- penalties (added to the NLL we minimise) ---
    # global ridge toward 0 (= league average, since α is centred)
    nll += l2 * (float(np.sum(a * a)) + float(np.sum(beta * beta)))
    grad_alpha = grad_alpha + 2.0 * l2 * a
    grad_beta = grad_beta + 2.0 * l2 * beta

    # confederation partial pooling toward each team's confederation mean
    if pooling > 0.0 and confed_idx is not None:
        counts = np.bincount(confed_idx, minlength=confed_idx.max() + 1).astype(np.float64)
        sum_a = np.bincount(confed_idx, a, minlength=counts.size)
        sum_b = np.bincount(confed_idx, beta, minlength=counts.size)
        mean_a = sum_a / counts
        mean_b = sum_b / counts
        da = a - mean_a[confed_idx]
        db = beta - mean_b[confed_idx]
        nll += pooling * (float(np.sum(da * da)) + float(np.sum(db * db)))
        # d/dα of Σ(a-mean)^2 simplifies to 2(a-mean): the mean's chain term
        # cancels because within-group deviations sum to zero.
        grad_alpha = grad_alpha + 2.0 * pooling * da
        grad_beta = grad_beta + 2.0 * pooling * db

    # tiny ridge on raw attack to pin the otherwise-flat Σα shift direction
    nll += _ALPHA_SHIFT_RIDGE * float(np.sum(alpha * alpha))
    grad_alpha = grad_alpha + 2.0 * _ALPHA_SHIFT_RIDGE * alpha

    grad = np.concatenate([grad_alpha, grad_beta, [grad_gamma], [grad_rho]])
    return nll, grad


class DixonColesModel:
    """Fitted Dixon-Coles model. See module docstring for the math."""

    def __init__(self, max_goals: int = 10) -> None:
        self.max_goals = max_goals
        self.teams: list[str] = []
        self.team_index: dict[str, int] = {}
        self.attack: np.ndarray = np.zeros(0)  # centred
        self.defence: np.ndarray = np.zeros(0)
        self.gamma: float = 0.0
        self.rho: float = 0.0
        self.xi: float = 0.0
        self.l2: float = 0.0
        self.pooling: float = 0.0
        self.meta: dict = {}

    # ---- fitting ---------------------------------------------------------

    def fit(
        self,
        matches: pd.DataFrame,
        xi: float,
        l2: float,
        *,
        pooling: float = 0.0,
        confederations: dict[str, str] | None = None,
        competitive_weight: float = 1.0,
        ref_date: pd.Timestamp | str | None = None,
        max_iter: int = 500,
        tol: float = 1e-7,
        fit_rho: bool = True,
    ) -> DixonColesModel:
        """Fit by time-weighted MLE. ``xi``/``l2``/``pooling`` are hyperparameters.

        ``matches`` needs columns: date, home_team, away_team, home_score,
        away_score, tournament, neutral. ``ref_date`` (default = latest match
        date) anchors the time-decay clock. Set ``fit_rho=False`` (with ``xi=0``)
        to recover the plain double-Poisson baseline (§4.6.3).
        """
        teams = sorted(set(matches["home_team"]) | set(matches["away_team"]))
        # restrict to teams that actually have a played match
        played = matches[matches["home_score"].notna() & matches["away_score"].notna()]
        active = set(played["home_team"]) | set(played["away_team"])
        teams = [t for t in teams if t in active]
        team_index = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        if ref_date is None:
            ref = pd.to_datetime(played["date"]).max()
        else:
            ref = pd.to_datetime(ref_date)

        design = _design_from_matches(played, team_index, xi, ref, competitive_weight)

        confed_idx = None
        confed_names: list[str] = []
        if pooling > 0.0 and confederations is not None:
            from model.ratings import build_confederation_index

            confed_idx, confed_names = build_confederation_index(teams, confederations)

        theta0 = np.zeros(2 * n + 2)
        theta0[2 * n] = 0.25  # gamma init (typical home log-advantage)
        theta0[2 * n + 1] = 0.0 if not fit_rho else -0.05  # rho init (DC value)

        rho_bounds = (0.0, 0.0) if not fit_rho else (-0.15, 0.15)
        bounds = [(None, None)] * (2 * n) + [(-1.0, 1.0), rho_bounds]

        result = minimize(
            _neg_log_likelihood,
            theta0,
            args=(design, n, l2, pooling, confed_idx),
            method="L-BFGS-B",
            jac=True,
            bounds=bounds,
            options={"maxiter": max_iter, "ftol": tol, "gtol": tol * 10},
        )

        theta = result.x
        alpha = theta[:n]
        self.teams = teams
        self.team_index = team_index
        self.attack = alpha - alpha.mean()  # store centred
        self.defence = theta[n : 2 * n].copy()
        self.gamma = float(theta[2 * n])
        self.rho = float(theta[2 * n + 1])
        self.xi = xi
        self.l2 = l2
        self.pooling = pooling
        self.meta = {
            "n_teams": n,
            "n_matches": int(design["w"].size),
            "sum_weights": float(design["w"].sum()),
            "ref_date": str(ref.date()),
            "half_life_days": (math.log(2) / xi) if xi > 0 else None,
            "competitive_weight": competitive_weight,
            "confederations": confed_names,
            "optimizer_success": bool(result.success),
            "optimizer_iterations": int(result.nit),
            "final_nll": float(result.fun),
        }
        return self

    # ---- prediction ------------------------------------------------------

    def expected_goals(
        self, home: str, away: str, home_advantage: float | None = None
    ) -> tuple[float, float]:
        """Return (λ, μ) for a fixture. ``home_advantage`` overrides γ (pass 0
        for a neutral venue; pass a reduced γ for a co-host playing at home)."""
        i = self.team_index[home]
        j = self.team_index[away]
        ha = self.gamma if home_advantage is None else home_advantage
        lam = math.exp(self.attack[i] + self.defence[j] + ha)
        mu = math.exp(self.attack[j] + self.defence[i])
        return lam, mu

    def predict_scoreline_matrix(
        self,
        home: str,
        away: str,
        max_goals: int | None = None,
        home_advantage: float | None = None,
    ) -> np.ndarray:
        """Return an ``(G+1, G+1)`` matrix ``P`` where ``P[x, y] = P(home x : away y)``.

        Renormalised to sum to 1 after τ adjustment and truncation at ``max_goals``.
        """
        g = self.max_goals if max_goals is None else max_goals
        lam, mu = self.expected_goals(home, away, home_advantage)

        ks = np.arange(g + 1)
        log_fact = gammaln(ks + 1.0)
        px = np.exp(ks * math.log(lam) - lam - log_fact)
        py = np.exp(ks * math.log(mu) - mu - log_fact)
        P = np.outer(px, py)

        rho = self.rho
        P[0, 0] *= 1.0 - lam * mu * rho
        P[0, 1] *= 1.0 + lam * rho
        P[1, 0] *= 1.0 + mu * rho
        P[1, 1] *= 1.0 - rho

        # For extreme mismatches (very large λ or μ) a τ factor such as 1 + λρ can
        # go negative, leaving a tiny negative cell. Clamp to keep P a valid
        # non-negative distribution (also keeps np.random.choice samplers safe).
        np.clip(P, 0.0, None, out=P)
        total = P.sum()
        if total > 0:
            P /= total
        return P

    def predict_outcome(
        self, home: str, away: str, home_advantage: float | None = None
    ) -> dict[str, float]:
        """Collapse the scoreline matrix into 1X2 probabilities + expected goals."""
        P = self.predict_scoreline_matrix(home, away, home_advantage=home_advantage)
        ks = np.arange(P.shape[0])
        home_win = float(np.tril(P, -1).sum())  # x > y
        away_win = float(np.triu(P, 1).sum())  # y > x
        draw = float(np.trace(P))
        exp_home = float((P.sum(axis=1) * ks).sum())
        exp_away = float((P.sum(axis=0) * ks).sum())
        return {
            "home_win": home_win,
            "draw": draw,
            "away_win": away_win,
            "exp_home": exp_home,
            "exp_away": exp_away,
        }

    # ---- persistence -----------------------------------------------------

    def save(self, path: str | Path) -> None:
        payload = {
            "model_type": "dixon_coles",
            "max_goals": self.max_goals,
            "teams": self.teams,
            "attack": self.attack.tolist(),
            "defence": self.defence.tolist(),
            "gamma": self.gamma,
            "rho": self.rho,
            "xi": self.xi,
            "l2": self.l2,
            "pooling": self.pooling,
            "meta": self.meta,
        }
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, path: str | Path) -> DixonColesModel:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        model = cls(max_goals=payload["max_goals"])
        model.teams = payload["teams"]
        model.team_index = {t: i for i, t in enumerate(model.teams)}
        model.attack = np.array(payload["attack"], dtype=np.float64)
        model.defence = np.array(payload["defence"], dtype=np.float64)
        model.gamma = payload["gamma"]
        model.rho = payload["rho"]
        model.xi = payload["xi"]
        model.l2 = payload["l2"]
        model.pooling = payload.get("pooling", 0.0)
        model.meta = payload.get("meta", {})
        return model
