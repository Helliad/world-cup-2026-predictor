"""Reconstruct the 12 official 2026 groups from the committed fixture list.

The martj42 results.csv already contains the 72 group-stage fixtures of the 2026
World Cup (June 11-27, 2026). Within the group stage a team only plays the other
three teams in its own group, so the connected components of the
"played-each-other" graph are exactly the 12 groups. Group *membership* is
therefore taken directly from the official schedule — not guessed.

Group *letters* are assigned by:
  - the three official host pre-assignments (Mexico=A, Canada=B, USA=D), which
    FIFA announced ahead of the draw, then
  - the remaining nine groups ordered by (first-match date, host city).

This is deterministic and documented. Because the third-place -> bracket
allocation is provisional (§2.2), the exact letter labels do not affect
simulation correctness; they only affect display and the allocation key.

Run:  python -m scripts.build_groups
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "results.csv"
OUT = ROOT / "data" / "groups.json"

# Official host pre-assignments (announced before the December 2025 draw).
HOST_ANCHORS = {"Mexico": "A", "Canada": "B", "United States": "D"}
# Letters available for the nine non-host groups, in order.
FILL_LETTERS = ["C", "E", "F", "G", "H", "I", "J", "K", "L"]
# Co-host -> the country name (as it appears in results.csv `country`) where that
# co-host enjoys (reduced) home advantage (§8.2).
COHOST_COUNTRY = {"Mexico": "Mexico", "Canada": "Canada", "United States": "United States"}


def reconstruct_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    wc26 = df[(df["tournament"] == "FIFA World Cup") & (df["date"].str.startswith("2026"))]
    if len(wc26) != 72:
        raise ValueError(f"Expected 72 group-stage fixtures, found {len(wc26)}.")

    # Adjacency over the group stage.
    adj: dict[str, set[str]] = defaultdict(set)
    for _, r in wc26.iterrows():
        adj[r["home_team"]].add(r["away_team"])
        adj[r["away_team"]].add(r["home_team"])

    # Connected components -> groups.
    seen: set[str] = set()
    components: list[set[str]] = []
    for t in adj:
        if t in seen:
            continue
        stack, comp = [t], set()
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            comp.add(u)
            stack.extend(adj[u] - seen)
        components.append(comp)

    if len(components) != 12 or any(len(c) != 4 for c in components):
        raise ValueError(f"Expected 12 groups of 4; got sizes {[len(c) for c in components]}.")

    # First-match metadata per component (for ordering + within-group order).
    def first_match_date(team: str) -> str:
        sub = wc26[(wc26["home_team"] == team) | (wc26["away_team"] == team)]
        return sub["date"].min()

    def comp_key(comp: set[str]) -> tuple[str, str, tuple[str, ...]]:
        sub = wc26[wc26["home_team"].isin(comp) | wc26["away_team"].isin(comp)]
        first = sub.sort_values("date").iloc[0]
        return (first["date"], str(first["city"]), tuple(sorted(comp)))

    # Assign letters.
    assigned: dict[str, set[str]] = {}
    remaining: list[set[str]] = []
    for comp in components:
        host = next((h for h in HOST_ANCHORS if h in comp), None)
        if host:
            assigned[HOST_ANCHORS[host]] = comp
        else:
            remaining.append(comp)
    remaining.sort(key=comp_key)
    for letter, comp in zip(FILL_LETTERS, remaining, strict=True):
        assigned[letter] = comp

    # Order teams within a group: host first (if any), then by first-match date, then name.
    def team_order(team: str, comp_letter: str) -> tuple[int, str, str]:
        is_host = team in HOST_ANCHORS and HOST_ANCHORS[team] == comp_letter
        return (0 if is_host else 1, first_match_date(team), team)

    groups: dict[str, list[str]] = {}
    for letter in sorted(assigned):
        comp = assigned[letter]
        groups[letter] = sorted(comp, key=lambda t: team_order(t, letter))
    return groups


def reconstruct_fixtures(df: pd.DataFrame, groups: dict[str, list[str]]) -> list[dict]:
    """The 72 actual scheduled group fixtures, each with host advantage resolved.

    ``home_advantage`` names the team (if any) that gets the reduced co-host home
    term for that match: the home side iff it is a co-host playing in its own
    country (§8.2). All other matches are neutral.
    """
    team_to_group = {t: g for g, teams in groups.items() for t in teams}
    wc26 = df[(df["tournament"] == "FIFA World Cup") & (df["date"].str.startswith("2026"))]
    fixtures = []
    for _, r in wc26.sort_values("date").iterrows():
        home, away, country = r["home_team"], r["away_team"], str(r["country"])
        home_adv = home if COHOST_COUNTRY.get(home) == country else None
        fixtures.append(
            {
                "group": team_to_group[home],
                "date": r["date"],
                "home": home,
                "away": away,
                "country": country,
                "home_advantage": home_adv,
            }
        )
    return fixtures


def main() -> int:
    df = pd.read_csv(RESULTS, encoding="utf-8")
    groups = reconstruct_groups(df)
    fixtures = reconstruct_fixtures(df, groups)

    payload = {
        "meta": {
            "provisional": False,
            "draw_reflected": True,
            "source": "Reconstructed from the official 2026 fixture list in data/results.csv "
            "(martj42/international_results).",
            "letter_assignment": "Host anchors A=Mexico, B=Canada, D=USA (FIFA pre-assignment); "
            "remaining groups ordered by (first-match date, host city). Letters may not "
            "match FIFA's published A-L labels for non-host groups; membership is official.",
        },
        "groups": groups,
        "fixtures": fixtures,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT.relative_to(ROOT)} with {len(groups)} groups:")
    for letter, teams in groups.items():
        print(f"  {letter}: {', '.join(teams)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
