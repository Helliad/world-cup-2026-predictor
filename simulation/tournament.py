"""One full tournament, start to champion (§6.5).

Composes the format exactly: 12 groups → best-third selection → seed the 32-team
bracket → play to the final. Returns, for every team, the furthest stage reached.
This is the clear, readable reference implementation; the vectorised Monte Carlo
(`monte_carlo.py`) reproduces its aggregate behaviour and is cross-checked
against running this many times.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from simulation.group_stage import TeamResult, simulate_group
from simulation.knockout import KnockoutParams, play_knockout_match
from simulation.third_place import select_best_thirds

# Furthest-stage ladder. Index in this list is the stage code; higher = further.
STAGES = ["group", "r32", "r16", "qf", "sf", "final", "champion"]
STAGE_CODE = {s: i for i, s in enumerate(STAGES)}
# Stage a team is recorded as having reached when it WINS a given round.
_ADVANCE_LABEL = ["r16", "qf", "sf", "final", "champion"]


@dataclass
class TournamentResult:
    champion: str
    reached: dict[str, str]  # team -> furthest stage label
    group_results: dict[str, list[TeamResult]] = field(default_factory=dict)
    group_rank: dict[str, int] = field(default_factory=dict)  # team -> 1..4 in its group


def _resolve_slot(label: str, winners: dict[str, str], runners: dict[str, str]) -> str:
    kind, group = label.split("_")
    return winners[group] if kind == "W" else runners[group]


def play_bracket(
    r32_matches: list[tuple[str, str]],
    model,
    rng: np.random.Generator,
    params: KnockoutParams,
) -> tuple[str, dict[str, str]]:
    """Fold a 32-team bracket to a champion; track each team's furthest stage."""
    reached: dict[str, str] = {}
    for a, b in r32_matches:
        reached[a] = "r32"
        reached[b] = "r32"

    matches = r32_matches
    round_idx = 0
    champion = ""
    while matches:
        winners_round = []
        for a, b in matches:
            w = play_knockout_match(a, b, model, rng, params)
            reached[w] = _ADVANCE_LABEL[round_idx]
            winners_round.append(w)
        round_idx += 1
        if len(winners_round) == 1:
            champion = winners_round[0]
            break
        matches = [
            (winners_round[k], winners_round[k + 1]) for k in range(0, len(winners_round), 2)
        ]
    return champion, reached


def simulate_tournament(
    model,
    groups: dict[str, list[str]],
    fixtures_by_group: dict[str, list[tuple[str, str, float]]],
    allocation: dict,
    params: KnockoutParams,
    rng: np.random.Generator,
) -> TournamentResult:
    # 1. groups
    group_results: dict[str, list[TeamResult]] = {}
    for letter, teams in groups.items():
        group_results[letter] = simulate_group(teams, model, rng, fixtures_by_group.get(letter))

    winners = {g: r[0].team for g, r in group_results.items()}
    runners = {g: r[1].team for g, r in group_results.items()}
    thirds = [(g, r[2]) for g, r in group_results.items()]

    # 2. best thirds -> slots
    third_assignment = select_best_thirds(thirds, allocation, rng)

    # 3. build the R32 matchups in bracket order
    r32: list[tuple[str, str]] = []
    for m in sorted(allocation["r32"], key=lambda x: x["match"]):
        top = _resolve_slot(m["top"], winners, runners)
        bottom = (
            third_assignment[m["match"]]
            if m["bottom"] == "3RD"
            else _resolve_slot(m["bottom"], winners, runners)
        )
        r32.append((top, bottom))

    # 4. fold to a champion
    champion, reached = play_bracket(r32, model, rng, params)

    # teams that didn't make the knockout stay at "group"
    group_rank: dict[str, int] = {}
    for _letter, results in group_results.items():
        for res in results:
            group_rank[res.team] = res.rank
            reached.setdefault(res.team, "group")

    return TournamentResult(
        champion=champion,
        reached=reached,
        group_results=group_results,
        group_rank=group_rank,
    )
