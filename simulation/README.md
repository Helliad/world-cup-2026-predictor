# `simulation/` — the tournament simulator

The showpiece. Plays one full 2026 World Cup correctly, then runs it 100,000
times and aggregates into probabilities with Monte-Carlo standard errors. The
simulator knows nothing about React.

## The 2026 format (implemented exactly)

```
48 teams → 12 groups of 4
        │
        ├─ top 2 of each group ───────────────┐  (24 teams)
        ├─ 8 best of the 12 third-placed teams ┤  (8 teams)
        │                                       ▼
        └────────────────────────▶  32-team knockout bracket
                Round of 32 → Round of 16 → Quarter-finals
                          → Semi-finals → Final
        104 matches total · only 4 thirds + all 12 fourths eliminated
```

## Qualification flow

1. **Groups** (`group_stage.py`). Each group plays its real 2026 schedule (the 6
   fixtures, with co-host home advantage resolved per venue, §8.2). Standings use
   the strict tiebreaker cascade below.
2. **Best thirds** (`third_place.py`). The 12 third-placed teams are ranked; the
   top 8 advance and are slotted into the eight winner-vs-third Round-of-32
   matches.
3. **Knockout** (`knockout.py`). Single elimination, folded to a champion.
4. **One tournament** (`tournament.py`) composes the above and records every
   team's furthest stage. **Monte Carlo** (`monte_carlo.py`) runs N of them
   vectorised and aggregates.

## Tiebreaker cascade (§2.1) — `group_stage.rank_group`

Applied in strict order; this is where most simulator bugs would live, so it
carries the most tests.

1. **Points** (3 win / 1 draw / 0 loss)
2. **Goal difference** (all group matches)
3. **Goals scored**
4. **Head-to-head** among the tied teams: points → GD → GF (restricted to matches
   *between* the tied teams only)
5. *Fair play (cards) — not simulated; collapses into the next step*
6. **Drawing of lots** — a seeded random key that breaks any residual tie
   deterministically (same seed ⇒ same result)

It affects a vanishing fraction of simulations and does not bias results.

## Knockout staging (§6.3) — regulation → ET → penalties

Collapsing a knockout tie into one coin flip systematically under-rewards strong
teams and biases title odds toward parity, so the three stages are explicit:

1. **Regulation (90'):** full Dixon-Coles scoreline matrix at a neutral venue →
   P(a win), P(draw), P(b win).
2. **Extra time (30'):** if drawn, an independent low-scoring period with goal
   rates scaled to ~1/3 of a full match (`30/90`); a stronger side is correctly
   more likely to win it.
3. **Penalties:** if still level, a near coin-flip with a small documented skill
   tilt — `0.5 + (cap−0.5)·tanh(strength gap)`, capped so the stronger side wins
   a shootout at most 55% of the time.

A config flag switches between `staged` (default) and `coinflip` so the effect is
measurable. A closed-form `knockout_win_prob` mirrors the sampled
`play_knockout_match` exactly, which lets the Monte Carlo precompute a 48×48
win-probability matrix instead of sampling every knockout goal.

## Third-place allocation (§2.2) — a release gate

Which **bracket slot** each qualifying third occupies depends on *which groups*
they came from. FIFA publishes a lookup keyed on the combination of qualifying
groups; until the official 2026 table is encoded, this repo uses a **documented
provisional fallback** (`data/third_place_allocation.json`): rank the 8 thirds
1–8 and assign them to the third-slots in bracket order, always skipping a third
whose source group matches that slot's group winner (no same-group Round-of-32
meeting). All predictions are flagged `provisional` until the official table
replaces it.

## Vectorised Monte Carlo (§6.6)

Vectorise across **simulations**, not matches:

- **Group scorelines** are sampled for all N sims at once from each fixture's
  precomputed scoreline CDF (exact, including the τ correction).
- **Standings** are computed with a packed `(points, GD, GF)` primary key; only
  the minority of sims that tie on that key fall back to the per-sim
  `rank_group` cascade — one source of truth for the tiebreakers.
- **Knockout** is resolved by the precomputed win-probability matrix + Bernoulli
  draws; the bracket folds over 5 rounds, vectorised across still-alive sims.

100,000 tournaments run in **~2 seconds** single-process (≈50k sims/s, ~220 MB
peak — see `python -m scripts.benchmark`). Every probability ships with its
standard error ≈ `sqrt(p(1−p)/N)` (±0.1% at N=100k) so a 12.1% vs 11.8% gap is
not over-read. The vectorised path is **cross-checked against the
single-tournament reference** (`tournament.py`) — they agree within Monte-Carlo
error. Title odds are robust to the uncertain co-host home-advantage multiplier
(top teams swing ≤0.1%, top-4 ordering stable — `python -m scripts.sensitivity`).

## Files

| File | Role |
|------|------|
| `group_stage.py` | standings, `tally`, the `rank_group` tiebreaker cascade, `simulate_group`. |
| `third_place.py` | rank 12 thirds → pick 8 → allocate to bracket slots. |
| `knockout.py` | staged ET/penalty resolution, win-prob matrix, scoreline sampler. |
| `tournament.py` | one full tournament (clear reference path). |
| `monte_carlo.py` | vectorised N tournaments → probabilities + SE + what-if sample. |
| `setup.py` | load groups/fixtures/allocation, resolve host advantage to γ. |

## Run

```bash
python -m scripts.run_pipeline --quick   # fast (N=2000)
python -m scripts.run_pipeline           # full (N=100000)
pytest simulation/tests -q               # tiebreaker / third-place / knockout coverage
```
