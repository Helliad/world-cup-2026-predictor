"""Group stage: round-robin standings + the strict tiebreaker cascade (§2.1, §6.1).

The cascade (points → GD → GF → head-to-head → drawing of lots) lives in
``rank_group`` and is the single source of truth used by both the clear
single-tournament path here and the vectorised Monte Carlo (which calls it only
to patch the rare sims that tie on the primary key). Fair-play (criterion 5) is
not simulated; per the spec it collapses into seeded lots (criterion 6).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Within-group index pairs for a generic round-robin of 4 teams (6 matches).
GROUP_FIXTURES = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


@dataclass
class TeamResult:
    """A team's group-stage record and final position (1 = group winner)."""

    team: str
    rank: int
    points: int
    gf: int
    ga: int

    @property
    def gd(self) -> int:
        return self.gf - self.ga


def _resolve_tie(
    tied: list[int], results: list[tuple[int, int, int, int]], lots: np.ndarray
) -> list[int]:
    """Order teams that are level on (points, GD, GF) by head-to-head then lots.

    ``results`` are (i, j, goals_i, goals_j) for every group match; only matches
    *among the tied teams* count for head-to-head. ``lots[t]`` is a unique seeded
    random key that breaks any residual tie deterministically (criterion 6).
    """
    if len(tied) == 1:
        return tied
    s = set(tied)
    hp = dict.fromkeys(tied, 0)
    hgf = dict.fromkeys(tied, 0)
    hga = dict.fromkeys(tied, 0)
    for i, j, gi, gj in results:
        if i in s and j in s:
            hgf[i] += gi
            hga[i] += gj
            hgf[j] += gj
            hga[j] += gi
            if gi > gj:
                hp[i] += 3
            elif gi < gj:
                hp[j] += 3
            else:
                hp[i] += 1
                hp[j] += 1
    # head-to-head: points, then GD, then GF; lots breaks the remainder.
    return sorted(
        tied,
        key=lambda t: (hp[t], hgf[t] - hga[t], hgf[t], float(lots[t])),
        reverse=True,
    )


def rank_group(
    points: np.ndarray,
    gf: np.ndarray,
    ga: np.ndarray,
    results: list[tuple[int, int, int, int]],
    lots: np.ndarray,
) -> list[int]:
    """Return the 4 team indices ordered best → worst by the full cascade (§2.1)."""
    gd = gf - ga
    teams = list(range(len(points)))
    order = sorted(teams, key=lambda t: (points[t], gd[t], gf[t]), reverse=True)

    final: list[int] = []
    i = 0
    while i < len(order):
        j = i
        key_i = (points[order[i]], gd[order[i]], gf[order[i]])
        while j < len(order) and (points[order[j]], gd[order[j]], gf[order[j]]) == key_i:
            j += 1
        final.extend(_resolve_tie(order[i:j], results, lots))
        i = j
    return final


def tally(
    n_teams: int, results: list[tuple[int, int, int, int]]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Accumulate (points, goals-for, goals-against) from match results."""
    points = np.zeros(n_teams, dtype=np.int64)
    gf = np.zeros(n_teams, dtype=np.int64)
    ga = np.zeros(n_teams, dtype=np.int64)
    for i, j, gi, gj in results:
        gf[i] += gi
        ga[i] += gj
        gf[j] += gj
        ga[j] += gi
        if gi > gj:
            points[i] += 3
        elif gi < gj:
            points[j] += 3
        else:
            points[i] += 1
            points[j] += 1
    return points, gf, ga


def simulate_group(
    teams: list[str],
    model,
    rng: np.random.Generator,
    fixtures: list[tuple[str, str, float]] | None = None,
) -> list[TeamResult]:
    """Play one group and return its 4 teams ranked best → worst (§6.1).

    ``fixtures`` is an optional explicit schedule of (home, away, home_adv_gamma)
    — used to honour the real 2026 venues / co-host home advantage. Without it a
    generic neutral round-robin is played.
    """
    from simulation.knockout import sample_scoreline  # shared sampler

    idx = {t: k for k, t in enumerate(teams)}
    if fixtures is None:
        fixtures = [(teams[i], teams[j], 0.0) for i, j in GROUP_FIXTURES]

    results: list[tuple[int, int, int, int]] = []
    for home, away, home_adv in fixtures:
        x, y = sample_scoreline(model, home, away, home_adv, rng)
        results.append((idx[home], idx[away], x, y))

    points, gf, ga = tally(len(teams), results)
    lots = rng.random(len(teams))
    order = rank_group(points, gf, ga, results, lots)
    return [
        TeamResult(team=teams[t], rank=pos + 1, points=int(points[t]), gf=int(gf[t]), ga=int(ga[t]))
        for pos, t in enumerate(order)
    ]
