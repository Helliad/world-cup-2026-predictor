"""Hierarchical priors, confederation pooling, and data-confidence helpers (§4.4).

The Dixon-Coles fit (`dixon_coles.py`) partially pools each team's attack/defence
toward its **confederation mean**, so thin records are pulled toward a sensible
regional baseline rather than producing absurd parameters from a handful of
matches. This module owns the confederation mapping and the per-team
data-confidence labelling surfaced in `predictions.json` (§7).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFEDERATIONS_PATH = ROOT / "data" / "confederations.json"
ALIASES_PATH = ROOT / "data" / "aliases.json"

# Confederation pool used for any team not found in confederations.json. Pooling
# toward this bucket's mean behaves like the global ridge — a safe fallback.
GLOBAL_POOL = "GLOBAL"


def load_aliases(path: Path = ALIASES_PATH) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def load_team_confederation(
    confed_path: Path = CONFEDERATIONS_PATH,
    aliases: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return a ``canonical_team_name -> confederation`` mapping."""
    aliases = aliases or {}
    raw = json.loads(confed_path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for confed, teams in raw.items():
        if confed.startswith("_"):
            continue
        for t in teams:
            mapping[aliases.get(t, t)] = confed
    return mapping


def build_confederation_index(
    teams: list[str],
    team_to_confed: dict[str, str],
) -> tuple[np.ndarray, list[str]]:
    """Map an ordered team list to integer confederation indices.

    Returns ``(confed_idx, confed_names)`` where ``confed_idx[i]`` is the index
    into ``confed_names`` for ``teams[i]``. Unmapped teams go to GLOBAL_POOL.
    """
    confed_names: list[str] = []
    name_to_idx: dict[str, int] = {}

    def idx_for(name: str) -> int:
        if name not in name_to_idx:
            name_to_idx[name] = len(confed_names)
            confed_names.append(name)
        return name_to_idx[name]

    confed_idx = np.array(
        [idx_for(team_to_confed.get(t, GLOBAL_POOL)) for t in teams], dtype=np.int64
    )
    return confed_idx, confed_names


def recent_match_counts(
    matches: pd.DataFrame,
    teams: list[str],
    ref_date: pd.Timestamp,
    window_days: int = 1461,  # ~4 years
) -> dict[str, int]:
    """Count matches each team played within ``window_days`` before ``ref_date``.

    Used for the data-confidence guardrail (§4.4): teams with few recent matches
    are flagged so the UI can label them honestly.
    """
    cutoff = ref_date - pd.Timedelta(days=window_days)
    dates = pd.to_datetime(matches["date"])
    recent = matches[(dates >= cutoff) & (dates <= ref_date)]
    home_counts = recent["home_team"].value_counts()
    away_counts = recent["away_team"].value_counts()
    counts: dict[str, int] = {}
    for t in teams:
        counts[t] = int(home_counts.get(t, 0)) + int(away_counts.get(t, 0))
    return counts


def data_confidence_labels(
    counts: dict[str, int],
    high_threshold: int,
    medium_threshold: int,
) -> dict[str, str]:
    """Bucket teams into ``high`` / ``medium`` / ``low`` data confidence."""
    labels: dict[str, str] = {}
    for team, c in counts.items():
        if c >= high_threshold:
            labels[team] = "high"
        elif c >= medium_threshold:
            labels[team] = "medium"
        else:
            labels[team] = "low"
    return labels
