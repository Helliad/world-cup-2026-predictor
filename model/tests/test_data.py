"""Tests for scripts/validate_data.py (§8.4 ingest contract).

Exercises validate_results, load_aliases, canonical_name, and the Report
dataclass against both the committed real snapshot and tiny synthetic frames
that inject specific schema/data-quality violations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.validate_data import (
    REQUIRED_COLUMNS,
    Report,
    canonical_name,
    load_aliases,
    validate_results,
)

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "data" / "results.csv"
ALIASES = ROOT / "data" / "aliases.json"
GROUPS = ROOT / "data" / "groups.json"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def aliases() -> dict[str, str]:
    return load_aliases()


def _good_row() -> dict:
    """A single, fully-valid results row."""
    return {
        "date": "2024-06-01",
        "home_team": "Brazil",
        "away_team": "Argentina",
        "home_score": 1,
        "away_score": 0,
        "tournament": "Friendly",
        "city": "Rio",
        "country": "Brazil",
        "neutral": False,
    }


def _good_df(n: int = 3) -> pd.DataFrame:
    rows = []
    pairs = [
        ("Brazil", "Argentina"),
        ("Spain", "Germany"),
        ("France", "England"),
        ("Italy", "Portugal"),
    ]
    for i in range(n):
        r = _good_row()
        h, a = pairs[i % len(pairs)]
        r["home_team"], r["away_team"] = h, a
        r["date"] = f"2024-06-0{(i % 9) + 1}"
        rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# (1) Real snapshot validates clean
# ---------------------------------------------------------------------------
def test_real_results_csv_validates_ok(aliases):
    df = pd.read_csv(RESULTS, encoding="utf-8")
    rep = validate_results(df, aliases=aliases)
    assert isinstance(rep, Report)
    # No errors => ok True, and ok must be consistent with the errors list.
    assert rep.errors == [], f"unexpected errors: {rep.errors}"
    assert rep.ok is True
    assert rep.stats["rows"] == len(df)


# ---------------------------------------------------------------------------
# (2) All 48 group teams resolve into results.csv
# ---------------------------------------------------------------------------
def test_all_group_teams_resolve(aliases):
    df = pd.read_csv(RESULTS, encoding="utf-8")
    rep = validate_results(df, aliases=aliases)

    # No unresolved-team error should be raised.
    assert not any("not resolvable" in e for e in rep.errors), rep.errors

    # And the validator should explicitly report full resolution.
    groups = json.loads(GROUPS.read_text(encoding="utf-8"))["groups"]
    total = sum(len(v) for v in groups.values())
    assert total == 48, f"expected 48 group teams, got {total}"
    assert rep.stats.get("group_teams_resolved") == "48/48"


def test_injected_unresolved_group_team_errors(aliases):
    # Drop a real group team from the results frame -> it must become unresolvable.
    groups = json.loads(GROUPS.read_text(encoding="utf-8"))["groups"]
    first_team = next(iter(next(iter(groups.values()))))
    canon = canonical_name(first_team, aliases)

    df = _good_df(4)
    # Ensure the dropped team is not present under any name in our tiny frame.
    assert canon not in (set(df["home_team"]) | set(df["away_team"]))

    rep = validate_results(df, aliases=aliases)
    assert rep.ok is False
    assert any("not resolvable" in e for e in rep.errors), rep.errors
    assert "group_teams_resolved" not in rep.stats


# ---------------------------------------------------------------------------
# (3) Negative score => error / not ok
# ---------------------------------------------------------------------------
def test_negative_score_errors(aliases):
    df = _good_df(2)
    df.loc[0, "home_score"] = -1
    rep = validate_results(df, aliases=aliases)
    assert rep.ok is False
    assert rep.errors  # non-empty
    assert any("negative scores" in e for e in rep.errors), rep.errors


def test_non_integer_score_errors(aliases):
    df = _good_df(2)
    df["home_score"] = df["home_score"].astype(float)
    df.loc[0, "home_score"] = 1.5
    rep = validate_results(df, aliases=aliases)
    assert rep.ok is False
    assert any("non-integer scores" in e for e in rep.errors), rep.errors


def test_all_valid_scores_no_score_error(aliases):
    # Positive control: a clean small frame yields no score-related errors.
    df = _good_df(3)
    rep = validate_results(df, aliases=aliases)
    assert not any("score" in e for e in rep.errors), rep.errors


# ---------------------------------------------------------------------------
# (4) Non-boolean neutral => error
# ---------------------------------------------------------------------------
def test_non_boolean_neutral_errors(aliases):
    df = _good_df(2)
    df["neutral"] = df["neutral"].astype(object)
    df.loc[0, "neutral"] = "maybe"
    rep = validate_results(df, aliases=aliases)
    assert rep.ok is False
    assert any("`neutral` has non-boolean values" in e for e in rep.errors), rep.errors
    # The offending value should be surfaced (upper-cased) in the message.
    assert any("MAYBE" in e for e in rep.errors), rep.errors


def test_boolean_neutral_strings_ok(aliases):
    # 'TRUE'/'False' style string booleans must NOT trip the neutral check.
    df = _good_df(2)
    df["neutral"] = df["neutral"].astype(object)
    df.loc[0, "neutral"] = "True"
    df.loc[1, "neutral"] = "false"
    rep = validate_results(df, aliases=aliases)
    assert not any("`neutral`" in e for e in rep.errors), rep.errors


# ---------------------------------------------------------------------------
# (5) Missing required column => error (and short-circuits)
# ---------------------------------------------------------------------------
def test_missing_required_column_errors(aliases):
    df = _good_df(2).drop(columns=["away_score"])
    rep = validate_results(df, aliases=aliases)
    assert rep.ok is False
    assert any("Missing required columns" in e for e in rep.errors), rep.errors
    assert any("away_score" in e for e in rep.errors), rep.errors
    # Schema failure short-circuits before any row-level stats are computed.
    assert "rows" not in rep.stats


@pytest.mark.parametrize("col", REQUIRED_COLUMNS)
def test_each_required_column_is_enforced(col, aliases):
    df = _good_df(2).drop(columns=[col])
    rep = validate_results(df, aliases=aliases)
    assert rep.ok is False
    assert any("Missing required columns" in e and col in e for e in rep.errors), (
        col,
        rep.errors,
    )


# ---------------------------------------------------------------------------
# (6) canonical_name + load_aliases
# ---------------------------------------------------------------------------
def test_canonical_name_resolves_known_alias(aliases):
    assert canonical_name("USA", aliases) == "United States"


def test_canonical_name_identity_for_unknown(aliases):
    # An unaliased name passes through unchanged.
    assert canonical_name("Brazil", aliases) == "Brazil"


def test_load_aliases_filters_comment_keys():
    raw = json.loads(ALIASES.read_text(encoding="utf-8"))
    aliases = load_aliases()
    # Underscore-prefixed metadata keys (e.g. "_comment") must be stripped.
    assert any(k.startswith("_") for k in raw), "expected a _comment key in aliases.json"
    assert not any(k.startswith("_") for k in aliases)
    # A real mapping survives the filter.
    assert aliases.get("USA") == "United States"


# ---------------------------------------------------------------------------
# Report dataclass invariants
# ---------------------------------------------------------------------------
def test_report_ok_property_tracks_errors():
    rep = Report()
    assert rep.ok is True
    rep.warnings.append("just a warning")
    assert rep.ok is True  # warnings alone do not flip ok
    rep.errors.append("boom")
    assert rep.ok is False


def test_report_render_includes_errors_and_warnings():
    rep = Report()
    rep.errors.append("an-error")
    rep.warnings.append("a-warning")
    rep.stats["rows"] = 5
    out = rep.render()
    assert "an-error" in out
    assert "a-warning" in out
    assert "rows: 5" in out
