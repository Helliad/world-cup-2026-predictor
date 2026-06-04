"""Tests for simulation/tournament.py (§6.4, §6.8).

Exercises the single-tournament reference implementation: groups -> best-thirds
-> 32-team bracket -> champion. Uses the real trained model and the real static
inputs (groups, fixtures, allocation) so the bracket structure under test is the
production one. All RNG is seeded via np.random.default_rng for determinism.
"""

from __future__ import annotations

import numpy as np
import pytest

import config
from model.dixon_coles import DixonColesModel
from simulation.knockout import KnockoutParams
from simulation.setup import load_sim_inputs
from simulation.tournament import (
    STAGE_CODE,
    STAGES,
    TournamentResult,
    play_bracket,
    simulate_tournament,
)


@pytest.fixture(scope="module")
def model() -> DixonColesModel:
    return DixonColesModel.load("model/params.json")


@pytest.fixture(scope="module")
def cfg() -> dict:
    return config.load_config()


@pytest.fixture(scope="module")
def sim_inputs(cfg: dict, model: DixonColesModel) -> dict:
    return load_sim_inputs(cfg, model)


@pytest.fixture(scope="module")
def params(cfg: dict) -> KnockoutParams:
    return KnockoutParams.from_config(cfg)


def _run(model, sim_inputs, params, seed: int) -> TournamentResult:
    rng = np.random.default_rng(seed)
    return simulate_tournament(
        model,
        sim_inputs["groups"],
        sim_inputs["fixtures_by_group"],
        sim_inputs["allocation"],
        params,
        rng,
    )


def _all_teams(sim_inputs) -> list[str]:
    return [t for teams in sim_inputs["groups"].values() for t in teams]


# --- Case 1: every one of the 48 teams has an entry in `reached`. ------------


def test_all_48_teams_have_reached_entry(model, sim_inputs, params):
    all_teams = _all_teams(sim_inputs)
    assert len(all_teams) == 48
    assert len(set(all_teams)) == 48  # sanity: distinct teams

    res = _run(model, sim_inputs, params, seed=1)

    assert isinstance(res, TournamentResult)
    # Exactly the 48 entrants are recorded, no more and no fewer.
    assert set(res.reached.keys()) == set(all_teams)
    assert len(res.reached) == 48
    # Every recorded stage is a valid ladder label.
    assert all(stage in STAGES for stage in res.reached.values())


# --- Case 2: exactly 32 teams reached >= 'r32' (made the knockout). ----------


def test_exactly_32_made_knockout(model, sim_inputs, params):
    res = _run(model, sim_inputs, params, seed=2)

    knockout = [t for t, s in res.reached.items() if STAGE_CODE[s] >= STAGE_CODE["r32"]]
    assert len(knockout) == 32

    # The complement: exactly 16 teams are eliminated in the group stage.
    group_only = [t for t, s in res.reached.items() if s == "group"]
    assert len(group_only) == 16
    # A team is either in the knockout or out at the group stage — nothing else.
    assert len(knockout) + len(group_only) == 48


# --- Case 3: exactly one champion (reached 'champion'). ----------------------


def test_exactly_one_champion(model, sim_inputs, params):
    res = _run(model, sim_inputs, params, seed=3)

    champions = [t for t, s in res.reached.items() if s == "champion"]
    assert champions == [res.champion]  # exactly one, and it is THE champion

    # The champion is a real entrant, and exactly one team reaches the final-win.
    assert res.champion in set(_all_teams(sim_inputs))
    assert sum(1 for s in res.reached.values() if s == "champion") == 1
    # Exactly one team reaches the final as a stage too (the beaten finalist),
    # so 'final' is the furthest stage for precisely one (losing) team.
    assert sum(1 for s in res.reached.values() if s == "final") == 1


def test_stage_funnel_counts(model, sim_inputs, params):
    """The furthest-stage histogram must follow the single-elimination funnel.

    32 enter the knockout; each round halves the survivors, so the count of
    teams *eliminated at* each stage (i.e. whose furthest stage is that label)
    is fixed: 16 at r32, 8 at r16, 4 at qf, 2 at sf, 1 at final, 1 champion.
    """
    res = _run(model, sim_inputs, params, seed=11)
    counts = dict.fromkeys(STAGES, 0)
    for stage in res.reached.values():
        counts[stage] += 1

    assert counts == {
        "group": 16,
        "r32": 16,
        "r16": 8,
        "qf": 4,
        "sf": 2,
        "final": 1,
        "champion": 1,
    }


# --- Case 4: play_bracket on a hand-built 16-match list halves each round. ---


def test_play_bracket_halves_field_each_round(model, params):
    """A clean 32-team bracket folds 16->8->4->2->1 to a single champion."""
    # 32 distinct real team names so the model can score every matchup.
    teams = list(model.team_index.keys())[:32]
    assert len(set(teams)) == 32
    r32_matches = [(teams[2 * i], teams[2 * i + 1]) for i in range(16)]
    assert len(r32_matches) == 16

    rng = np.random.default_rng(99)
    champion, reached = play_bracket(r32_matches, model, rng, params)

    # Single champion, and it is one of the 32 entrants.
    assert champion in teams

    # Every entrant gets a furthest-stage record; nobody outside the 32 appears.
    assert set(reached.keys()) == set(teams)
    assert len(reached) == 32

    # The funnel: counts of teams whose furthest stage is each label.
    counts = dict.fromkeys(STAGES, 0)
    for stage in reached.values():
        counts[stage] += 1
    # No team in a hand-built bracket is recorded at 'group'.
    assert counts["group"] == 0
    assert counts["r32"] == 16  # lost their first knockout match
    assert counts["r16"] == 8
    assert counts["qf"] == 4
    assert counts["sf"] == 2
    assert counts["final"] == 1
    assert counts["champion"] == 1
    # The champion's recorded stage agrees with the returned champion.
    assert reached[champion] == "champion"


def test_play_bracket_winners_subset_each_round(model, params):
    """Each round's survivors must be drawn from the previous round's competitors.

    We can't observe intermediate winner lists directly, but the furthest-stage
    ladder is monotone: a team recorded at stage S must be one of the original
    competitors, and exactly one team sits at every advanced stage label.
    """
    teams = list(model.team_index.keys())[:32]
    r32_matches = [(teams[2 * i], teams[2 * i + 1]) for i in range(16)]
    rng = np.random.default_rng(2024)
    champion, reached = play_bracket(r32_matches, model, rng, params)

    # The champion and beaten finalist are exactly two distinct teams.
    finalists = [t for t, s in reached.items() if STAGE_CODE[s] >= STAGE_CODE["final"]]
    assert len(finalists) == 2
    assert champion in finalists


# --- Case 5: determinism — same seed => identical champion and reached dict. -


def test_determinism_same_seed(model, sim_inputs, params):
    res_a = _run(model, sim_inputs, params, seed=4242)
    res_b = _run(model, sim_inputs, params, seed=4242)

    assert res_a.champion == res_b.champion
    assert res_a.reached == res_b.reached
    assert res_a.group_rank == res_b.group_rank


def test_different_seeds_can_differ(model, sim_inputs, params):
    """Sanity check that the RNG actually drives outcomes (not a constant)."""
    champs = {_run(model, sim_inputs, params, seed=s).champion for s in range(8)}
    # With 8 independent seeds we expect more than one distinct champion.
    assert len(champs) > 1


def test_play_bracket_determinism(model, params):
    teams = list(model.team_index.keys())[:32]
    r32 = [(teams[2 * i], teams[2 * i + 1]) for i in range(16)]

    champ1, reached1 = play_bracket(r32, model, np.random.default_rng(5), params)
    champ2, reached2 = play_bracket(r32, model, np.random.default_rng(5), params)
    assert champ1 == champ2
    assert reached1 == reached2


# --- Case 6: no team appears in two different R32 matchups in one bracket. ----


def test_no_team_in_two_r32_matchups(model, sim_inputs, params):
    """Reconstruct the bracket the way simulate_tournament does and assert that
    the 16 R32 matchups use 32 distinct teams (no team double-booked)."""
    rng = np.random.default_rng(777)

    # Mirror simulate_tournament's group + third-place resolution, then read the
    # R32 matchups it would build, to inspect the matchup list directly.
    from simulation.group_stage import simulate_group
    from simulation.third_place import select_best_thirds
    from simulation.tournament import _resolve_slot

    groups = sim_inputs["groups"]
    fixtures_by_group = sim_inputs["fixtures_by_group"]
    allocation = sim_inputs["allocation"]

    group_results = {
        letter: simulate_group(teams, model, rng, fixtures_by_group.get(letter))
        for letter, teams in groups.items()
    }
    winners = {g: r[0].team for g, r in group_results.items()}
    runners = {g: r[1].team for g, r in group_results.items()}
    thirds = [(g, r[2]) for g, r in group_results.items()]
    third_assignment = select_best_thirds(thirds, allocation, rng)

    r32: list[tuple[str, str]] = []
    for m in sorted(allocation["r32"], key=lambda x: x["match"]):
        top = _resolve_slot(m["top"], winners, runners)
        bottom = (
            third_assignment[m["match"]]
            if m["bottom"] == "3RD"
            else _resolve_slot(m["bottom"], winners, runners)
        )
        r32.append((top, bottom))

    assert len(r32) == 16
    flat = [t for pair in r32 for t in pair]
    assert len(flat) == 32
    # The load-bearing assertion: every R32 participant is unique.
    assert len(set(flat)) == 32, "a team appears in two R32 matchups"
    # No matchup pits a team against itself.
    assert all(a != b for a, b in r32)


def test_simulated_bracket_has_distinct_knockout_teams(model, sim_inputs, params):
    """End-to-end: the 32 teams recorded at >= r32 are exactly distinct, which
    can only hold if the R32 field had no duplicates."""
    res = _run(model, sim_inputs, params, seed=314)
    knockout = [t for t, s in res.reached.items() if STAGE_CODE[s] >= STAGE_CODE["r32"]]
    assert len(knockout) == len(set(knockout)) == 32
