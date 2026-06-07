"""Load and resolve the simulator's static inputs (groups, fixtures, allocation).

Resolves each group fixture's co-host home advantage from a team name into the
numeric γ to apply (reduced by ``cohost_multiplier``, §8.2), so the simulation
modules deal only in numbers.

Also loads any **actually-played 2026 results** (``data/results_2026.json``) and
turns them into pins the Monte Carlo applies instead of sampling: group results
fix the scoreline, knockout results fix who advances. With an empty/absent file
the pins are empty and the simulation is the pure pre-tournament forecast.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS_PATH = ROOT / "data" / "groups.json"
ALLOCATION_PATH = ROOT / "data" / "third_place_allocation.json"
RESULTS_PATH = ROOT / "data" / "results_2026.json"

# Group matches are numbered 1..72 in data/schedule.json; 73..104 are knockout.
_LAST_GROUP_MATCH = 72


def _load_played_results() -> list[dict]:
    if not RESULTS_PATH.exists():
        return []
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    return data.get("matches", [])


def _build_pins(
    played: list[dict], orient: dict[frozenset, tuple[str, str]]
) -> tuple[dict[tuple[str, str], tuple[int, int]], list[tuple[str, str]]]:
    """Split played results into group-scoreline pins and knockout-winner pins.

    ``orient`` maps the unordered team pair of each group fixture to its canonical
    ``(home, away)`` orientation, so a result entered either way round is stored
    against the fixture's own orientation (scores flipped to match).
    """
    pinned_group: dict[tuple[str, str], tuple[int, int]] = {}
    pinned_ko: list[tuple[str, str]] = []
    for r in played:
        match_no = r.get("match")
        is_group = (match_no is not None and match_no <= _LAST_GROUP_MATCH) or (
            "winner" not in r and "decided_by" not in r and r.get("round") in (None, "group")
        )
        if is_group:
            key = frozenset((r["home"], r["away"]))
            if key not in orient:
                raise ValueError(
                    f"results_2026.json match {match_no}: {r['home']} vs {r['away']} "
                    "is not a group fixture in groups.json"
                )
            chome, caway = orient[key]
            hs, as_ = int(r["home_score"]), int(r["away_score"])
            if (chome, caway) != (r["home"], r["away"]):
                hs, as_ = as_, hs  # flip to the fixture's canonical orientation
            pinned_group[(chome, caway)] = (hs, as_)
        else:
            winner = r["winner"]
            if winner not in (r["home"], r["away"]):
                raise ValueError(
                    f"results_2026.json match {match_no}: winner {winner!r} is not "
                    f"one of {r['home']} / {r['away']}"
                )
            loser = r["away"] if winner == r["home"] else r["home"]
            pinned_ko.append((winner, loser))
    return pinned_group, pinned_ko


def load_sim_inputs(cfg: dict, model) -> dict:
    """Return ``{groups, fixtures_by_group, allocation, provisional, pinned_group, pinned_ko}``.

    ``fixtures_by_group[letter]`` is a list of ``(home, away, home_adv_gamma)``.
    ``pinned_group[(home, away)]`` is an actual ``(home_score, away_score)`` to use
    instead of sampling; ``pinned_ko`` is a list of ``(winner, loser)`` names whose
    knockout meeting is forced to the real outcome.
    """
    groups_data = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    groups = groups_data["groups"]
    cohost_mult = cfg["home_advantage"]["cohost_multiplier"]

    fixtures_by_group: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    orient: dict[frozenset, tuple[str, str]] = {}
    for f in groups_data["fixtures"]:
        home_adv = cohost_mult * model.gamma if f["home_advantage"] else 0.0
        fixtures_by_group[f["group"]].append((f["home"], f["away"], home_adv))
        orient[frozenset((f["home"], f["away"]))] = (f["home"], f["away"])

    allocation = json.loads(ALLOCATION_PATH.read_text(encoding="utf-8"))
    provisional = bool(allocation.get("provisional", True)) or bool(
        groups_data.get("meta", {}).get("provisional", False)
    )

    pinned_group, pinned_ko = _build_pins(_load_played_results(), orient)

    return {
        "groups": groups,
        "fixtures_by_group": dict(fixtures_by_group),
        "allocation": allocation,
        "provisional": provisional,
        "pinned_group": pinned_group,
        "pinned_ko": pinned_ko,
    }
