"""Tests for best-third selection and bracket allocation (§2.2, §6.2).

Exercises ``simulation/third_place.py`` — the module the spec flags as the place
"where most simulator bugs live". We build fully-determined synthetic
third-place records (distinct primary keys so the drawing-of-lots never enters)
and assert the documented rules:

  1. exactly the 8 best thirds advance (the 4 worst are dropped);
  2. the 8 survivors fill all 8 winner-vs-third slots, one distinct team each;
  3. same-group avoidance: a third is not slotted against its own group's winner
     when a valid alternative exists;
  4. ``rank_thirds`` orders by points → GD → GF (then lots).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from simulation.group_stage import TeamResult
from simulation.third_place import (
    rank_thirds,
    select_best_thirds,
    third_slot_groups,
)

ALL_GROUPS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]


@pytest.fixture(scope="module")
def allocation() -> dict:
    path = Path(__file__).resolve().parents[2] / "data" / "third_place_allocation.json"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _third(group: str, points: int, gf: int, ga: int) -> tuple[str, TeamResult]:
    """A (group_letter, TeamResult) third-place record with team name 'T<group>'."""
    return group, TeamResult(team=f"T{group}", rank=3, points=points, gf=gf, ga=ga)


# --------------------------------------------------------------------------- #
# The allocation file / slot layout itself                                    #
# --------------------------------------------------------------------------- #


def test_eight_third_slots_with_expected_winner_groups(allocation: dict) -> None:
    """There are exactly 8 winner-vs-third slots. With the official FIFA bracket
    stored in fold order, the third slots sit at list entries 1,2,7,8,11,12,15,16
    and face winner groups E,I,D,G,A,L,B,K respectively."""
    slots = third_slot_groups(allocation)
    assert len(slots) == 8
    assert [m for m, _ in slots] == [1, 2, 7, 8, 11, 12, 15, 16]
    assert [g for _, g in slots] == ["E", "I", "D", "G", "A", "L", "B", "K"]
    # The slot winner-groups are exactly the documented winners_facing_thirds set.
    assert {g for _, g in slots} == set(allocation["winners_facing_thirds"])


def test_official_table_matches_realized_2026_draw(allocation: dict) -> None:
    """The encoded Annex C row for the realized 2026 combination (third-place
    groups B,D,E,F,I,J,K,L) must reproduce the official Round-of-32 third-place
    matchups: each winner group faces the third of the documented source group."""
    # Third-placed team of each qualifying group (distinct keys -> no lots needed).
    realized = ["B", "D", "E", "F", "I", "J", "K", "L"]
    thirds = [_third(g, points=8 - i, gf=10, ga=0) for i, g in enumerate(realized)]
    # Plus four clearly-worst non-qualifying thirds.
    thirds += [_third(g, points=0, gf=0, ga=0) for g in ["A", "C", "G", "H"]]

    assignment = select_best_thirds(thirds, allocation, np.random.default_rng(0))
    slot_wg = dict(third_slot_groups(allocation))  # match_no -> winner group
    by_winner = {slot_wg[mn]: team for mn, team in assignment.items()}

    # Official Annex C allocation for combination BDEFIJKL.
    assert by_winner == {
        "A": "TE",  # Mexico   vs 3rd E (Ecuador)
        "B": "TJ",  # Switzerland vs 3rd J (Algeria)
        "D": "TB",  # USA      vs 3rd B (Bosnia)
        "E": "TD",  # Germany  vs 3rd D (Paraguay)
        "G": "TI",  # Belgium  vs 3rd I (Senegal)
        "I": "TF",  # France   vs 3rd F (Sweden)
        "K": "TL",  # Colombia vs 3rd L (Ghana)
        "L": "TK",  # England  vs 3rd K (DR Congo)
    }


# --------------------------------------------------------------------------- #
# (1) Exactly the 8 best advance; 4 worst dropped                             #
# --------------------------------------------------------------------------- #


def test_exactly_eight_best_advance_four_worst_dropped(allocation: dict) -> None:
    """With 12 unambiguously-ranked thirds, only the top 8 by points get slotted
    and the 4 lowest-scoring thirds are eliminated."""
    # Distinct points 12..1 -> ranking is unambiguous (no lots needed).
    thirds = [_third(g, points=12 - i, gf=20, ga=0) for i, g in enumerate(ALL_GROUPS)]
    rng = np.random.default_rng(2026)

    assignment = select_best_thirds(thirds, allocation, rng)

    assert len(assignment) == 8
    advanced = set(assignment.values())
    # Top-8 groups A..H -> teams TA..TH advance; bottom-4 I..L are dropped.
    assert advanced == {f"T{g}" for g in ["A", "B", "C", "D", "E", "F", "G", "H"]}
    dropped = {f"T{g}" for g in ["I", "J", "K", "L"]}
    assert advanced.isdisjoint(dropped)


def test_drop_set_follows_full_ranking_not_just_points(allocation: dict) -> None:
    """When points are tied across all thirds, GD then GF decides who survives:
    the four worst on (points, GD, GF) are the ones eliminated."""
    # All level on points; GF strictly decreasing A..L while GA fixed -> GD/GF
    # both strictly decreasing, so the four worst are exactly I, J, K, L.
    thirds = [_third(g, points=4, gf=30 - i, ga=0) for i, g in enumerate(ALL_GROUPS)]
    rng = np.random.default_rng(11)

    assignment = select_best_thirds(thirds, allocation, rng)

    advanced = set(assignment.values())
    assert advanced == {f"T{g}" for g in ["A", "B", "C", "D", "E", "F", "G", "H"]}
    assert advanced.isdisjoint({f"T{g}" for g in ["I", "J", "K", "L"]})


# --------------------------------------------------------------------------- #
# (2) Assignment fills all 8 slots with 8 distinct teams                      #
# --------------------------------------------------------------------------- #


def test_assignment_maps_all_eight_slots_distinct_teams(allocation: dict) -> None:
    thirds = [_third(g, points=12 - i, gf=20, ga=0) for i, g in enumerate(ALL_GROUPS)]
    rng = np.random.default_rng(7)

    assignment = select_best_thirds(thirds, allocation, rng)

    expected_slots = {m for m, _ in third_slot_groups(allocation)}
    # Every third-slot match number is filled exactly once...
    assert set(assignment.keys()) == expected_slots
    # ...and no team is reused across slots.
    assert len(set(assignment.values())) == 8


def test_assignment_only_uses_advancing_teams(allocation: dict) -> None:
    """No slot may be filled by one of the four eliminated thirds."""
    thirds = [_third(g, points=12 - i, gf=20, ga=0) for i, g in enumerate(ALL_GROUPS)]
    rng = np.random.default_rng(3)

    assignment = select_best_thirds(thirds, allocation, rng)

    eliminated = {f"T{g}" for g in ["I", "J", "K", "L"]}
    assert set(assignment.values()).isdisjoint(eliminated)


def test_select_best_thirds_is_deterministic_for_fixed_seed(allocation: dict) -> None:
    thirds = [_third(g, points=12 - i, gf=20, ga=0) for i, g in enumerate(ALL_GROUPS)]

    a = select_best_thirds(thirds, allocation, np.random.default_rng(99))
    b = select_best_thirds(thirds, allocation, np.random.default_rng(99))
    assert a == b


# --------------------------------------------------------------------------- #
# (3) Same-group avoidance                                                    #
# --------------------------------------------------------------------------- #


def test_no_third_assigned_to_its_own_groups_winner(allocation: dict) -> None:
    """When the 8 surviving thirds come from the very winner-groups that own the
    third-slots, the fallback must route each third away from the slot whose
    winner is from its own group.

    The slot winner-groups (in processing order) are A, E, B, G, C, F, D, H. We
    feed thirds from exactly those eight groups but order the points so the
    greedy avoidance never paints itself into a corner (group H ranked above
    group G), so a fully same-group-free assignment exists and must be found.
    """
    slots = third_slot_groups(allocation)
    team_group = {f"T{g}": g for g in ALL_GROUPS}

    # Advancing groups (all eight winner-groups), ordered best -> worst by points.
    advancing = ["A", "B", "C", "D", "E", "F", "H", "G"]
    thirds: list[tuple[str, TeamResult]] = []
    for i, g in enumerate(advancing):
        thirds.append(_third(g, points=20 - i, gf=20 - i, ga=0))
    # Four clearly-worst thirds from the non-winner groups get dropped.
    for g in ["I", "J", "K", "L"]:
        thirds.append(_third(g, points=0, gf=0, ga=0))

    assignment = select_best_thirds(thirds, allocation, np.random.default_rng(5))

    # Every survivor came from a winner-group, so this is a genuine test of the
    # avoidance rule rather than a vacuous one.
    assert set(assignment.values()) == {f"T{g}" for g in advancing}
    for match_no, winner_group in slots:
        assigned_team = assignment[match_no]
        assert team_group[assigned_team] != winner_group, (
            f"slot {match_no} (winner group {winner_group}) was given "
            f"{assigned_team} from its own group {winner_group}"
        )


def test_avoidance_holds_for_corner_painting_order(allocation: dict) -> None:
    """Regression: a naive single-pass greedy paints itself into a corner when
    the 8 survivors are ranked A,B,C,D,E,F,G,H — it is forced to seat group H's
    third against the group-H winner at the last slot. The backtracking matcher
    must still find the conflict-free assignment that provably exists."""
    slots = third_slot_groups(allocation)
    team_group = {f"T{g}": g for g in ALL_GROUPS}
    advancing = ["A", "B", "C", "D", "E", "F", "G", "H"]  # rank == alphabetical
    thirds = [_third(g, points=20 - i, gf=20 - i, ga=0) for i, g in enumerate(advancing)]
    thirds += [_third(g, points=0, gf=0, ga=0) for g in ["I", "J", "K", "L"]]

    assignment = select_best_thirds(thirds, allocation, np.random.default_rng(1))

    assert set(assignment.values()) == {f"T{g}" for g in advancing}
    for match_no, winner_group in slots:
        assert team_group[assignment[match_no]] != winner_group, (
            f"slot {match_no} (winner group {winner_group}) got a same-group third"
        )


def test_avoidance_holds_across_multiple_seeds(allocation: dict) -> None:
    """Avoidance is structural (driven by distinct points), so it must hold for
    every seed, not just one lucky draw."""
    slots = third_slot_groups(allocation)
    team_group = {f"T{g}": g for g in ALL_GROUPS}
    advancing = ["A", "B", "C", "D", "E", "F", "H", "G"]

    def build() -> list[tuple[str, TeamResult]]:
        out = [_third(g, points=20 - i, gf=20 - i, ga=0) for i, g in enumerate(advancing)]
        out += [_third(g, points=0, gf=0, ga=0) for g in ["I", "J", "K", "L"]]
        return out

    for seed in (0, 1, 13, 404, 2026):
        assignment = select_best_thirds(build(), allocation, np.random.default_rng(seed))
        for match_no, winner_group in slots:
            assert team_group[assignment[match_no]] != winner_group


# --------------------------------------------------------------------------- #
# (4) rank_thirds ordering: points -> GD -> GF -> lots                         #
# --------------------------------------------------------------------------- #


def test_rank_thirds_orders_by_points_then_gd_then_gf() -> None:
    # T1: best on points. T2/T3 tie on points but T2 has better GD. T3/T4 tie on
    # points+GD but T3 has more GF. T5: worst on points despite huge GF.
    t1 = ("A", TeamResult(team="T1", rank=3, points=7, gf=5, ga=0))  # GD +5
    t2 = ("B", TeamResult(team="T2", rank=3, points=4, gf=6, ga=2))  # GD +4
    t3 = ("C", TeamResult(team="T3", rank=3, points=4, gf=9, ga=6))  # GD +3, GF 9
    t4 = ("D", TeamResult(team="T4", rank=3, points=4, gf=8, ga=5))  # GD +3, GF 8
    t5 = ("E", TeamResult(team="T5", rank=3, points=1, gf=99, ga=0))  # low points
    thirds = [t3, t5, t1, t4, t2]  # deliberately scrambled input order

    # Distinct lots; with distinct primary keys they should not affect order.
    lots = {"A": 0.1, "B": 0.2, "C": 0.3, "D": 0.4, "E": 0.5}
    ranked = rank_thirds(thirds, lots)

    assert [gt[1].team for gt in ranked] == ["T1", "T2", "T3", "T4", "T5"]


def test_rank_thirds_uses_lots_only_to_break_full_ties() -> None:
    """Two thirds identical on points, GD and GF are separated solely by lots
    (higher lot ranks first, since the sort is reverse=True)."""
    a = ("A", TeamResult(team="TA", rank=3, points=4, gf=3, ga=1))
    b = ("B", TeamResult(team="TB", rank=3, points=4, gf=3, ga=1))

    # B has the larger lot -> B should rank ahead of A.
    ranked = rank_thirds([a, b], {"A": 0.10, "B": 0.90})
    assert [gt[1].team for gt in ranked] == ["TB", "TA"]

    # Flip the lots -> the order flips, proving lots is the deciding key.
    ranked2 = rank_thirds([a, b], {"A": 0.90, "B": 0.10})
    assert [gt[1].team for gt in ranked2] == ["TA", "TB"]


def test_rank_thirds_returns_all_twelve_without_loss() -> None:
    thirds = [_third(g, points=12 - i, gf=20, ga=0) for i, g in enumerate(ALL_GROUPS)]
    lots = dict.fromkeys(ALL_GROUPS, 0.5)
    ranked = rank_thirds(thirds, lots)
    assert len(ranked) == 12
    assert {gt[0] for gt in ranked} == set(ALL_GROUPS)
    # Strictly decreasing points -> ranking equals the input group order A..L.
    assert [gt[0] for gt in ranked] == ALL_GROUPS
