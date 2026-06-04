"""Tests for the staged knockout resolver (§6.3, §6.8).

Exercises ``simulation/knockout.py``: the sampled resolver
(``play_knockout_match``), the closed-form win probability
(``knockout_win_prob``), the capped shootout tilt (``_shootout_prob_a``), the
precomputed win-probability matrix (``build_winprob_matrix``), and scoreline
sampling (``sample_scoreline``).

The real fitted model is loaded once (session-scoped) since these are read-only
predictions. All randomness flows through ``np.random.default_rng(seed)`` so the
empirical checks are deterministic.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from model.dixon_coles import DixonColesModel
from simulation.knockout import (
    KnockoutParams,
    _shootout_prob_a,
    build_winprob_matrix,
    knockout_win_prob,
    play_knockout_match,
    sample_scoreline,
)

MODEL_PATH = "model/params.json"

# A clearly-favoured strong team vs a meaningfully weaker but non-trivial
# opponent: the win prob is well above 0.5 yet strictly below 1.0, so we can
# test both ordering (staged > coinflip) and the (0, 1) bounds without bumping
# into floating-point saturation at 1.0.
STRONG = "Argentina"
WEAK = "Japan"


@pytest.fixture(scope="module")
def model() -> DixonColesModel:
    return DixonColesModel.load(MODEL_PATH)


@pytest.fixture(scope="module")
def staged() -> KnockoutParams:
    return KnockoutParams(
        mode="staged",
        extra_time_fraction=1.0 / 3.0,
        penalty_skill_tilt=True,
        penalty_cap=0.55,
    )


@pytest.fixture(scope="module")
def coinflip() -> KnockoutParams:
    return KnockoutParams(
        mode="coinflip",
        extra_time_fraction=1.0 / 3.0,
        penalty_skill_tilt=True,
        penalty_cap=0.55,
    )


# --------------------------------------------------------------------------- #
# (1) play_knockout_match never produces a draw — always one of the two teams. #
# --------------------------------------------------------------------------- #
def test_play_knockout_match_always_returns_a_team(model, staged):
    rng = np.random.default_rng(20260604)
    # Use a near-even pair so plenty of ties go to ET / shootout and exercise
    # every resolution stage, not just regulation.
    a, b = "Spain", "Brazil"
    winners = {a: 0, b: 0}
    n = 800
    for _ in range(n):
        w = play_knockout_match(a, b, model, rng, staged)
        assert w in (a, b), f"resolver returned {w!r}, not one of the two teams"
        winners[w] += 1
    # Both outcomes must actually occur for an even pair (sanity that it is not
    # degenerate / always-team-a), and the counts must sum to every trial.
    assert winners[a] + winners[b] == n
    assert winners[a] > 0 and winners[b] > 0


def test_play_knockout_match_coinflip_branch_returns_a_team(model, coinflip):
    """The coinflip branch (regulation draw -> rng coin) also never draws."""
    rng = np.random.default_rng(7)
    a, b = "Spain", "Brazil"
    for _ in range(300):
        w = play_knockout_match(a, b, model, rng, coinflip)
        assert w in (a, b)


# --------------------------------------------------------------------------- #
# (2) Empirical favourite win-rate matches the closed-form within ~3 SE.       #
# --------------------------------------------------------------------------- #
def test_empirical_winrate_matches_closed_form(model, staged):
    rng = np.random.default_rng(424242)
    a, b = STRONG, WEAK
    p = knockout_win_prob(model, a, b, staged)
    assert 0.0 < p < 1.0

    n = 1500
    wins_a = sum(play_knockout_match(a, b, model, rng, staged) == a for _ in range(n))
    phat = wins_a / n
    se = math.sqrt(p * (1.0 - p) / n)
    # Sampled resolver and closed form share the same staged math, so they must
    # agree to within Monte-Carlo noise (3 SE ~ 99.7% interval).
    assert abs(phat - p) <= 3.0 * se, (
        f"empirical {phat:.4f} vs closed-form {p:.4f} differ by "
        f"{abs(phat - p):.4f} > 3*SE={3 * se:.4f}"
    )


# --------------------------------------------------------------------------- #
# (3) Staged beats coinflip for the favourite, and is strictly in (coin, 1).   #
# --------------------------------------------------------------------------- #
def test_staged_rewards_strong_team_more_than_coinflip(model, staged, coinflip):
    a, b = STRONG, WEAK
    p_staged = knockout_win_prob(model, a, b, staged)
    p_coin = knockout_win_prob(model, a, b, coinflip)

    # The favourite is genuinely favoured under both modes.
    assert p_coin > 0.5
    assert p_staged > 0.5
    # Staging the tie-break (ET + skill-tilted shootout) hands the stronger team
    # strictly more than collapsing the draw mass to a 50/50 coin flip...
    assert p_staged > p_coin
    # ...but never a certainty: staged sits strictly between coinflip and 1.0.
    assert p_coin < p_staged < 1.0


def test_staged_is_antisymmetric_in_ordering(model, staged):
    """Swapping the teams flips who is favoured; the underdog wins prob < 0.5."""
    p_ab = knockout_win_prob(model, STRONG, WEAK, staged)
    p_ba = knockout_win_prob(model, WEAK, STRONG, staged)
    assert p_ab > 0.5 > p_ba
    # No home advantage in a knockout (home_advantage=0.0), so the two should be
    # near-complementary; allow a little slack for the ET plain-Poisson stage.
    assert abs((p_ab + p_ba) - 1.0) < 0.05


# --------------------------------------------------------------------------- #
# (4) Shootout tilt respects the cap, and collapses to 0.5 when disabled.      #
# --------------------------------------------------------------------------- #
def test_shootout_prob_respects_cap(model):
    params = KnockoutParams(penalty_skill_tilt=True, penalty_cap=0.55)
    lo, hi = 1.0 - params.penalty_cap, params.penalty_cap
    pairs = [
        ("Argentina", "American Samoa"),  # extreme gap -> hugs the cap
        ("American Samoa", "Argentina"),  # extreme gap, other direction
        ("Spain", "Brazil"),
        ("Japan", "Argentina"),
    ]
    for a, b in pairs:
        ps = _shootout_prob_a(model, a, b, params)
        assert lo <= ps <= hi, f"{a} vs {b}: shootout prob {ps} outside [{lo}, {hi}]"

    # The extreme favourite must approach (but never exceed) the cap.
    extreme = _shootout_prob_a(model, "Argentina", "American Samoa", params)
    assert extreme > 0.5
    assert extreme <= params.penalty_cap


def test_shootout_prob_is_half_without_tilt(model):
    params = KnockoutParams(penalty_skill_tilt=False, penalty_cap=0.55)
    assert _shootout_prob_a(model, "Argentina", "American Samoa", params) == 0.5
    assert _shootout_prob_a(model, "Spain", "Brazil", params) == 0.5


def test_shootout_prob_is_skew_symmetric(model):
    """P(a) + P(b) about the shootout = 1 (tilt is odd in the strength gap)."""
    params = KnockoutParams(penalty_skill_tilt=True, penalty_cap=0.55)
    pa = _shootout_prob_a(model, "Spain", "Brazil", params)
    pb = _shootout_prob_a(model, "Brazil", "Spain", params)
    assert pa == pytest.approx(1.0 - pb, abs=1e-12)
    # Equal-skill pair (a team vs itself) yields exactly 0.5 (tanh(0) = 0).
    assert _shootout_prob_a(model, "Spain", "Spain", params) == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# (5) build_winprob_matrix: square, ~0.5 diagonal, off-diagonal in (0, 1).     #
# --------------------------------------------------------------------------- #
def test_build_winprob_matrix_shape_and_bounds(model, staged):
    teams = ["Argentina", "Spain", "Brazil", "Japan", "American Samoa"]
    W = build_winprob_matrix(model, staged, teams)
    n = len(teams)

    assert W.shape == (n, n)
    # Diagonal is the self-match placeholder, exactly 0.5.
    assert np.allclose(np.diag(W), 0.5)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            assert 0.0 < W[i, j] < 1.0, f"W[{i},{j}]={W[i, j]} not in (0,1)"

    # Off-diagonal entries match the closed-form for the corresponding pair.
    assert W[0, 3] == pytest.approx(knockout_win_prob(model, teams[0], teams[3], staged))
    # Stronger team's row entry beats the reverse direction.
    assert W[0, 3] > W[3, 0]
    # W[i,j] + W[j,i] need not equal 1, but should be close (no home edge).
    assert abs((W[0, 3] + W[3, 0]) - 1.0) < 0.05


# --------------------------------------------------------------------------- #
# Extra: sample_scoreline returns valid in-range non-negative integer goals.   #
# --------------------------------------------------------------------------- #
def test_sample_scoreline_valid_goals(model):
    rng = np.random.default_rng(99)
    g = model.max_goals
    for _ in range(200):
        x, y = sample_scoreline(model, STRONG, WEAK, 0.0, rng)
        assert isinstance(x, int) and isinstance(y, int)
        assert 0 <= x <= g
        assert 0 <= y <= g

    # The favourite should, on average, outscore the underdog over many draws.
    rng = np.random.default_rng(1234)
    n = 600
    diffs = [
        (lambda xy: xy[0] - xy[1])(sample_scoreline(model, STRONG, WEAK, 0.0, rng))
        for _ in range(n)
    ]
    assert float(np.mean(diffs)) > 0.0
