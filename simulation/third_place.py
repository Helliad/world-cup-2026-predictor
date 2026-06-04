"""Best-third selection and bracket allocation (§2.2, §6.2).

Only 4 of the 12 third-placed teams are eliminated. The 8 best (ranked by
points → GD → GF → lots) advance and are slotted into the eight
winner-vs-third Round-of-32 matches. The allocation here is the documented
**provisional** fallback (data/third_place_allocation.json): assign the ranked
thirds to the third-slots in bracket order, always skipping a third whose source
group matches that slot's group winner (no same-group R32 meeting). The official
FIFA combination table replaces this as a release gate (§8.1).

This is where most simulator bugs live, so it carries the most tests (§6.8).
"""

from __future__ import annotations

import numpy as np

from simulation.group_stage import TeamResult


def third_slot_groups(allocation: dict) -> list[tuple[int, str]]:
    """Return [(match_number, winner_group), …] for the third-slots, in order."""
    out = []
    for m in allocation["r32"]:
        if m["bottom"] == "3RD":
            out.append((m["match"], m["top"].split("_")[1]))  # "W_A" -> "A"
    return out


def rank_thirds(
    thirds: list[tuple[str, TeamResult]], lots: dict[str, float]
) -> list[tuple[str, TeamResult]]:
    """Rank the 12 third-placed teams best → worst (points → GD → GF → lots)."""
    return sorted(
        thirds,
        key=lambda gt: (gt[1].points, gt[1].gd, gt[1].gf, lots[gt[0]]),
        reverse=True,
    )


def assign_thirds_to_slots(forbidden: list[str], ranked_groups: list[str]) -> list[int]:
    """Match the 8 ranked thirds to the 8 third-slots with no same-group meeting.

    ``forbidden[s]`` is the winner group of slot ``s``; ``ranked_groups[k]`` is the
    source group of the k-th best third. Returns ``slot -> rank-index``: a
    conflict-free perfect matching that prefers to seat higher-ranked thirds in
    earlier slots. A single-pass greedy can paint itself into a corner (a later
    slot left only its own group's third), so this uses backtracking — cheap for
    8 slots — and a conflict-free matching exists in essentially every real case.
    Falls back to rank order only if none exists.
    """
    n = len(forbidden)
    assignment = [-1] * n
    used = [False] * n

    def backtrack(slot: int) -> bool:
        if slot == n:
            return True
        for k in range(n):  # try thirds best-rank first
            if not used[k] and ranked_groups[k] != forbidden[slot]:
                used[k] = True
                assignment[slot] = k
                if backtrack(slot + 1):
                    return True
                used[k] = False
                assignment[slot] = -1
        return False

    if backtrack(0):
        return assignment
    return list(range(n))  # no conflict-free matching exists (vanishingly rare)


def select_best_thirds(
    thirds: list[tuple[str, TeamResult]],
    allocation: dict,
    rng: np.random.Generator,
) -> dict[int, str]:
    """Pick the 8 best thirds and map them to third-slots.

    ``thirds`` is [(group_letter, TeamResult)] for all 12 thirds. Returns
    ``{match_number: team_name}`` for the eight winner-vs-third matches.
    """
    lots = {g: float(rng.random()) for g, _ in thirds}
    ranked = rank_thirds(thirds, lots)
    top8 = ranked[:8]

    slots = third_slot_groups(allocation)
    forbidden = [winner_group for _match_no, winner_group in slots]
    ranked_groups = [g for g, _ in top8]
    slot_to_rank = assign_thirds_to_slots(forbidden, ranked_groups)
    return {slots[s][0]: top8[slot_to_rank[s]][1].team for s in range(len(slots))}
