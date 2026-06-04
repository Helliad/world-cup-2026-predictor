"""Schema + data-quality validation for results.csv (§8.4).

A hand-rolled validator (no pandera dependency) that enforces the ingest
contract: required columns, parseable dates, non-negative integer scores,
boolean ``neutral``, resolvable team names. Emits a short data-quality report
and **fails loudly** on schema violations so we never train on silently
malformed data.

Usage:
  python -m scripts.validate_data                 # validate the committed snapshot
  python -m scripts.validate_data --strict        # warnings also fail
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "results.csv"
ALIASES = ROOT / "data" / "aliases.json"
GROUPS = ROOT / "data" / "groups.json"

REQUIRED_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "tournament",
    "city",
    "country",
    "neutral",
]

# Implausible-but-not-impossible score threshold (largest int'l win is ~31-0).
MAX_PLAUSIBLE_SCORE = 31


@dataclass
class Report:
    """Outcome of a validation pass. ``ok`` is False if there are any errors."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def render(self) -> str:
        lines = ["# Data-quality report", ""]
        for k, v in self.stats.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
        lines.append(f"Errors: {len(self.errors)}  |  Warnings: {len(self.warnings)}")
        for e in self.errors:
            lines.append(f"  [ERROR] {e}")
        for w in self.warnings:
            lines.append(f"  [WARN]  {w}")
        return "\n".join(lines)


def load_aliases(path: Path = ALIASES) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def canonical_name(name: str, aliases: dict[str, str]) -> str:
    """Resolve a team name through the alias table (identity if not aliased)."""
    return aliases.get(name, name)


def validate_results(
    df: pd.DataFrame,
    aliases: dict[str, str] | None = None,
    prev_row_count: int | None = None,
) -> Report:
    """Validate a results dataframe against the ingest contract.

    ``prev_row_count`` enables the snapshot-shrink check (§8.4): a sudden drop in
    rows between snapshots is flagged.
    """
    rep = Report()
    aliases = aliases or {}

    # --- schema: required columns present ---
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        rep.errors.append(f"Missing required columns: {missing}")
        return rep  # cannot meaningfully continue

    n = len(df)
    rep.stats["rows"] = n

    # --- dates parseable ---
    dates = pd.to_datetime(df["date"], errors="coerce", format="%Y-%m-%d")
    n_bad_dates = int(dates.isna().sum())
    if n_bad_dates:
        rep.errors.append(f"{n_bad_dates} rows have unparseable dates (expected YYYY-MM-DD).")
    else:
        rep.stats["date_range"] = f"{df['date'].min()} -> {df['date'].max()}"

    # --- scores: NA allowed (future fixtures); else non-negative integers ---
    played = df["home_score"].notna() & df["away_score"].notna()
    rep.stats["played_rows"] = int(played.sum())
    rep.stats["unplayed_rows"] = int((~played).sum())
    for col in ("home_score", "away_score"):
        vals = pd.to_numeric(df.loc[played, col], errors="coerce")
        if vals.isna().any():
            rep.errors.append(f"{col}: non-numeric values among played matches.")
            continue
        if (vals < 0).any():
            rep.errors.append(f"{col}: negative scores present.")
        if ((vals % 1) != 0).any():
            rep.errors.append(f"{col}: non-integer scores present.")
        n_implausible = int((vals > MAX_PLAUSIBLE_SCORE).sum())
        if n_implausible:
            rep.warnings.append(
                f"{col}: {n_implausible} implausibly high scores (> {MAX_PLAUSIBLE_SCORE})."
            )

    # --- neutral boolean-like ---
    neutral_vals = set(df["neutral"].astype(str).str.upper().unique())
    if not neutral_vals <= {"TRUE", "FALSE"}:
        rep.errors.append(f"`neutral` has non-boolean values: {neutral_vals - {'TRUE', 'FALSE'}}")

    # --- duplicate fixtures (same date + home + away) ---
    dup_mask = df.duplicated(subset=["date", "home_team", "away_team"], keep=False)
    n_dups = int(dup_mask.sum())
    if n_dups:
        rep.warnings.append(f"{n_dups} rows are part of duplicate (date, home, away) fixtures.")

    # --- team-name resolvability: every group team resolves into results.csv ---
    canon_teams = set(df["home_team"]) | set(df["away_team"])
    rep.stats["distinct_teams"] = len(canon_teams)
    if GROUPS.exists():
        groups = json.loads(GROUPS.read_text(encoding="utf-8"))["groups"]
        unresolved = []
        for letter, teams in groups.items():
            for t in teams:
                if canonical_name(t, aliases) not in canon_teams:
                    unresolved.append(f"{t} (group {letter})")
        if unresolved:
            rep.errors.append(f"Group teams not resolvable to results.csv: {unresolved}")
        else:
            rep.stats["group_teams_resolved"] = "48/48"

    # --- snapshot shrink check ---
    if prev_row_count is not None:
        rep.stats["prev_rows"] = prev_row_count
        if n < prev_row_count * 0.98:  # >2% shrink is suspicious for an append-only feed
            rep.warnings.append(
                f"Row count dropped from {prev_row_count} to {n} (>2%). Possible upstream issue."
            )

    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate data/results.csv against the ingest contract."
    )
    ap.add_argument("--path", default=str(RESULTS), help="Path to results.csv")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = ap.parse_args(argv)

    df = pd.read_csv(args.path, encoding="utf-8")
    rep = validate_results(df, aliases=load_aliases())
    print(rep.render())

    if not rep.ok:
        print("\nVALIDATION FAILED (errors present).", file=sys.stderr)
        return 1
    if args.strict and rep.warnings:
        print("\nVALIDATION FAILED (--strict and warnings present).", file=sys.stderr)
        return 1
    print("\nVALIDATION PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
