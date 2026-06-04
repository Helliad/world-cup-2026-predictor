# `data/` — provenance, schema, licensing, refresh

This directory holds the **committed data snapshot** the model trains on and the
static lookups the simulator needs. A clean clone reproduces the published
numbers from exactly these files (§6.7).

## Files

| File | What it is |
|------|------------|
| `results.csv` | Historical men's international results, 1872 → 2026 (incl. unplayed 2026 WC fixtures). |
| `groups.json` | The 12 official 2026 groups, reconstructed from the fixture list. |
| `aliases.json` | Team-name reconciliation: alternate spellings → canonical `results.csv` names. |
| `third_place_allocation.json` | Best-third → knockout-slot lookup (provisional until FIFA's table is encoded — release gate, §2.2). |
| `snapshot_manifest.json` | Provenance of the current `results.csv`: source, checksum, row count, date. |

## `results.csv` schema

| column | meaning |
|--------|---------|
| `date` | match date, `YYYY-MM-DD` |
| `home_team` / `away_team` | canonical team names |
| `home_score` / `away_score` | full-time goals (integer; `NA` for unplayed fixtures) |
| `tournament` | competition (`FIFA World Cup`, `Friendly`, …) |
| `city` / `country` | venue city and country |
| `neutral` | `TRUE`/`FALSE` — whether played at a neutral venue |

The snapshot includes the **72 scheduled 2026 group-stage fixtures** with `NA`
scores. These define the official groups (see below) and are excluded from the
training pool by the score filter.

## Provenance & licensing

- **Source:** [`martj42/international_results`](https://github.com/martj42/international_results)
  — the de-facto standard open dataset (~49k matches), continuously updated.
- **License:** the upstream dataset is published under **CC BY-NC-SA 4.0**.
  Redistribution with attribution is permitted for non-commercial use; this repo
  is MIT-licensed *code* over a CC BY-NC-SA *dataset* — keep that distinction.
  If you fork for commercial use, ship the downloader (`scripts/refresh_data.py`)
  instead of redistributing the CSV, or confirm current upstream terms.
- **Current snapshot:** see `snapshot_manifest.json` (`max_date`, `sha256`, `rows`).

## How `groups.json` is built

Within the group stage a team plays only the other three teams in its group, so
the connected components of the "played-each-other" graph over the 72 fixtures
are exactly the 12 groups — group **membership is official, not guessed**. Group
**letters** use the three official host pre-assignments (A=Mexico, B=Canada,
D=USA) and order the remaining nine by (first-match date, host city). Regenerate:

```bash
python -m scripts.build_groups
```

## Refresh + validate

```bash
# Download the latest upstream snapshot, validate, update results.csv + manifest:
python -m scripts.refresh_data

# Validate the committed snapshot without downloading:
python -m scripts.refresh_data --check
python -m scripts.validate_data            # standalone validator + quality report
python -m scripts.validate_data --strict   # warnings also fail
```

The validator (§8.4) enforces: required columns, parseable dates, non-negative
integer scores, boolean `neutral`, every group team resolvable via `aliases.json`,
and flags duplicates / implausible scores / sudden row-count drops. The refresh
**aborts and leaves the snapshot untouched** on any schema error.
