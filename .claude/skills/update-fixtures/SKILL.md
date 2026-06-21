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
the user for scores. Find the actual results yourself from the openfootball
results feed (step 2), pin them, re-run, and commit. The user only reviews the result
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

### 2. Pull the results with the helper (autonomous — do not ask the user)

**Source of truth: the [openfootball/worldcup.json](https://github.com/openfootball/worldcup.json)
feed** — a public-domain, structured JSON results file on GitHub
(`raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json`),
refreshed ~once a day during the tournament. It is the source because it is
(a) **structured** — plain JSON, so no HTML scraping and no group-letter guessing,
and (b) on `raw.githubusercontent.com`, a GitHub host that the cloud sandbox's
egress allowlist permits. Do *not* pin scores from free-text web-search snippets —
they hallucinate and recycle old headlines.

Run the bundled helper from the repo root (via the `wc26` env):

```bash
python .claude/skills/update-fixtures/fetch_results.py        # --today YYYY-MM-DD to override the cutoff
```

It fetches the feed and prints two sections:

- **VERIFY** — re-checks every already-pinned result against openfootball. It must
  report `N pinned results match openfootball; 0 mismatches`. A **MISMATCH** means
  either a name-mapping/orientation bug or a score openfootball has since
  corrected — **stop and investigate** before doing anything else.
- **DUE & UNPINNED** — for each schedule match due on/before today: a ready-to-
  paste `results_2026.json` line when openfootball has a final score, or a
  `# match N … unplayed in openfootball — skip` comment when it doesn't.

The helper exits `0` when nothing needs a human, `2` when something does (a verify
mismatch, or a played **knockout** that needs hand-completion), and `3` if the
feed is unreachable. Pin **only** the matches it emits as ready-to-paste lines —
**never guess or infer a score.** Leave unplayed matches for the next run (note
any you skipped); because openfootball updates only ~once/day, a match played late
may not appear until the following run.

Team names are reconciled via [data/aliases.json](../../../data/aliases.json) —
openfootball uses a few alternates (e.g. `USA`, `Bosnia & Herzegovina`) but is
otherwise canonical, and matching is by canonical team **pair**, so openfootball's
own group labels and match order never matter. If a future opponent's name fails
to resolve it will surface in the helper's output as unmatched — add the alias.

**Knockout matches (73–104).** openfootball carries placeholder slots (`W73`,
`1A`, `3A/B/C/D/F`) until a tie is played, then fills in the real teams +
`score.ft`. The helper prints knockout results with any `et`/`p` (extra-time /
penalty) fields it finds but **does not auto-emit a pin line** — set `winner` +
`decided_by` (`"regulation"` / `"extra_time"` / `"penalties"`) **by hand**:
`home_score`/`away_score` record the score at the end of play (90/120 min), not
the shootout, and the shootout decides the winner.

> **Cloud reachability — the next scheduled run is the real test.**
> `raw.githubusercontent.com` is on the documented cloud-sandbox allowlist and was
> reachable from a remote-agent probe, so a scheduled cloud run *should* now work
> (Wikipedia, the old source, never was — it isn't on the allowlist). But the
> scheduled-routine sandbox has historically been tighter than the docs (an
> earlier run saw `api.github.com` return `403 Host not in allowlist`), so treat
> the **first cloud run on this source as the confirmation**: if the helper exits
> `3` on a `403 Host not in allowlist`, the routine still can't reach GitHub —
> that's an environment failure (make no commit, report it) and you must run the
> skill **locally** (open egress always works) until it's resolved. There is no
> self-serve way to extend the routine allowlist (Claude Code issue
> [#50146](https://github.com/anthropics/claude-code/issues/50146)).

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

  **Getting the prior for 2nd/3rd-game teams.** From matchday 2 on, swings.py's
  `old` already includes earlier conditioning, so it is **not** the pre-tournament
  prior — don't use it as `from`. Read the true prior straight from the baseline
  `predictions.json` (the version from just before the first result was ever
  pinned, i.e. the parent of reference commit `213f19a`):

  ```bash
  git show 213f19a^:web/public/predictions.json > _pre_pred.json   # baseline, no results conditioned
  # `from` = teams[].p_advance * 100 from _pre_pred.json (round to int)
  # `to`   = teams[].p_advance * 100 from the freshly-written web/public/predictions.json
  rm _pre_pred.json
  ```

  (Write the temp file *inside the repo dir*, not `/tmp` — on Windows the conda
  Python can't see `/tmp`.) Classify `up`/`down` by the **prior→now** direction:
  a team that won game 1 then lost game 2 can still be net-up versus its prior, so
  it belongs in `up` with an honest `note` about the loss — keep the arrow and the
  number consistent.

Match the existing array style and keep the figures consistent with what the
pipeline just produced.

### 6. Verify the diff (leave the ledger row alone — do NOT `git checkout` it)

```bash
git status        # expect 5 dirty files: the 4 below + experiments/ledger.csv
```

The pipeline appended one throwaway row to `experiments/ledger.csv`. **Do not try
to discard it with `git checkout -- experiments/ledger.csv`** — the harness
permission classifier blocks that command (it reverts a pre-existing tracked file
you didn't name), so a scheduled/autonomous run errors out there. Instead just
**never stage it**: in step 7 you `git add` the 4 intended files by name, which
leaves the ledger row out of the commit. The dirty ledger row is harmless — in a
cloud run the checkout is ephemeral and thrown away; locally the user can discard
it themselves.

The 4 files that DO get committed:
`data/results_2026.json`, `web/public/predictions.json`,
`web/public/outcomes_sample.json`, `web/src/routes/Landing.tsx`.

If any file *other* than those 4 + `experiments/ledger.csv` is dirty, investigate
before committing.

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
