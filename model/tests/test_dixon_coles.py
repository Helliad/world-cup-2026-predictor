"""Tests for the Dixon-Coles match model (model/dixon_coles.py, §4.7).

Covers the core spec rules: scoreline matrices are proper distributions, 1X2
probabilities partition unity, ordering of win probabilities respects relative
strength, fitting is deterministic, the analytic gradient matches a numeric one,
save/load round-trips parameters, and the home-advantage knob moves the home-win
probability in the expected direction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import check_grad

from model.dixon_coles import (
    DixonColesModel,
    _design_from_matches,
    _neg_log_likelihood,
)

PARAMS_PATH = "model/params.json"


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


def make_synthetic_matches(seed: int = 0, n_teams: int = 6, n_matches: int = 80) -> pd.DataFrame:
    """Build a tiny synthetic results table with a known strength gradient.

    Teams ``T0..T{n-1}`` have increasing latent attacking strength, so the
    likelihood has signal to fit. Goals are Poisson around strength-derived
    means. Schema matches what ``fit`` / ``_design_from_matches`` consume:
    date, home_team, away_team, home_score, away_score, tournament, neutral.
    """
    rng = np.random.default_rng(seed)
    teams = [f"T{i}" for i in range(n_teams)]
    # latent attack/defence so that higher-index teams are stronger
    atk = np.linspace(-0.4, 0.4, n_teams)
    dfc = np.linspace(0.3, -0.3, n_teams)
    gamma = 0.25

    base = pd.Timestamp("2020-01-01")
    rows = []
    for k in range(n_matches):
        i, j = rng.choice(n_teams, size=2, replace=False)
        lam = np.exp(atk[i] + dfc[j] + gamma)
        mu = np.exp(atk[j] + dfc[i])
        hs = int(rng.poisson(lam))
        as_ = int(rng.poisson(mu))
        rows.append(
            {
                "date": base + pd.Timedelta(days=int(k * 5)),
                "home_team": teams[i],
                "away_team": teams[j],
                "home_score": hs,
                "away_score": as_,
                "tournament": "Friendly" if k % 3 == 0 else "WorldCup",
                "neutral": "FALSE",
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def real_model() -> DixonColesModel:
    return DixonColesModel.load(PARAMS_PATH)


@pytest.fixture(scope="module")
def synth_matches() -> pd.DataFrame:
    return make_synthetic_matches(seed=12345)


# --------------------------------------------------------------------------- #
# (1) scoreline matrix is a proper probability distribution
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "home,away",
    [
        ("Spain", "Cook Islands"),
        ("Brazil", "Argentina"),
        ("Germany", "Gibraltar"),
        ("Cook Islands", "Spain"),
        ("San Marino", "France"),
    ],
)
def test_scoreline_matrix_sums_to_one(real_model: DixonColesModel, home, away):
    P = real_model.predict_scoreline_matrix(home, away)
    assert P.shape == (real_model.max_goals + 1, real_model.max_goals + 1)
    assert P.sum() == pytest.approx(1.0, abs=1e-6)


def test_scoreline_matrix_nonnegative_balanced(real_model: DixonColesModel):
    """For ordinary (non-blowout) fixtures the τ adjustment keeps every cell
    non-negative, so the matrix is a genuine probability distribution."""
    for home, away in [("Brazil", "Argentina"), ("France", "Germany"), ("Spain", "Brazil")]:
        P = real_model.predict_scoreline_matrix(home, away)
        assert np.all(P >= 0.0), f"{home} vs {away} has a negative scoreline cell"


def test_scoreline_matrix_nonnegative_blowout(real_model: DixonColesModel):
    # Extreme mismatch: the DC tau factor 1 + lam*rho can go negative for very
    # large lam; predict_scoreline_matrix clamps the result to a valid
    # non-negative distribution (regression test for the clamp).
    P = real_model.predict_scoreline_matrix("Spain", "Cook Islands")
    assert np.all(P >= 0.0)
    assert P.sum() == pytest.approx(1.0, abs=1e-6)


def test_scoreline_matrix_custom_max_goals_sums_to_one(real_model: DixonColesModel):
    P = real_model.predict_scoreline_matrix("Brazil", "Germany", max_goals=4)
    assert P.shape == (5, 5)
    assert P.sum() == pytest.approx(1.0, abs=1e-6)


# --------------------------------------------------------------------------- #
# (2) predict_outcome 1X2 probabilities partition unity
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "home,away",
    [
        ("Spain", "Cook Islands"),
        ("Brazil", "Argentina"),
        ("France", "Germany"),
        ("Gibraltar", "San Marino"),
    ],
)
def test_outcome_probabilities_sum_to_one(real_model: DixonColesModel, home, away):
    out = real_model.predict_outcome(home, away)
    total = out["home_win"] + out["draw"] + out["away_win"]
    assert total == pytest.approx(1.0, abs=1e-6)
    for key in ("home_win", "draw", "away_win"):
        assert 0.0 <= out[key] <= 1.0
    # expected goals should be non-negative and finite
    assert out["exp_home"] >= 0.0 and np.isfinite(out["exp_home"])
    assert out["exp_away"] >= 0.0 and np.isfinite(out["exp_away"])


def test_outcome_expected_goals_match_matrix(real_model: DixonColesModel):
    """exp_home/exp_away returned by predict_outcome agree with the matrix marginals."""
    home, away = "Brazil", "Gibraltar"
    P = real_model.predict_scoreline_matrix(home, away)
    ks = np.arange(P.shape[0])
    exp_home = float((P.sum(axis=1) * ks).sum())
    exp_away = float((P.sum(axis=0) * ks).sum())
    out = real_model.predict_outcome(home, away)
    assert out["exp_home"] == pytest.approx(exp_home, abs=1e-9)
    assert out["exp_away"] == pytest.approx(exp_away, abs=1e-9)


# --------------------------------------------------------------------------- #
# (3) a clearly stronger team wins more often than the reverse fixture
# --------------------------------------------------------------------------- #


def test_stronger_team_has_higher_win_prob(real_model: DixonColesModel):
    strong, weak = "Spain", "Cook Islands"
    out_fwd = real_model.predict_outcome(strong, weak)  # strong at home
    out_rev = real_model.predict_outcome(weak, strong)  # weak at home

    # Strong team's home win prob should dominate.
    assert out_fwd["home_win"] > out_fwd["away_win"]
    # And the strong team should win far more often than when it is the away
    # side in the reversed fixture (its away_win there) -- but more simply, its
    # win prob when home (out_fwd.home_win) exceeds the weak team's win prob
    # when home (out_rev.home_win).
    assert out_fwd["home_win"] > out_rev["home_win"]
    # Sanity: a strong-vs-weak top-tier mismatch is decisive.
    assert out_fwd["home_win"] > 0.6


def test_stronger_team_more_expected_goals(real_model: DixonColesModel):
    out = real_model.predict_outcome("Spain", "Cook Islands")
    assert out["exp_home"] > out["exp_away"]


# --------------------------------------------------------------------------- #
# (4) fitting is deterministic
# --------------------------------------------------------------------------- #


def test_fit_is_deterministic(synth_matches: pd.DataFrame):
    kwargs = {"xi": 0.0008, "l2": 0.01}
    m1 = DixonColesModel().fit(synth_matches, **kwargs)
    m2 = DixonColesModel().fit(synth_matches, **kwargs)

    assert m1.teams == m2.teams
    np.testing.assert_array_equal(m1.attack, m2.attack)
    np.testing.assert_array_equal(m1.defence, m2.defence)
    assert m1.gamma == m2.gamma
    assert m1.rho == m2.rho

    # Attack is stored mean-centred (identifiability constraint Σα = 0).
    assert m1.attack.sum() == pytest.approx(0.0, abs=1e-6)


def test_fit_recovers_strength_ordering(synth_matches: pd.DataFrame):
    """Sanity that fit produces a usable model: higher-index synthetic teams,
    constructed to be stronger, should end up with higher (attack - defence)."""
    m = DixonColesModel().fit(synth_matches, xi=0.0, l2=0.001)
    strength = {t: m.attack[i] - m.defence[i] for t, i in m.team_index.items()}
    # T0 is the weakest, T5 (or T{n-1}) the strongest by construction.
    last = f"T{len(m.teams) - 1}"
    assert strength[last] > strength["T0"]


# --------------------------------------------------------------------------- #
# (5) analytic gradient matches numeric (scipy.optimize.check_grad)
# --------------------------------------------------------------------------- #


def test_analytic_gradient_matches_numeric(synth_matches: pd.DataFrame):
    teams = sorted(set(synth_matches["home_team"]) | set(synth_matches["away_team"]))
    team_index = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    ref = pd.to_datetime(synth_matches["date"]).max()
    design = _design_from_matches(
        synth_matches, team_index, xi=0.001, ref_date=ref, competitive_weight=1.0
    )

    l2 = 0.02
    pooling = 0.0
    confed_idx = None

    def f(theta):
        return _neg_log_likelihood(theta, design, n, l2, pooling, confed_idx)[0]

    def g(theta):
        return _neg_log_likelihood(theta, design, n, l2, pooling, confed_idx)[1]

    rng = np.random.default_rng(7)
    # perturb attack/defence/gamma; keep rho within its meaningful range
    theta = np.zeros(2 * n + 2)
    theta[: 2 * n] = rng.normal(scale=0.2, size=2 * n)
    theta[2 * n] = 0.3  # gamma
    theta[2 * n + 1] = -0.05  # rho

    err = check_grad(f, g, theta)
    assert err < 1e-4, f"analytic/numeric gradient mismatch: {err}"


def test_analytic_gradient_matches_numeric_with_pooling(synth_matches: pd.DataFrame):
    """The pooling penalty term also contributes to the analytic gradient."""
    teams = sorted(set(synth_matches["home_team"]) | set(synth_matches["away_team"]))
    team_index = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    ref = pd.to_datetime(synth_matches["date"]).max()
    design = _design_from_matches(
        synth_matches, team_index, xi=0.0, ref_date=ref, competitive_weight=1.0
    )

    # two confederations: split teams in half
    confed_idx = np.array([0 if i < n // 2 else 1 for i in range(n)], dtype=np.int64)
    l2 = 0.0
    pooling = 0.05

    def f(theta):
        return _neg_log_likelihood(theta, design, n, l2, pooling, confed_idx)[0]

    def g(theta):
        return _neg_log_likelihood(theta, design, n, l2, pooling, confed_idx)[1]

    rng = np.random.default_rng(99)
    theta = np.zeros(2 * n + 2)
    theta[: 2 * n] = rng.normal(scale=0.15, size=2 * n)
    theta[2 * n] = 0.25
    theta[2 * n + 1] = -0.04

    err = check_grad(f, g, theta)
    assert err < 1e-4, f"analytic/numeric gradient mismatch (pooling): {err}"


# --------------------------------------------------------------------------- #
# (6) save / load round-trips parameters and predictions
# --------------------------------------------------------------------------- #


def test_save_load_roundtrip(synth_matches: pd.DataFrame, tmp_path):
    m = DixonColesModel().fit(synth_matches, xi=0.0005, l2=0.01)
    path = tmp_path / "rt_params.json"
    m.save(path)
    loaded = DixonColesModel.load(path)

    assert loaded.teams == m.teams
    np.testing.assert_array_equal(loaded.attack, m.attack)
    np.testing.assert_array_equal(loaded.defence, m.defence)
    assert loaded.gamma == m.gamma
    assert loaded.rho == m.rho
    assert loaded.max_goals == m.max_goals

    # Predictions must be byte-for-byte identical after a round-trip.
    home, away = m.teams[0], m.teams[-1]
    P_orig = m.predict_scoreline_matrix(home, away)
    P_load = loaded.predict_scoreline_matrix(home, away)
    np.testing.assert_array_equal(P_orig, P_load)

    o_orig = m.predict_outcome(home, away)
    o_load = loaded.predict_outcome(home, away)
    assert o_orig == o_load


def test_real_model_save_load_roundtrip(real_model: DixonColesModel, tmp_path):
    path = tmp_path / "real_rt.json"
    real_model.save(path)
    reloaded = DixonColesModel.load(path)
    P1 = real_model.predict_scoreline_matrix("Spain", "Cook Islands")
    P2 = reloaded.predict_scoreline_matrix("Spain", "Cook Islands")
    np.testing.assert_array_equal(P1, P2)


# --------------------------------------------------------------------------- #
# (7) home_advantage knob moves home_win in the expected direction
# --------------------------------------------------------------------------- #


def test_home_advantage_zero_reduces_home_win(real_model: DixonColesModel):
    """Removing the home term (home_advantage=0) must not increase home_win and,
    for a balanced-ish fixture with positive gamma, should strictly reduce it."""
    assert real_model.gamma > 0.0, "fixture assumes a positive home advantage"
    home, away = "Brazil", "Argentina"

    out_default = real_model.predict_outcome(home, away)  # uses gamma
    out_neutral = real_model.predict_outcome(home, away, home_advantage=0.0)

    assert out_neutral["home_win"] < out_default["home_win"]
    # Symmetrically, away_win should rise when the home edge is removed.
    assert out_neutral["away_win"] > out_default["away_win"]
    # Expected home goals also drop when the home boost is removed.
    assert out_neutral["exp_home"] < out_default["exp_home"]


def test_home_advantage_larger_increases_home_win(real_model: DixonColesModel):
    home, away = "France", "Germany"
    out_default = real_model.predict_outcome(home, away)
    out_boosted = real_model.predict_outcome(home, away, home_advantage=real_model.gamma + 0.5)
    assert out_boosted["home_win"] > out_default["home_win"]


def test_expected_goals_home_advantage_override(real_model: DixonColesModel):
    """expected_goals with home_advantage=0 should give a smaller lambda than
    the default gamma case (mu is unaffected by the home term)."""
    lam_def, mu_def = real_model.expected_goals("Brazil", "Argentina")
    lam_neut, mu_neut = real_model.expected_goals("Brazil", "Argentina", home_advantage=0.0)
    assert lam_neut < lam_def
    assert mu_neut == pytest.approx(mu_def, abs=1e-12)
