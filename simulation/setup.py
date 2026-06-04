"""Load and resolve the simulator's static inputs (groups, fixtures, allocation).

Resolves each group fixture's co-host home advantage from a team name into the
numeric γ to apply (reduced by ``cohost_multiplier``, §8.2), so the simulation
modules deal only in numbers.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS_PATH = ROOT / "data" / "groups.json"
ALLOCATION_PATH = ROOT / "data" / "third_place_allocation.json"


def load_sim_inputs(cfg: dict, model) -> dict:
    """Return ``{groups, fixtures_by_group, allocation, provisional}``.

    ``fixtures_by_group[letter]`` is a list of ``(home, away, home_adv_gamma)``.
    """
    groups_data = json.loads(GROUPS_PATH.read_text(encoding="utf-8"))
    groups = groups_data["groups"]
    cohost_mult = cfg["home_advantage"]["cohost_multiplier"]

    fixtures_by_group: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for f in groups_data["fixtures"]:
        home_adv = cohost_mult * model.gamma if f["home_advantage"] else 0.0
        fixtures_by_group[f["group"]].append((f["home"], f["away"], home_adv))

    allocation = json.loads(ALLOCATION_PATH.read_text(encoding="utf-8"))
    provisional = bool(allocation.get("provisional", True)) or bool(
        groups_data.get("meta", {}).get("provisional", False)
    )
    return {
        "groups": groups,
        "fixtures_by_group": dict(fixtures_by_group),
        "allocation": allocation,
        "provisional": provisional,
    }
