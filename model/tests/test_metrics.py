"""Tests for model/evaluation/metrics.py (§4.6 proper scoring rules).

Outcome convention: 0=home win, 1=draw, 2=away win.
Lower is better for RPS / Brier / log-loss; higher better for accuracy.
"""

from __future__ import annotations

import numpy as np
import pytest

from model.evaluation.metrics import (
    AWAY,
    DRAW,
    HOME,
    all_metrics,
    brier_score,
    expected_calibration_error,
    log_loss,
    ranked_probability_score,
    reliability_table,
    top_pick_accuracy,
)


# --------------------------------------------------------------------------- #
# Case 1: perfect deterministic prediction
# --------------------------------------------------------------------------- #
def test_perfect_prediction_scores_zero_and_accuracy_one():
    # One match per outcome, each predicted with certainty.
    probs = np.array(
        [
            [1.0, 0.0, 0.0],  # home, realised home
            [0.0, 1.0, 0.0],  # draw, realised draw
            [0.0, 0.0, 1.0],  # away, realised away
        ]
    )
    outcomes = np.array([HOME, DRAW, AWAY])

    assert ranked_probability_score(probs, outcomes) == pytest.approx(0.0, abs=1e-12)
    assert brier_score(probs, outcomes) == pytest.approx(0.0, abs=1e-12)
    # log_loss clips at _EPS=1e-15, so -log(1)=0 exactly here.
    assert log_loss(probs, outcomes) == pytest.approx(0.0, abs=1e-9)
    assert top_pick_accuracy(probs, outcomes) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# Case 2: uniform prediction => known RPS = 5/18 for a single decided outcome
# --------------------------------------------------------------------------- #
def test_uniform_prediction_known_rps_home():
    # Uniform (1/3,1/3,1/3): cumulative pred (1/3,2/3), actual cumulative (1,1).
    # RPS = ((1/3-1)^2 + (2/3-1)^2)/2 = (4/9 + 1/9)/2 = 5/18.
    probs = np.array([[1 / 3, 1 / 3, 1 / 3]])
    outcomes = np.array([HOME])
    assert ranked_probability_score(probs, outcomes) == pytest.approx(5 / 18)


def test_uniform_prediction_rps_away_equals_home_by_symmetry():
    # For AWAY: cumulative pred (1/3,2/3), actual cumulative (0,0).
    # RPS = (1/9 + 4/9)/2 = 5/18. Symmetric with the home case.
    probs = np.array([[1 / 3, 1 / 3, 1 / 3]])
    assert ranked_probability_score(probs, np.array([AWAY])) == pytest.approx(5 / 18)


def test_uniform_prediction_rps_draw_is_smallest():
    # For DRAW: cumulative pred (1/3,2/3), actual cumulative (0,1).
    # RPS = ((1/3-0)^2 + (2/3-1)^2)/2 = (1/9 + 1/9)/2 = 1/9.
    probs = np.array([[1 / 3, 1 / 3, 1 / 3]])
    rps_draw = ranked_probability_score(probs, np.array([DRAW]))
    rps_home = ranked_probability_score(probs, np.array([HOME]))
    assert rps_draw == pytest.approx(1 / 9)
    # The middle outcome is "easier" under RPS than the extremes.
    assert rps_draw < rps_home


def test_uniform_prediction_other_metrics_known_values():
    probs = np.array([[1 / 3, 1 / 3, 1 / 3]])
    outcomes = np.array([HOME])
    # Brier = (1/3-1)^2 + (1/3)^2 + (1/3)^2 = 4/9 + 1/9 + 1/9 = 6/9 = 2/3.
    assert brier_score(probs, outcomes) == pytest.approx(2 / 3)
    # log_loss = -log(1/3) = log(3).
    assert log_loss(probs, outcomes) == pytest.approx(np.log(3.0))


# --------------------------------------------------------------------------- #
# Case 3: RPS distance-sensitivity
# --------------------------------------------------------------------------- #
def test_rps_distance_sensitivity_home_heavy_pred():
    # A home-heavy prediction. When the truth is AWAY (far, distance 2) it must
    # be penalised MORE than when the truth is DRAW (near, distance 1).
    probs = np.array([[0.7, 0.2, 0.1]])
    rps_away = ranked_probability_score(probs, np.array([AWAY]))
    rps_draw = ranked_probability_score(probs, np.array([DRAW]))
    rps_home = ranked_probability_score(probs, np.array([HOME]))

    assert rps_away > rps_draw > rps_home

    # Brier, being non-ordinal, treats draw and away misses identically here
    # only if the off-class mass is symmetric — verify RPS is the one encoding
    # ordinal distance by an explicit hand-check.
    # AWAY: cum pred (0.7,0.9), actual (0,0): (0.49 + 0.81)/2 = 0.65.
    assert rps_away == pytest.approx((0.7**2 + 0.9**2) / 2.0)
    # DRAW: cum pred (0.7,0.9), actual (0,1): (0.49 + 0.01)/2 = 0.25.
    assert rps_draw == pytest.approx((0.7**2 + (0.9 - 1) ** 2) / 2.0)


def test_rps_penalises_confident_wrong_more_than_unsure():
    # Same (away) outcome: a confident-home prediction must score worse than
    # a hedged uniform one.
    confident = np.array([[0.8, 0.15, 0.05]])
    hedged = np.array([[1 / 3, 1 / 3, 1 / 3]])
    out = np.array([AWAY])
    assert ranked_probability_score(confident, out) > ranked_probability_score(hedged, out)


# --------------------------------------------------------------------------- #
# Case 4: calibration — probabilities matching base rates => small ECE
# --------------------------------------------------------------------------- #
def test_well_calibrated_predictions_have_small_ece():
    rng = np.random.default_rng(20260604)
    n = 1200
    # True (and predicted) class probabilities; data generated FROM them, so the
    # forecaster is perfectly calibrated in expectation.
    true_p = np.array([0.5, 0.3, 0.2])
    probs = np.tile(true_p, (n, 1))
    outcomes = rng.choice(3, size=n, p=true_p)

    ece = expected_calibration_error(probs, outcomes, n_bins=10)
    # All confidences land in the same bin (max prob = 0.5), so ECE reduces to
    # |accuracy - 0.5|. Accuracy ~ P(argmax correct) = P(home) = 0.5; the residual
    # is pure finite-sample noise (SE of accuracy at n=1200, p=0.5 is ~0.014).
    assert ece < 0.07
    # A perfectly-calibrated forecaster is far below a grossly overconfident one.
    bad = np.tile(np.array([0.95, 0.03, 0.02]), (n, 1))
    assert ece < expected_calibration_error(bad, outcomes, n_bins=10)


def test_miscalibrated_overconfident_has_larger_ece():
    rng = np.random.default_rng(7)
    n = 1000
    # Forecaster claims 0.95 confidence on home but home only happens ~50%.
    probs = np.tile(np.array([0.95, 0.03, 0.02]), (n, 1))
    outcomes = rng.choice(3, size=n, p=[0.5, 0.3, 0.2])

    ece_bad = expected_calibration_error(probs, outcomes, n_bins=10)
    # Confidence ~0.95 but accuracy ~0.5 => ECE near 0.45.
    assert ece_bad > 0.3

    # And it should be worse than a calibrated forecaster on the same data.
    calib = np.tile(np.array([0.5, 0.3, 0.2]), (n, 1))
    assert ece_bad > expected_calibration_error(calib, outcomes, n_bins=10)


def test_ece_zero_for_perfect_predictions():
    probs = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]])
    outcomes = np.array([HOME, AWAY, DRAW])
    # Confidence 1.0, accuracy 1.0 in the top bin => ECE 0.
    assert expected_calibration_error(probs, outcomes) == pytest.approx(0.0)


# --------------------------------------------------------------------------- #
# reliability_table
# --------------------------------------------------------------------------- #
def test_reliability_table_structure_and_values():
    # Two predicted-prob buckets for the HOME class.
    probs = np.array(
        [
            [0.1, 0.5, 0.4],  # low home prob, outcome NOT home
            [0.15, 0.45, 0.4],  # low home prob, outcome NOT home
            [0.85, 0.1, 0.05],  # high home prob, outcome home
            [0.9, 0.05, 0.05],  # high home prob, outcome home
        ]
    )
    outcomes = np.array([AWAY, DRAW, HOME, HOME])
    table = reliability_table(probs, outcomes, class_idx=HOME, n_bins=10)

    assert set(table.keys()) == {"predicted", "observed", "count"}
    # The three parallel lists must have equal length (one entry per non-empty bin).
    assert len(table["predicted"]) == len(table["observed"]) == len(table["count"])
    assert sum(table["count"]) == 4  # every match accounted for exactly once
    # Low bucket (~0.1-0.15) observed 0 homes; high bucket (~0.85-0.9) observed all homes.
    assert 0.0 in table["observed"]
    assert 1.0 in table["observed"]
    # Predicted means should bracket the observed transition.
    assert min(table["predicted"]) < 0.5 < max(table["predicted"])


def test_reliability_table_perfectly_calibrated_diagonal():
    rng = np.random.default_rng(11)
    n = 4000
    # Predicted home prob varies; generate the home indicator from it => the
    # observed frequency in each bucket should track the predicted mean.
    home_p = rng.uniform(0.0, 1.0, size=n)
    rest = (1.0 - home_p) / 2.0
    probs = np.stack([home_p, rest, rest], axis=1)
    is_home = rng.uniform(size=n) < home_p
    # Build outcomes: home where is_home, else split remainder draw/away.
    outcomes = np.where(is_home, HOME, rng.choice([DRAW, AWAY], size=n))

    table = reliability_table(probs, outcomes, class_idx=HOME, n_bins=10)
    pred = np.array(table["predicted"])
    obs = np.array(table["observed"])
    # Each well-populated bin's observed freq should be near its predicted mean.
    assert np.max(np.abs(pred - obs)) < 0.1


# --------------------------------------------------------------------------- #
# all_metrics: documented keys + consistency with individual functions
# --------------------------------------------------------------------------- #
def test_all_metrics_keys_and_consistency():
    rng = np.random.default_rng(2026)
    n = 50
    raw = rng.uniform(0.05, 1.0, size=(n, 3))
    probs = raw / raw.sum(axis=1, keepdims=True)
    outcomes = rng.integers(0, 3, size=n)

    m = all_metrics(probs, outcomes)
    assert set(m.keys()) == {"rps", "brier", "log_loss", "accuracy", "ece", "n"}

    assert m["rps"] == pytest.approx(ranked_probability_score(probs, outcomes))
    assert m["brier"] == pytest.approx(brier_score(probs, outcomes))
    assert m["log_loss"] == pytest.approx(log_loss(probs, outcomes))
    assert m["accuracy"] == pytest.approx(top_pick_accuracy(probs, outcomes))
    assert m["ece"] == pytest.approx(expected_calibration_error(probs, outcomes))
    assert m["n"] == n
    assert isinstance(m["n"], int)


def test_metric_ranges_are_respected():
    rng = np.random.default_rng(99)
    n = 200
    raw = rng.uniform(0.05, 1.0, size=(n, 3))
    probs = raw / raw.sum(axis=1, keepdims=True)
    outcomes = rng.integers(0, 3, size=n)
    m = all_metrics(probs, outcomes)

    # RPS in [0,1] for r=3 normalisation; Brier in [0,2]; accuracy & ECE in [0,1].
    assert 0.0 <= m["rps"] <= 1.0
    assert 0.0 <= m["brier"] <= 2.0
    assert 0.0 <= m["accuracy"] <= 1.0
    assert 0.0 <= m["ece"] <= 1.0
    assert m["log_loss"] >= 0.0


def test_outcome_constants_match_convention():
    assert (HOME, DRAW, AWAY) == (0, 1, 2)
