"""Tests for the vectorised Monte Carlo (`simulation/monte_carlo.py`, §6.6/§6.8).

These encode the spec's "probability sanity" rules for the aggregate run:
frequencies that must sum to 1 (champion) and to 32 (advancing), per-team stage
monotonicity, the published Monte Carlo standard error, the compact what-if
sample's shape/dtype/encoding contract, and a cross-check that the vectorised MC
agrees with the readable single-tournament reference path (`simulate_tournament`)
to within Monte Carlo error.

Everything is deterministic (all RNG seeded) and kept fast: one shared MC run at
N=1200 plus ~1500 single tournaments for the reference tally.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from config import load_config
from model.dixon_coles import DixonColesModel
from simulation.knockout import KnockoutParams
from simulation.monte_carlo import SimResults, run_simulations
from simulation.setup import load_sim_inputs
from simulation.tournament import simulate_tournament

# Keep runs modest so the suite stays fast but the frequencies stay meaningful.
N_SIMS = 1200
MC_SEED = 20260604
WHATIF_K = 64
REF_TOURNAMENTS = 1500
REF_SEED = 7777


@pytest.fixture(scope="module")
def model() -> DixonColesModel:
    return DixonColesModel.load("model/params.json")


@pytest.fixture(scope="module")
def sim_inputs(model: DixonColesModel) -> dict:
    cfg = load_config()
    return load_sim_inputs(cfg, model)


@pytest.fixture(scope="module")
def params() -> KnockoutParams:
    return KnockoutParams.from_config(load_config())


@pytest.fixture(scope="module")
def results(model, sim_inputs, params) -> SimResults:
    """A single shared Monte Carlo run reused by every test in this module."""
    return run_simulations(
        model,
        sim_inputs,
        params,
        n=N_SIMS,
        seed=MC_SEED,
        whatif_sample_size=WHATIF_K,
        verbose=False,
    )


# --------------------------------------------------------------------------- #
# Basic structure
# --------------------------------------------------------------------------- #


def test_covers_48_teams(results: SimResults) -> None:
    assert len(results.teams) == 48
    assert results.n == N_SIMS
    assert results.seed == MC_SEED
    # every per-team probability array is aligned with the team list
    for arr in (
        results.p_advance,
        results.p_r16,
        results.p_qf,
        results.p_sf,
        results.p_final,
        results.p_win,
        results.se_win,
    ):
        assert arr.shape == (48,)


# --------------------------------------------------------------------------- #
# (1) Champion probabilities are a frequency over exactly one champion per sim.
# --------------------------------------------------------------------------- #


def test_p_win_sums_to_one(results: SimResults) -> None:
    # Exactly one champion per simulation, so the win frequencies partition the
    # sims and sum to 1 (a frequency, so the tolerance is at float-noise level).
    assert results.p_win.sum() == pytest.approx(1.0, abs=1e-9)
    assert np.all(results.p_win >= 0.0)
    assert np.all(results.p_win <= 1.0)


# --------------------------------------------------------------------------- #
# (2) Exactly 32 teams advance in every simulation.
# --------------------------------------------------------------------------- #


def test_p_advance_sums_to_32(results: SimResults) -> None:
    # 12 group winners + 12 runners-up + 8 best thirds = 32 advancing every sim,
    # so the sum of advance frequencies is exactly 32.
    assert results.p_advance.sum() == pytest.approx(32.0, abs=1e-9)
    assert np.all(results.p_advance >= 0.0)
    assert np.all(results.p_advance <= 1.0)


def test_p_r16_sums_to_16(results: SimResults) -> None:
    # The Round of 32 produces 16 Round-of-16 teams every simulation.
    assert results.p_r16.sum() == pytest.approx(16.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# (3) Per-team stage monotonicity: advancing further is strictly nested.
# --------------------------------------------------------------------------- #


def test_stage_probabilities_monotone_per_team(results: SimResults) -> None:
    slack = 1e-12  # these come from nested boolean masks, so equality is exact
    assert np.all(results.p_advance >= results.p_r16 - slack)
    assert np.all(results.p_r16 >= results.p_qf - slack)
    assert np.all(results.p_qf >= results.p_sf - slack)
    assert np.all(results.p_sf >= results.p_final - slack)
    assert np.all(results.p_final >= results.p_win - slack)


# --------------------------------------------------------------------------- #
# (4) Published Monte Carlo standard error matches sqrt(p(1-p)/N).
# --------------------------------------------------------------------------- #


def test_se_win_matches_binomial_formula(results: SimResults) -> None:
    expected = np.sqrt(results.p_win * (1.0 - results.p_win) / N_SIMS)
    assert np.allclose(results.se_win, expected, atol=1e-12, rtol=0.0)
    assert np.all(results.se_win >= 0.0)


# --------------------------------------------------------------------------- #
# (5) The compact "what if" sample: shapes, dtypes, and value encodings.
# --------------------------------------------------------------------------- #


def test_whatif_arrays_shape_and_dtype(results: SimResults) -> None:
    assert results.whatif_stage.shape == (WHATIF_K, 48)
    assert results.whatif_slots.shape == (WHATIF_K, 32)
    assert results.whatif_group_rank.shape == (WHATIF_K, 48)
    assert results.whatif_stage.dtype == np.uint8
    assert results.whatif_slots.dtype == np.uint8
    assert results.whatif_group_rank.dtype == np.uint8


def test_whatif_stage_codes_in_range(results: SimResults) -> None:
    # Furthest-stage codes: 0 (group exit) .. 6 (champion).
    assert results.whatif_stage.min() >= 0
    assert results.whatif_stage.max() <= 6
    # Each what-if sim has exactly one champion (stage code 6) among the 48 teams.
    champions_per_sim = (results.whatif_stage == 6).sum(axis=1)
    assert np.all(champions_per_sim == 1)
    # ...and exactly 32 teams that reached at least the Round of 32 (code >= 1).
    advanced_per_sim = (results.whatif_stage >= 1).sum(axis=1)
    assert np.all(advanced_per_sim == 32)


def test_whatif_slots_encode_valid_distinct_teams(results: SimResults) -> None:
    # Each of the 32 bracket slots holds a valid team index (0..47), and the 32
    # slots in a single sim are 32 distinct teams (the knockout field).
    assert results.whatif_slots.min() >= 0
    assert results.whatif_slots.max() <= 47
    for row in results.whatif_slots:
        assert len(np.unique(row)) == 32


def test_whatif_group_rank_in_one_to_four(results: SimResults) -> None:
    # Group finish position is 1..4 for every team in every sampled sim.
    assert results.whatif_group_rank.min() >= 1
    assert results.whatif_group_rank.max() <= 4


# --------------------------------------------------------------------------- #
# Determinism: a fixed seed reproduces the run bit-for-bit.
# --------------------------------------------------------------------------- #


def test_run_is_deterministic(model, sim_inputs, params, results: SimResults) -> None:
    again = run_simulations(
        model,
        sim_inputs,
        params,
        n=N_SIMS,
        seed=MC_SEED,
        whatif_sample_size=WHATIF_K,
        verbose=False,
    )
    assert np.array_equal(again.p_win, results.p_win)
    assert np.array_equal(again.p_advance, results.p_advance)
    assert np.array_equal(again.whatif_slots, results.whatif_slots)
    assert np.array_equal(again.whatif_stage, results.whatif_stage)


# --------------------------------------------------------------------------- #
# (6) Cross-check the vectorised MC against the readable reference path.
# --------------------------------------------------------------------------- #


def test_top_team_matches_reference_frequency(
    model, sim_inputs, params, results: SimResults
) -> None:
    """The MC's most-likely champion should win at a rate consistent (within ~4
    combined standard errors) with an independent tally from the single-tournament
    reference implementation (`simulate_tournament`)."""
    ti = int(np.argmax(results.p_win))
    top_team = results.teams[ti]
    p_mc = float(results.p_win[ti])
    se_mc = float(results.se_win[ti])

    groups = sim_inputs["groups"]
    fixtures_by_group = sim_inputs["fixtures_by_group"]
    allocation = sim_inputs["allocation"]

    # Distinct, deterministic seeds for each independent reference tournament.
    seeds = np.random.SeedSequence(REF_SEED).generate_state(REF_TOURNAMENTS)
    champions: Counter[str] = Counter()
    for s in seeds:
        rng = np.random.default_rng(int(s))
        tr = simulate_tournament(model, groups, fixtures_by_group, allocation, params, rng)
        champions[tr.champion] += 1

    # Sanity on the reference tally itself: one champion per tournament.
    assert sum(champions.values()) == REF_TOURNAMENTS

    p_ref = champions[top_team] / REF_TOURNAMENTS
    se_ref = float(np.sqrt(p_ref * (1.0 - p_ref) / REF_TOURNAMENTS))
    se_combined = float(np.sqrt(se_mc**2 + se_ref**2))

    # The top team should be a genuine contender in the reference run too, not a
    # vanishingly rare champion — guards against the two paths diverging wildly.
    assert p_ref > 0.02, (
        f"reference almost never crowns the MC favourite {top_team!r} "
        f"(p_ref={p_ref:.4f}), suggesting the two paths disagree"
    )

    z = abs(p_mc - p_ref) / se_combined
    assert z <= 4.0, (
        f"MC vs reference champion frequency for {top_team!r} disagree: "
        f"p_mc={p_mc:.4f}, p_ref={p_ref:.4f}, combined_se={se_combined:.4f}, z={z:.2f}"
    )


# --------------------------------------------------------------------------- #
# Pinned actual results re-condition the run (live-tracking feature).
# --------------------------------------------------------------------------- #


def _run(model, sim_inputs, params, **pins) -> SimResults:
    si = {**sim_inputs, "pinned_group": {}, "pinned_ko": [], **pins}
    return run_simulations(
        model, si, params, n=N_SIMS, seed=MC_SEED, whatif_sample_size=WHATIF_K, verbose=False
    )


def test_pinned_group_result_reconditions_advancement(model, sim_inputs, params) -> None:
    """Pinning a lopsided group scoreline lifts the winner's P(advance) and drops
    the loser's, relative to the unpinned forecast."""
    base = _run(model, sim_inputs, params)
    ti = {t: i for i, t in enumerate(base.teams)}
    # Fixture orientation in groups.json is home=Mexico, away=South Africa.
    pinned = _run(model, sim_inputs, params, pinned_group={("Mexico", "South Africa"): (0, 5)})
    assert pinned.p_advance[ti["South Africa"]] > base.p_advance[ti["South Africa"]] + 0.05
    assert pinned.p_advance[ti["Mexico"]] < base.p_advance[ti["Mexico"]]


def test_pinned_knockout_loss_drops_title_odds(model, sim_inputs, params) -> None:
    """Forcing the favourite to lose any knockout meeting with a set of opponents
    can only reduce (never raise) its championship probability."""
    base = _run(model, sim_inputs, params)
    ti = {t: i for i, t in enumerate(base.teams)}
    fav = base.teams[int(np.argmax(base.p_win))]
    koed = _run(model, sim_inputs, params, pinned_ko=[("Panama", fav), ("Jordan", fav)])
    assert koed.p_win[ti[fav]] <= base.p_win[ti[fav]]


def test_empty_pins_match_default_run(model, sim_inputs, params, results: SimResults) -> None:
    """Explicit empty pins reproduce the default run bit-for-bit (no RNG drift)."""
    explicit = _run(model, sim_inputs, params)
    assert np.array_equal(explicit.p_win, results.p_win)
    assert np.array_equal(explicit.p_advance, results.p_advance)
