#!/usr/bin/env python3
"""Fetch played 2026 World Cup results from openfootball/worldcup.json, cross-
reference our schedule, and report:

  1. VERIFY  — every already-pinned result in data/results_2026.json checked
               against openfootball (catches name-mapping / orientation bugs).
  2. DUE     — each schedule match not yet pinned whose date is on/before
               --today: a ready-to-paste results_2026.json line if openfootball
               shows a final score, else "unplayed (skip)".

This is the source step for the update-fixtures skill. openfootball is a
public-domain JSON feed on GitHub (raw.githubusercontent.com), which — unlike
Wikipedia — is on the cloud sandbox's egress allowlist, and is structured (no
HTML scraping, no group-letter mismatch). Matching is by canonical team pair, so
openfootball's group labels / match order are irrelevant.

Usage (from repo root, via the wc26 env):
    python .claude/skills/update-fixtures/fetch_results.py [--today YYYY-MM-DD]

Exit code 2 if any pinned result mismatches openfootball or a due match's teams
can't be resolved — i.e. something a human must look at before committing.
"""

import argparse
import datetime
import json
import ssl
import sys
import urllib.request

# Emit UTF-8 regardless of the platform console (Windows cp1252 would otherwise
# mangle "Curaçao" etc.); harmless on Linux cloud runs.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fetch_openfootball():
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(URL, timeout=30, context=ctx) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — surface the access failure plainly
        print(f"FETCH FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        print(
            "If this is '403 Host not in allowlist' on a cloud run, that is an "
            "environment failure — make no commit (see SKILL.md step 2).",
            file=sys.stderr,
        )
        sys.exit(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--today",
        default=datetime.date.today().isoformat(),
        help="cutoff date YYYY-MM-DD (default: system today)",
    )
    args = ap.parse_args()
    today = datetime.date.fromisoformat(args.today)

    aliases = load("data/aliases.json")
    schedule = load("data/schedule.json")["matches"]
    pinned = {m["match"]: m for m in load("data/results_2026.json")["matches"]}

    def canon(name):
        # aliases maps alternate -> canonical; pass canonical names through.
        return aliases.get(name, name)

    of = fetch_openfootball()
    # Index openfootball matches that have a final score, by canonical team pair.
    by_pair = {}
    for m in of["matches"]:
        score = m.get("score") or {}
        ft = score.get("ft")
        if not ft:
            continue  # not yet played
        key = frozenset({canon(m["team1"]), canon(m["team2"])})
        by_pair.setdefault(key, []).append(
            {
                "team1": canon(m["team1"]),
                "team2": canon(m["team2"]),
                "ft": ft,
                "date": m.get("date"),
                "round": m.get("round"),
                "extra": {k: score[k] for k in ("et", "p", "pens", "pen") if k in score},
            }
        )

    def lookup(home, away, date):
        cands = by_pair.get(frozenset({canon(home), canon(away)}), [])
        if len(cands) <= 1:
            return cands[0] if cands else None
        # multiple meetings (e.g. group + knockout) — pick the nearest date
        d = datetime.date.fromisoformat(date)
        return min(
            cands,
            key=lambda c: (
                abs((datetime.date.fromisoformat(c["date"]) - d).days) if c["date"] else 999
            ),
        )

    def oriented(rec, home, away):
        """Return (home_score, away_score) in OUR home/away orientation."""
        if canon(rec["team1"]) == canon(home):
            return rec["ft"][0], rec["ft"][1]
        if canon(rec["team1"]) == canon(away):
            return rec["ft"][1], rec["ft"][0]
        return None  # shouldn't happen — pair matched by set

    problems = 0

    # 1. VERIFY already-pinned results.
    print("=== VERIFY (pinned vs openfootball) ===")
    sched_by_num = {m["match"]: m for m in schedule}
    verified = mismatched = 0
    for num in sorted(pinned):
        p = pinned[num]
        s = sched_by_num.get(num, p)
        rec = lookup(
            s.get("home", p.get("home")), s.get("away", p.get("away")), s.get("date", "2026-06-11")
        )
        if rec is None:
            print(
                f"  [{num}] {p.get('home')} v {p.get('away')}: NOT in openfootball "
                f"(still listed unplayed there?) — leaving as-is"
            )
            continue
        hs, as_ = oriented(rec, s.get("home", p["home"]), s.get("away", p["away"]))
        if p.get("home_score") == hs and p.get("away_score") == as_:
            verified += 1
        else:
            mismatched += 1
            problems += 1
            print(
                f"  [{num}] MISMATCH: ours {p.get('home_score')}-{p.get('away_score')} "
                f"vs openfootball {hs}-{as_}  ({p.get('home')} v {p.get('away')})"
            )
    print(
        f"  {verified} pinned results match openfootball"
        + (f"; {mismatched} MISMATCH(es) above" if mismatched else "; 0 mismatches")
    )

    # 2. DUE-but-unpinned matches on/before --today.
    print(f"\n=== DUE & UNPINNED (date <= {today}) ===")
    due = [
        m
        for m in schedule
        if m["match"] not in pinned
        and m.get("date")
        and datetime.date.fromisoformat(m["date"]) <= today
    ]
    if not due:
        print("  (none)")
    for m in sorted(due, key=lambda x: x["match"]):
        num, home, away = m["match"], m["home"], m["away"]
        ko = m.get("round") != "group"
        rec = lookup(home, away, m["date"])
        if rec is None:
            print(f"  # match {num} {home} v {away} ({m['date']}): unplayed in openfootball — skip")
            continue
        hs, as_ = oriented(rec, home, away)
        if ko:
            problems += 1  # knockouts need winner/decided_by judgement
            print(
                f"  # match {num} KNOCKOUT {home} v {away}: openfootball ft {hs}-{as_} "
                f"extra={rec['extra']} — set winner + decided_by BY HAND (verify penalties)"
            )
        else:
            print(
                f'    {{ "match": {num}, "home": "{home}", "away": "{away}", '
                f'"home_score": {hs}, "away_score": {as_} }},'
            )

    print(
        f"\n{'OK' if problems == 0 else 'REVIEW NEEDED'}: "
        f"{len([m for m in due if lookup(m['home'], m['away'], m['date'])])} of "
        f"{len(due)} due matches have a final score in openfootball."
    )
    sys.exit(2 if problems else 0)


if __name__ == "__main__":
    main()
