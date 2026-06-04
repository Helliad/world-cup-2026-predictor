"""Tiebreaker-cascade tests for ``simulation.group_stage`` (§2.1, §6.8).

The strict cascade is: points -> goal difference -> goals scored -> head-to-head
(points, then GD, then GF among the tied teams) -> drawing of lots (seeded). These
tests hand-build numpy standings so each rung of the ladder is exercised in
isolation and asserted against the spec ordering, plus a determinism check on the
random drawing of lots.

All results are ``(i, j, goals_i, goals_j)`` tuples for a 4-team round robin.
"""

from __future__ import annotations

import numpy as np

from simulation.group_stage import TeamResult, _resolve_tie, rank_group, tally

# Generic round-robin fixture pairs (team indices) for 4 teams / 6 matches.
FIXTURES = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def _build(scorelines):
    """Turn a list of (gi, gj) aligned with FIXTURES into result tuples + tally."""
    results = [
        (FIXTURES[k][0], FIXTURES[k][1], scorelines[k][0], scorelines[k][1])
        for k in range(len(FIXTURES))
    ]
    points, gf, ga = tally(4, results)
    return results, points, gf, ga


# --------------------------------------------------------------------------- #
# tally(): the raw accumulator the whole cascade is built on.
# --------------------------------------------------------------------------- #


def test_tally_points_and_goals_from_known_results():
    """3/1/0 scoring and gf/ga accumulation from a fully known set of results."""
    # 0 beats 1 (2-1); 0 draws 2 (0-0); 3 beats 0 (1-0).
    results = [
        (0, 1, 2, 1),  # 0 win
        (0, 2, 0, 0),  # draw
        (3, 0, 1, 0),  # 3 win, 0 loss
    ]
    points, gf, ga = tally(4, results)

    # Points: 0 -> 3(win)+1(draw)+0(loss)=4 ; 1 -> 0 ; 2 -> 1 ; 3 -> 3.
    assert points.tolist() == [4, 0, 1, 3]
    # Goals for: 0 -> 2+0+0=2 ; 1 -> 1 ; 2 -> 0 ; 3 -> 1.
    assert gf.tolist() == [2, 1, 0, 1]
    # Goals against: 0 -> 1+0+1=2 ; 1 -> 2 ; 2 -> 0 ; 3 -> 0.
    assert ga.tolist() == [2, 2, 0, 0]
    # Symmetry: total goals for == total goals against across the group.
    assert int(gf.sum()) == int(ga.sum())


def test_tally_returns_integer_arrays():
    """Standings are integer counts, not floats (downstream sorts rely on it)."""
    results = [(0, 1, 3, 2), (2, 3, 1, 1)]
    points, gf, ga = tally(4, results)
    for arr in (points, gf, ga):
        assert isinstance(arr, np.ndarray)
        assert np.issubdtype(arr.dtype, np.integer)
        assert arr.shape == (4,)


# --------------------------------------------------------------------------- #
# Rung 2: goal difference breaks a tie on points.
# --------------------------------------------------------------------------- #


def test_goal_difference_breaks_points_tie():
    """Two teams level on points are separated by overall goal difference."""
    # 0 & 1 both finish on 7 pts (draw each other, beat 2 and 3); 0 wins bigger.
    scorelines = [
        (1, 1),  # 0 vs 1 draw  -> both +1
        (3, 0),  # 0 beats 2 by 3
        (3, 0),  # 0 beats 3 by 3
        (1, 0),  # 1 beats 2 by 1
        (1, 0),  # 1 beats 3 by 1
        (0, 0),  # 2 vs 3 draw
    ]
    results, points, gf, ga = _build(scorelines)
    gd = gf - ga

    assert points[0] == points[1] == 7  # genuine points tie
    assert gd[0] > gd[1]  # 0 has the superior goal difference (+6 vs +2)

    order = rank_group(points, gf, ga, results, np.zeros(4))
    # GD alone (rung 2) settles it before head-to-head or lots are consulted.
    assert order.index(0) < order.index(1)
    assert order == [0, 1, 2, 3]


# --------------------------------------------------------------------------- #
# Rung 3: goals scored breaks a tie on points AND goal difference.
# --------------------------------------------------------------------------- #


def test_goals_scored_breaks_points_and_gd_tie():
    """Level on points and GD, the team that scored more ranks higher."""
    # 0 & 1 draw (2-2) so the head-to-head is level; both beat 2 and 3 by the same
    # margin but 0 scores more goals than 1 overall.
    scorelines = [
        (2, 2),  # 0 vs 1 draw, equal goals in H2H
        (3, 1),  # 0 beats 2 by 2 (scores 3)
        (3, 1),  # 0 beats 3 by 2 (scores 3)
        (2, 0),  # 1 beats 2 by 2 (scores 2)
        (2, 0),  # 1 beats 3 by 2 (scores 2)
        (1, 1),  # 2 vs 3 draw
    ]
    results, points, gf, ga = _build(scorelines)
    gd = gf - ga

    assert points[0] == points[1] == 7  # points tie
    assert gd[0] == gd[1]  # goal-difference tie too
    assert gf[0] > gf[1]  # 0 simply scored more (8 vs 6)

    order = rank_group(points, gf, ga, results, np.zeros(4))
    assert order.index(0) < order.index(1)
    assert order == [0, 1, 2, 3]


# --------------------------------------------------------------------------- #
# Rung 4: head-to-head, when teams are level on points, GD and GF overall.
# --------------------------------------------------------------------------- #


def test_head_to_head_breaks_full_overall_tie():
    """Teams identical on (points, GD, GF) are ordered by their direct meeting.

    0 and 1 both finish on 4 pts, GD 0, GF 1 — indistinguishable on the primary
    cascade — and 0 beat 1 head-to-head 1-0, so 0 must rank above 1.
    """
    scorelines = [
        (1, 0),  # 0 beats 1, 1-0  <- the decisive head-to-head
        (0, 0),  # 0 vs 2 draw
        (0, 1),  # 0 loses to 3
        (0, 0),  # 1 vs 2 draw
        (1, 0),  # 1 beats 3
        (0, 1),  # 2 loses to 3
    ]
    results, points, gf, ga = _build(scorelines)
    gd = gf - ga

    # 0 and 1 are genuinely indistinguishable on every primary key.
    assert (points[0], gd[0], gf[0]) == (points[1], gd[1], gf[1]) == (4, 0, 1)
    # And they are not tied with the other two teams (so only 0 vs 1 needs H2H).
    assert (points[2], gd[2], gf[2]) != (4, 0, 1)
    assert (points[3], gd[3], gf[3]) != (4, 0, 1)

    order = rank_group(points, gf, ga, results, np.zeros(4))
    # Head-to-head winner (0) ranks ahead of head-to-head loser (1).
    assert order.index(0) < order.index(1)
    # Full expected order: 3 wins the group, then 0 over 1 on H2H, then 2.
    assert order == [3, 0, 1, 2]


def test_head_to_head_is_decisive_and_reversible():
    """The direct result alone settles a level pair, and reversing it flips order.

    Exercises the head-to-head resolver directly (``_resolve_tie``): the two teams
    are already known to be level on the primary cascade, so only their mutual
    match — recomputed from ``results`` — can separate them. This isolates rung 4
    cleanly, which an overall-tally construction cannot (the H2H goals also feed
    the overall totals, so varying them would break the overall tie).
    """
    no_lots = np.zeros(4)

    # 0 beats 1 head-to-head -> 0 ranks first.
    assert _resolve_tie([0, 1], [(0, 1, 2, 1)], no_lots) == [0, 1]
    # Reverse only the head-to-head result -> the order of the pair flips.
    assert _resolve_tie([0, 1], [(0, 1, 1, 2)], no_lots) == [1, 0]


def test_head_to_head_uses_only_matches_among_tied_teams():
    """Results against non-tied teams must not pollute the head-to-head record.

    0 lost heavily to outsider team 2, but among the tied pair {0, 1} only the
    0-vs-1 meeting counts, which 0 won — so 0 still ranks ahead of 1.
    """
    results = [
        (0, 1, 1, 0),  # 0 beats 1 in the only match that counts for this tie
        (0, 2, 0, 5),  # 0 thrashed by an outsider — irrelevant to the {0,1} tie
        (1, 2, 1, 0),  # 1's outside result — also irrelevant
    ]
    assert _resolve_tie([0, 1], results, np.zeros(4)) == [0, 1]


def test_head_to_head_gd_then_gf_among_tied_teams():
    """Within head-to-head: points first, then GD, then GF among the tied teams.

    A 3-team head-to-head triangle where all three are level on H2H points
    (each wins one, loses one); ordering then falls to head-to-head goal
    difference and goals scored.
    """
    # Triangle among {0, 1, 2}: 0>1, 1>2, 2>0, but with different margins/totals.
    results = [
        (0, 1, 3, 0),  # 0 beats 1 by 3
        (1, 2, 1, 0),  # 1 beats 2 by 1
        (2, 0, 1, 0),  # 2 beats 0 by 1
    ]
    # H2H points are 3 each. H2H goal diff: 0 -> +3-1=+2 ; 1 -> -3+1=-2 ; 2 -> +1-1=0.
    # So 0 (GD +2) > 2 (GD 0) > 1 (GD -2).
    assert _resolve_tie([0, 1, 2], results, np.zeros(4)) == [0, 2, 1]


# --------------------------------------------------------------------------- #
# Rung 6: exact tie -> deterministic drawing of lots.
# --------------------------------------------------------------------------- #


def _exact_tie_group():
    """Two teams identical on points/GD/GF AND level head-to-head (a 0-0 draw)."""
    scorelines = [
        (0, 0),  # 0 vs 1 draw 0-0 -> head-to-head is level too
        (1, 0),  # 0 beats 2
        (1, 0),  # 0 beats 3
        (1, 0),  # 1 beats 2
        (1, 0),  # 1 beats 3
        (0, 0),  # 2 vs 3 draw
    ]
    return _build(scorelines)


def test_exact_tie_falls_through_to_lots():
    """When every prior rung is level, the seeded lots array decides — higher wins."""
    results, points, gf, ga = _exact_tie_group()
    gd = gf - ga

    # 0 and 1 are level on points, GD, GF, and drew head-to-head 0-0.
    assert (points[0], gd[0], gf[0]) == (points[1], gd[1], gf[1]) == (7, 2, 2)

    # lots gives 0 the larger key -> 0 ranks first.
    order_a = rank_group(points, gf, ga, results, np.array([0.9, 0.1, 0.0, 0.0]))
    assert order_a.index(0) < order_a.index(1)

    # Swap the lots -> the order of the tied pair flips, proving lots is the only
    # discriminator left (nothing else changed).
    order_b = rank_group(points, gf, ga, results, np.array([0.1, 0.9, 0.0, 0.0]))
    assert order_b.index(1) < order_b.index(0)


def test_drawing_of_lots_is_deterministic_under_fixed_seed():
    """Same seed -> identical lots -> identical ranking (reproducibility, §6.8)."""
    results, points, gf, ga = _exact_tie_group()

    seed = 20260604
    lots1 = np.random.default_rng(seed).random(4)
    lots2 = np.random.default_rng(seed).random(4)
    assert np.array_equal(lots1, lots2)  # seeded RNG is reproducible

    order1 = rank_group(points, gf, ga, results, lots1)
    order2 = rank_group(points, gf, ga, results, lots2)
    assert order1 == order2  # deterministic resolution

    # A different seed may legitimately permute the tied pair, but must still
    # produce a valid permutation of all four teams.
    other = rank_group(points, gf, ga, results, np.random.default_rng(seed + 1).random(4))
    assert sorted(order1) == sorted(other) == [0, 1, 2, 3]


# --------------------------------------------------------------------------- #
# rank_group structural invariants.
# --------------------------------------------------------------------------- #


def test_rank_group_returns_full_permutation():
    """The result is always a permutation of all team indices, best -> worst."""
    results, points, gf, ga = _build([(2, 1), (1, 0), (0, 3), (2, 2), (1, 1), (0, 0)])
    order = rank_group(points, gf, ga, results, np.zeros(4))
    assert sorted(order) == [0, 1, 2, 3]
    # Points are non-increasing along the returned order (rung 1 dominates).
    pts_in_order = [int(points[t]) for t in order]
    assert pts_in_order == sorted(pts_in_order, reverse=True)


def test_clear_standings_need_no_tiebreaker():
    """A group with strictly distinct points ranks purely by points."""
    # 0 wins all, 1 wins two, 2 wins one, 3 loses all.
    scorelines = [
        (1, 0),  # 0 beats 1
        (1, 0),  # 0 beats 2
        (1, 0),  # 0 beats 3
        (1, 0),  # 1 beats 2
        (1, 0),  # 1 beats 3
        (1, 0),  # 2 beats 3
    ]
    results, points, gf, ga = _build(scorelines)
    assert points.tolist() == [9, 6, 3, 0]
    order = rank_group(points, gf, ga, results, np.zeros(4))
    assert order == [0, 1, 2, 3]


def test_teamresult_gd_property():
    """TeamResult.gd is goals-for minus goals-against."""
    tr = TeamResult(team="Brazil", rank=1, points=9, gf=7, ga=2)
    assert tr.gd == 5
