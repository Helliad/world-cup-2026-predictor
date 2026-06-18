#!/usr/bin/env python3
"""Diff the freshly-written web/public/predictions.json against its committed
(HEAD) version and print the title race + biggest probability swings, ready to
paste into a fixture-update commit message.

Run from anywhere (paths resolve relative to the repo); requires that the new
predictions.json has already been written by `python -m scripts.run_pipeline`
and that the baseline is the version in git HEAD.

    python .claude/skills/update-fixtures/swings.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # .../.claude/skills/update-fixtures/ -> repo root
PRED = ROOT / "web" / "public" / "predictions.json"
TOP_N = 10  # how many swings to list per metric


def head_version() -> dict | None:
    try:
        raw = subprocess.check_output(
            ["git", "show", "HEAD:web/public/predictions.json"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


def by_team(pred: dict, key: str) -> dict[str, float]:
    return {t["team"]: t.get(key) for t in pred["teams"]}


def swings(old: dict, new: dict, key: str) -> list[tuple[float, str, float, float]]:
    o, n = by_team(old, key), by_team(new, key)
    out = []
    for team, nv in n.items():
        ov = o.get(team)
        if ov is None or nv is None:
            continue
        out.append((nv - ov, team, ov, nv))
    out.sort(key=lambda x: -abs(x[0]))
    return out


def fmt(rows: list[tuple[float, str, float, float]]) -> None:
    for delta, team, ov, nv in rows[:TOP_N]:
        if abs(delta) < 0.005:  # < 0.5pp — noise at this point
            continue
        arrow = "up" if delta > 0 else "down"
        print(f"  {team} {ov * 100:.0f}->{nv * 100:.0f} ({arrow})")


def main() -> int:
    if not PRED.exists():
        print(f"missing {PRED} — run the pipeline first", file=sys.stderr)
        return 1
    new = json.loads(PRED.read_text(encoding="utf-8"))
    teams = new["teams"]

    print("Title race (top 5):")
    for d in teams[:5]:
        print(f"  {d['team']} {d['p_win'] * 100:.1f}%")

    old = head_version()
    if old is None:
        print("\n(no committed baseline in HEAD to diff against)")
        return 0

    print("\nBiggest advance-prob swings:")
    fmt(swings(old, new, "p_advance"))
    print("\nBiggest title-prob swings:")
    fmt(swings(old, new, "p_win"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
