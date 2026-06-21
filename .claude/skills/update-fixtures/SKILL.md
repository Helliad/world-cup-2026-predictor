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
the user for scores. Find the actual results yourself from Wikipedia's tournament
pages (step 2), pin them, re-run, and commit. The user only reviews the result
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

### 2. Find the results from Wikipedia (autonomous — do not ask the user)

**Source of truth: the Wikipedia tournament pages.** Do *not* rely on free-text
web-search snippets for scores — they routinely hallucinate or recycle a
different day's headlines (e.g. opening-weekend results re-surfaced as "today's"),
including confident-but-wrong scorelines. Only pin scores read from a structured
result table.

Wikipedia is the source because it is **structured and not bot-blocked** — unlike
ESPN and the FIFA match centre, which are Akamai bot-blocked (HTTP 403) from
automated runs (don't depend on them; if you're running locally and ESPN *is*
reachable you may cross-check, but Wikipedia must be sufficient on its own).

> **⚠️ This routine cannot run as a remote/cloud scheduled agent today — run it
> locally.** The remote scheduled-agent sandbox only reaches hosts on a **preset,
> Anthropic-managed egress allowlist**, and `en.wikipedia.org` is not on it, so
> every `WebFetch`/`curl` returns `403 Host not in allowlist: en.wikipedia.org`
> and the run can pin nothing. There is **no self-serve way** to add a domain to
> that allowlist — see Claude Code issue
> [#50146](https://github.com/anthropics/claude-code/issues/50146) (closed as a
> duplicate of the master tracking request). Note the local `settings.json`
> `allowedDomains` key governs only the *local* Bash sandbox, **not** the remote
> routine, so it can't help here. **The only working setup is to run this skill on
> a machine with open egress** (i.e. locally). If you are a cloud run and hit that
> 403, stop and report it as an environment failure (see the end of this step) —
> do not print an all-clear.

Group-stage matches live on the per-group articles, knockouts on the knockout page:

```
https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_Group_A   (… through Group L)
https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_knockout_stage
```

There is **no** single combined results page — `..._group_stage` 404s, and the
main `2026_FIFA_World_Cup` article shows only standings, not per-match scores.
Use the per-group pages.

**⚠️ Wikipedia's group LETTERS do not match ours, and you can't know the mapping
in advance.** Our internal letters (`data/groups.json`) are reconstructed; only
the host groups align (Wikipedia A=Mexico, B=Canada, D=USA). For every other
group, *our* Group X is some *other* Wikipedia letter (e.g. this tournament our
Group F = Wikipedia Group E, our Group G = Wikipedia Group H). Our group-stage
match **numbers** likewise need not equal Wikipedia's 1–72 labels (knockout
73–104 do match). So **identify groups by their teams, never by letter:**

1. From `data/groups.json`, list the distinct *our*-groups your due matches span,
   with the 4 teams in each.
2. `WebFetch` group pages, asking each prompt to return **(a) the 4 teams in that
   group and (b) every match: date, both teams, and final score or "not yet
   played".** The returned roster is what tells you which of your groups the page
   actually is.
3. Match each due fixture to its result by the **two team names** (orientation-
   independent — ignore Wikipedia's letter *and* its match number), then pin it
   under **our** schedule's match number.

Because the letter won't tell you in advance which page holds a group, expect to
fetch a few group pages whose rosters don't contain your teams and discard them —
that's normal, not an error. (Host-group due matches you can target directly:
our A/B/D = Wikipedia A/B/D.) Per match, capture both teams, the final score, the
date, and whether it is **played (has a score)** or **not yet played**.

Record **only matches Wikipedia shows as played with a final score.** Skip
anything shown as "not yet played" / scoreless — leave it unrecorded and note it
in your summary (it gets picked up next run, once Wikipedia reflects it). **Never
guess or infer a score.**

For knockout matches (73–104) also capture **who won** and **how** — the
knockout-stage page annotates extra time ("a.e.t.") and penalty shootouts
("(p)" / "X–Y on penalties"). `home_score`/`away_score` record the score at the
end of play (90 or 120 min), not the shootout; the shootout decides `winner` +
`decided_by` (`"regulation"` / `"extra_time"` / `"penalties"`).

If *no* structured source is reachable at all (e.g. Wikipedia also returns an
error), that is an environment failure, **not** a "no finals played" day — make
no commit and report the access failure rather than printing the all-clear.

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
