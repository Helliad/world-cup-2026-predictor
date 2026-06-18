---
name: update-fixtures
description: >-
  Record newly-played 2026 World Cup match results and re-condition every
  downstream probability. Use when the user wants to update fixtures / pin
  results / log the latest matchday and refresh the predictions — i.e. add
  scores to data/results_2026.json, re-run the Monte Carlo pipeline, and commit
  the regenerated predictions. Run roughly every other day as matches are played.
---

# Update fixtures

Pin freshly-played matches into `data/results_2026.json`, re-run the full Monte
Carlo, and commit the regenerated `predictions.json` + `outcomes_sample.json`.
This reproduces commit `213f19a` ("data: pin opening 8 results, re-condition
predictions") as a repeatable routine.

**This routine is fully autonomous — the user is not in the loop.** Do not ask
the user for scores. Find the actual results yourself from the ESPN scoreboard
(step 2), pin them, re-run, and commit. The user only reviews the result
afterwards. The only times you stop and surface to the user instead of
proceeding: a dirty/unexpected working tree (step 0), a result you genuinely
cannot confirm as Final (leave that match unrecorded and note it), or a
pipeline/test failure.

The model itself is **not** retrained here — training data lives in `results.csv`
(refreshed separately via `scripts/refresh_data.py`). This skill only pins
*actual tournament outcomes* so the simulation re-conditions on reality.

## What the pipeline writes

`python -m scripts.run_pipeline` regenerates three files:

- `web/public/predictions.json` — **commit this**
- `web/public/outcomes_sample.json` — **commit this**
- `experiments/ledger.csv` — appended a row; **do NOT commit it** (discard it,
  see step 6). The reference commit `213f19a` excluded it and left the tree clean.

You also hand-edit one source file each run (step 5b):

- `web/src/routes/Landing.tsx` — the home-page "Model update" card — **commit this**

So a correct fixture update produces a diff of exactly **4 files**:
`data/results_2026.json`, `web/public/predictions.json`,
`web/public/outcomes_sample.json`, `web/src/routes/Landing.tsx`.

## Steps

Always work from the repo root and confirm the tree is clean first (`git status`).
If `data/results_2026.json` or the prediction files already have uncommitted
edits, stop and ask the user before continuing.

### 1. Find which matches need recording

Read [data/schedule.json](../../../data/schedule.json) (full 104-match schedule)
and [data/results_2026.json](../../../data/results_2026.json) (already-pinned
results). The matches still needing scores are the schedule entries whose `match`
number is **not** yet in `results_2026.json`. Focus on those whose `date` is on
or before today (`2026-XX-XX`).

List them for the user with match number, date, round, group, and the
`home`/`away` (group rounds) or `top_label`/`bottom_label` (knockout rounds) so
they know exactly which scores to provide.

### 2. Find the results from the ESPN scoreboard (autonomous — do not ask the user)

**Source of truth: the ESPN daily scoreboard.** Do *not* rely on free-text web
search snippets for scores — they routinely hallucinate or recycle a different
day's headlines (e.g. opening-weekend results re-surfaced as "today's"),
including confident-but-wrong scorelines. Always read the structured scoreboard.

For each distinct due date, `WebFetch` the ESPN scoreboard for that date:

```
https://www.espn.com/soccer/scoreboard/_/league/fifa.world/date/YYYYMMDD
```

(e.g. `.../date/20260617`). One fetch lists every match that day with teams,
score, and status. Ask the fetch prompt to return, per match: home team, away
team, score, and whether it is **FT / Final** vs **live/in-progress** vs
**scheduled/not started**. Note that ESPN buckets a match under its **local
kickoff date** — a late US night game can sit on the previous day's board, so if
a due match isn't on today's board, also check the prior day's.

Record **only matches explicitly marked FT/Final.** Skip anything live,
scheduled, or absent — leave it unrecorded and note it in your summary (it gets
picked up next run). **Never guess or infer a score.**

If a Final score looks surprising or the scoreboard is ambiguous, confirm on that
match's ESPN report page or the FIFA match centre before pinning. For knockout
matches (73-104) also capture **who won** and **how** — regulation, extra time,
or penalties; `home_score`/`away_score` record the score at the end of play (90
or 120 min), not the shootout, and the shootout decides `winner` + `decided_by`.

### 3. Append entries to `data/results_2026.json`

Add one object per played match to the `matches` array and set
`meta.updated` to today's date (`YYYY-MM-DD`).

**Group matches** — pin the scoreline. Write `home`/`away` in the **schedule's
orientation** (the pipeline normalises if reversed, but keep it consistent):

```json
{ "match": 9, "home": "Argentina", "away": "Nigeria", "home_score": 3, "away_score": 1 }
```

**Knockout matches (73-104)** — pin the two teams, the score, the `winner`, and
`decided_by` (one of `"regulation"`, `"extra_time"`, `"penalties"`):

```json
{ "match": 73, "home": "Spain", "away": "Croatia", "home_score": 1, "away_score": 1,
  "winner": "Spain", "decided_by": "penalties" }
```

Use canonical team names exactly as they appear in `schedule.json` /
`groups.json` (e.g. "United States", "South Korea", "Bosnia and Herzegovina").
If a name doesn't match, check [data/aliases.json](../../../data/aliases.json).

### 4. Re-run the full pipeline

From the repo root (use a long timeout — the full N=100,000 run takes a few
minutes):

```bash
python -m scripts.run_pipeline
```

Do **not** use `--quick` for a real update — that's the 2,000-sim CI/dev path and
would publish low-resolution probabilities. The script prints the title
favourite and top 5; confirm it finished without error.

### 5. Summarise the swings (for the commit message)

Run the bundled helper, which diffs the freshly-written `predictions.json`
against its committed (HEAD) version:

```bash
python .claude/skills/update-fixtures/swings.py
```

It prints the title race (top 5) and the biggest advance-probability and
title-probability swings — paste the notable ones into the commit body, matching
the style of `213f19a`. Keep these numbers handy; you reuse them in 5b.

### 5b. Refresh the home-page "Model update" card

The landing page shows a hand-written editorial recap of the latest matchday —
the `LATEST_UPDATE` object in [web/src/routes/Landing.tsx](../../../web/src/routes/Landing.tsx)
(search for `const LATEST_UPDATE`). It is **not** auto-generated, so update it
every run to reflect the matchday you just pinned (e.g. replace a "June 14"
update with the "June 16" one). Rewrite all of its fields:

- `date` — the day you're publishing (today, `"Month D, YYYY"`).
- `matchday` — short phrase for how far the tournament has got, e.g.
  `"after matchday 2 (16 matches played)"`.
- `summary` — 1-2 sentences on what moved, including the current title-race top
  (use the top-5 from step 5; keep the leaders honest about whether they've
  played yet).
- `up` / `down` — the biggest advance-prob movers from step 5, as
  `{ team, from, to, note }`. **`from` is the team's pre-tournament prior, `to`
  is its re-conditioned value now.** For teams playing for the first time this
  matchday, the swings.py `old->new` numbers map directly to `from`/`to` (their
  prior was unaffected by earlier groups). `note` is a short human reason
  ("thrashed Tunisia 5-1"). List ~4-5 each side; use canonical team names.

Match the existing array style and keep the figures consistent with what the
pipeline just produced.

### 6. Discard the ledger row, then verify the diff

```bash
git checkout -- experiments/ledger.csv
git status        # expect exactly 4 files: data/results_2026.json, web/public/predictions.json, web/public/outcomes_sample.json, web/src/routes/Landing.tsx
```

If any other file is dirty, investigate before committing.

### 7. Run tests, then commit (and push only if asked)

Per repo convention, run CI's checks locally and confirm green **before any
push**:

```bash
ruff check . && ruff format --check . && WC2026_QUICK=1 pytest -q
cd web && npm run build && cd ..
```

Then commit the 4 files with a message in the established style:

```
data: pin <matchday/desc>, re-condition predictions

<which matches were pinned, with scores>
Full N=100000 re-run. Biggest advance-prob swings: <from swings.py>.
Title race <top, with %s>.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

Since the routine is autonomous, **commit** the 3 files once tests are green
(committing on `main` is fine — the reference commits go straight to `main`).
Push only if the user has configured this routine to push or explicitly asks;
otherwise leave the commit local for the user to review and push.

## Notes

- Score orientation for group games is auto-normalised by `build_schedule`, but
  write the entries in the schedule's `home`/`away` order anyway.
- The `data_snapshot` / model params in `predictions.json.meta` come from
  `results.csv`, not from this update — they won't change unless the training
  data is refreshed.
- If the user only wants to preview impact without committing, run steps 1-5 and
  report, then revert with `git checkout -- data/results_2026.json web/public/`.
