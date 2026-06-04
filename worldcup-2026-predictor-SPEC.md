# World Cup 2026 Predictor & Simulator — Technical Specification

**Status:** Build-ready specification (single source of truth)
**Audience:** Developer building the open-source repository
**Goal:** A documented, marketable open-source project that (1) predicts match scorelines with a real statistical model fit on historical data and properly evaluated, (2) simulates the full 48-team 2026 World Cup tens of thousands of times, and (3) presents results through a polished, accessible, interactive React product. Built to demonstrate clean, well-documented, rigorous engineering for a public GitHub audience.

---

## 1. Project at a glance

| Item | Decision |
|------|----------|
| Repo name | `worldcup-2026-predictor` |
| License | MIT |
| Model stack | Python 3.11+, NumPy, pandas, SciPy |
| Simulation stack | Python (NumPy-vectorised) |
| Frontend stack | React + Vite, TypeScript, Tailwind CSS |
| Data flow | Python pipeline produces a static `predictions.json` consumed by the React app |
| Hosting target | GitHub Pages (static site) for the demo; repo itself for the code |
| CI | GitHub Actions: lint + tests on every push |

The three layers are deliberately decoupled. The model knows nothing about tournaments; the simulator knows nothing about React; the frontend reads a static JSON artifact and never calls Python at runtime. This separation is what keeps each module independently documentable and testable.

### 1.1 Suggested build order

1. **Data + model first.** Get `results.csv` in, fit Dixon-Coles, build the evaluation harness (§4.6) and confirm the model clears its acceptance gates before building anything on top of it. Commit `params.json`.
2. **Simulator core.** `group_stage` → `third_place` → `knockout` → `tournament`, each with its tests. This is where to spend the most care.
3. **Monte Carlo + pipeline.** Produce a real `predictions.json` with a run manifest.
4. **Frontend.** Title Race → groups → bracket → team detail → "what if".
5. **Docs + CI polish.** Write the READMEs alongside, not at the end; wire up Actions; deploy to Pages.
6. **Launch loop.** Automate the matchday re-run.

### 1.2 Minimum launch scope vs. enhancements

Must-haves for a credible v1.0 launch: the evaluation framework (§4.6), the frontend product spec (§7), and replacing the provisional third-place allocation with the official table (§8.1, a release gate). Defer if needed: the random-walk strength option (§4.5), multi-process parallelism (§6.6), and the sensitivity grid (§8.2) are valuable but post-launch.

---

## 2. The 2026 tournament format (the thing being modelled)

This is the source of the project's complexity and must be implemented exactly. Get this wrong and every probability is wrong.

- **48 teams**, divided into **12 groups of 4** (Groups A through L).
- Each team plays the other three in its group once: **3 matches each, 72 group matches total**, round-robin.
- **Top 2 of each group advance** automatically → 24 teams.
- **The 8 best third-placed teams** (out of 12) also advance → completing a **32-team knockout bracket**.
- This means only 4 of the 12 third-place teams are eliminated, plus all 12 fourth-place teams.
- Knockout is single elimination: **Round of 32 → Round of 16 → Quarter-finals → Semi-finals → Final** (plus a third-place playoff).
- Knockout matches level after 90 minutes go to **extra time, then penalties**.
- Total tournament: **104 matches**, hosted across the USA, Canada and Mexico.

### 2.1 Group-stage standings tiebreakers (apply in strict order)

1. Points (3 win / 1 draw / 0 loss)
2. Goal difference (across all group matches)
3. Goals scored
4. Head-to-head: points, then goal difference, then goals scored among the tied teams
5. Fair play ranking (fewer cards) — *see note below*
6. Drawing of lots (random)

> **Implementation note on fair play:** the simulator does not generate cards, so steps 5–6 collapse into a deterministic-but-arbitrary tiebreak. Use a seeded random draw for step 6 and skip step 5 (document this clearly). It affects a vanishingly small fraction of simulations and does not bias results.

### 2.2 Third-place ranking and bracket allocation

After all 72 group matches, collect the 12 third-placed teams into a single table and rank them by the same metrics (points → GD → goals scored → drawing of lots). The top 8 advance. The **specific bracket slot** each qualifying third-place team occupies depends on *which groups* they came from — FIFA publishes a lookup table mapping the set of qualifying groups to bracket positions (the same mechanism Euro 2016/2020/2024 used). Implement this as a lookup keyed on the sorted combination of the 8 source groups, stored in `data/third_place_allocation.json`.

> **Release gate:** obtain FIFA's official "combination of third-placed teams" allocation table for 2026 and encode it. Until it is confirmed, implement a documented provisional fallback (rank third-place teams 1–8 and seed them against group winners in a fixed order), label all predictions `provisional` in `meta` and the UI, and treat replacing it with the official table as a gate before any "final" launch. See §8.1.

---

## 3. Repository structure

```
worldcup-2026-predictor/
├── README.md                  # hero: what it is, demo GIF, quickstart, live metrics + odds table
├── LICENSE                    # MIT
├── CONTRIBUTING.md            # how to run, test, submit PRs
├── config.yaml                # single source of every tunable knob (§6.7)
├── requirements.txt           # pinned Python deps + lockfile
├── .github/
│   └── workflows/ci.yml       # lint (ruff) + pytest on push/PR
├── data/
│   ├── results.csv            # historical international matches (sourced, see §5)
│   ├── groups.json            # the 12 official 2026 groups
│   ├── third_place_allocation.json  # FIFA bracket-slot lookup (or provisional)
│   ├── aliases.json           # team-name reconciliation table
│   └── README.md              # provenance, schema, licensing, refresh + validation steps
├── model/
│   ├── __init__.py
│   ├── dixon_coles.py         # the model: fit() + predict_scoreline_matrix()
│   ├── ratings.py             # hierarchical priors / recency weighting helpers
│   ├── train.py               # CLI: read results.csv -> fit -> save params
│   ├── params.json            # serialised fitted parameters (committed artifact)
│   ├── evaluation/            # metrics, baselines, calibration, backtest
│   │   ├── metrics.py         # RPS, Brier, log-loss, ECE
│   │   ├── baselines.py       # uniform, base-rate, double-Poisson, bookmaker
│   │   ├── backtest.py        # walk-forward harness
│   │   └── calibrate.py       # temperature / isotonic post-hoc calibration
│   ├── evaluate.py            # CLI: emit metrics report + reliability plots
│   ├── tests/
│   └── README.md              # the math, the evaluation framework, worked example
├── simulation/
│   ├── __init__.py
│   ├── group_stage.py         # standings + tiebreaker cascade
│   ├── third_place.py         # rank 12 -> pick 8 -> slot into bracket
│   ├── knockout.py            # single-elim incl. staged ET/penalties
│   ├── tournament.py          # one full tournament from start to champion
│   ├── monte_carlo.py         # run N tournaments, aggregate probabilities + SE
│   ├── tests/
│   └── README.md              # qualification flow diagram + algorithm notes
├── scripts/
│   ├── run_pipeline.py        # params + groups -> simulate -> predictions.json
│   ├── refresh_data.py        # pull + validate latest data snapshot (§8.3)
│   ├── benchmark.py           # wall-clock + memory for N in {1k,10k,100k}
│   └── sensitivity.py         # re-run across assumption grid (§8.2)
├── experiments/
│   └── ledger.csv             # per-run: config hash, metrics, notes (§6.7)
└── web/
    ├── package.json
    ├── index.html
    ├── public/
    │   ├── predictions.json   # the artifact the pipeline emits
    │   └── outcomes_sample.bin # compact encoded sims for "what if" (§6.5)
    ├── src/
    │   ├── App.tsx
    │   ├── routes/            # /, /groups, /bracket, /team/:id
    │   ├── store/             # single state store + memoized selectors
    │   ├── components/        # typed component system (§7.7)
    │   ├── lib/recompute.ts   # client-side conditional-probability recompute
    │   └── types.ts
    └── README.md              # run, build, deploy, design tokens, "what if" internals
```

---

## 4. The model (`model/`)

### 4.1 Why Dixon-Coles

Football scores are well-approximated by a Poisson process: model the goals each side scores as Poisson-distributed with a mean (its expected goals for that match) derived from the attacking strength of the team and the defensive weakness of the opponent. The classic refinement is **Dixon & Coles (1997)**, which adds two things a plain double-Poisson misses:

1. **A low-score dependence correction (the τ / rho term)** that fixes the known empirical fact that 0-0, 1-0, 0-1 and 1-1 occur at rates plain Poisson gets wrong.
2. **Time-weighting**, down-weighting older matches so current form matters more than 2005 results.

This is the right choice because it is genuinely respected (not a toy), it is explainable in a README with real equations, and it outputs a **full scoreline probability matrix** — which the simulator needs and which makes the frontend far richer than a bare win/draw/loss number.

### 4.2 Parameterisation

For each team *i*: an attack strength `α_i` and a defence strength `β_i`. Plus a global home-advantage term `γ`. For a match where home team *i* plays away team *j*:

```
λ (home expected goals) = exp(α_i + β_j + γ)
μ (away expected goals) = exp(α_j + β_i)
```

The probability of an exact scoreline (x home, y away):

```
P(x, y) = τ(x, y; λ, μ, ρ) · Poisson(x; λ) · Poisson(y; μ)
```

where `τ` is the Dixon-Coles low-score adjustment (a function of ρ that nudges the four lowest scorelines). Fit all parameters by **maximum likelihood** with `scipy.optimize.minimize`, applying a per-match time-decay weight `w_t = exp(-ξ · Δt)` where `Δt` is the age of the match in days and `ξ` is a tuned decay rate (§4.6.4).

Constraint: fix the mean of the attack parameters (`sum(α) = 0`) for identifiability.

### 4.3 Public API of the model

```python
class DixonColesModel:
    def fit(self, matches: pd.DataFrame, xi: float, l2: float) -> "DixonColesModel": ...
    def predict_scoreline_matrix(self, home: str, away: str, max_goals: int = 10) -> np.ndarray:
        """Return an (max_goals+1, max_goals+1) matrix P where P[x, y] = P(home x : away y)."""
    def predict_outcome(self, home: str, away: str) -> dict:
        """Collapse the matrix into {'home_win', 'draw', 'away_win', 'exp_home', 'exp_away'}."""
    def save(self, path: str) -> None: ...
    @classmethod
    def load(cls, path: str) -> "DixonColesModel": ...
```

The simulator needs `predict_scoreline_matrix` (sample a scoreline) for group games, and a derived win-probability for knockout games (with draw mass resolved through the staged ET/penalty logic — see §6.4).

### 4.4 Regularization, sparsity, and new teams

These are first-class modelling decisions, not afterthoughts — several 2026 debutants have thin international records and must not get absurd parameters from a handful of matches.

- **L2 penalty (ridge)** on attack/defense parameters, shrinking teams toward the league-average baseline. Tune the penalty weight in the walk-forward loop (§4.6.4). This stabilizes parameters.
- **Hierarchical shrinkage / partial pooling.** Treat each team's strength as drawn from a confederation-level prior. Teams with few matches get pulled strongly toward their confederation mean; teams with many matches dominate their own data. This is the principled fix for sparsity.
- **Minimum-data guardrail.** Below a match-count threshold (e.g. < 15 recent competitive matches), widen the team's effective uncertainty and lean on the prior. Surface this in `predictions.json` as a `data_confidence` flag per team so the UI can label low-confidence teams honestly (§7).
- **Cold-start seeding.** Initialize a new team's prior from its confederation strength and, where available, an external rating (Elo-style or FIFA ranking) as a soft anchor. Document the anchor as a prior, not a label.
- **Parameter stability reporting.** Re-fit on adjacent time windows and plot how each team's α/β moves. Large unexplained swings indicate over-fitting or sparse data and should be visible, not buried.

### 4.5 Non-stationarity

Team strength drifts over time, so the model must not treat 2010 and 2025 equally.

- Time-decay weighting is the first-line defense; `ξ` is a tuned hyperparameter (§4.6.4), not a guess.
- Report the **half-life** implied by the chosen `ξ` in human terms ("matches lose half their weight after ~N months") so the choice is interpretable.
- *(Enhancement, post-launch.)* Optionally evaluate a slow random-walk on team strength, but only add it if it beats time-decay on the walk-forward RPS. Do not add it speculatively.

### 4.6 Evaluation framework (a hard requirement)

A model is not "done" when it fits; it is done when it clears its acceptance gates on held-out data. This module is mandatory.

#### 4.6.1 Metrics — report all three, optimize on RPS

Match prediction is a 3-outcome ordered problem (home / draw / away).

- **Ranked Probability Score (RPS)** — the field-standard proper scoring rule for football because it respects outcome ordering (a draw is "closer" to a home win than an away win is). Lower is better. Primary metric; tune hyperparameters against it.
- **Brier score (multiclass)** — proper, ordering-insensitive. Reported as a cross-check.
- **Log loss / ignorance score** — punishes overconfidence hardest; catches miscalibration RPS can hide.

Report all three. There is genuine academic disagreement about whether RPS's distance-sensitivity is a virtue, so reporting the trio is both more defensible and itself a mark of rigor. RPS for a single match:

```
RPS = (1 / (r - 1)) * Σ_{i=1}^{r-1} ( Σ_{j=1}^{i} (p_j - e_j) )²
```

where `r = 3`, `p_j` are cumulative predicted probabilities, `e_j` cumulative actuals. Average over all test matches.

#### 4.6.2 Acceptance thresholds

Published strong models on international/club match prediction land around **RPS 0.205–0.210 with ~51–52% top-pick accuracy**. Tiered, falsifiable targets:

| Tier | RPS (test) | Top-pick accuracy | Interpretation |
|------|-----------|-------------------|----------------|
| Floor (must beat to ship) | < 0.230 | > 0.47 | Beats naive baselines |
| Target | ≤ 0.215 | ≥ 0.50 | Competitive with good public models |
| Stretch | ≤ 0.208 | ≥ 0.52 | At/near published state of the art |

These are *match-level* targets on held-out matches, not tournament-outcome accuracy (which is unfalsifiable on a single tournament — see §9.3).

#### 4.6.3 Mandatory baselines

Implement and report all of these on the same test set:

1. **Uniform** — 1/3 each. Absolute floor.
2. **Home/draw/away base rates** — historical marginals. Surprisingly hard to beat.
3. **Plain double-Poisson** (no DC correction, no time decay) — proves the refinements earn their complexity.
4. **Bookmaker-implied probabilities** (de-margined odds) where available — an aspirational ceiling, not a baseline to beat.

If Dixon-Coles + time-decay does not beat plain double-Poisson on RPS, that is a finding to report honestly, not hide.

#### 4.6.4 Validation protocol — temporal, never random

Football strength is non-stationary, so **random k-fold CV leaks the future into the past and is invalid here.**

- **Rolling-origin (walk-forward) backtest.** Train on all matches up to date *T*, predict the next block, advance *T*, repeat. Mirrors real use.
- Report metrics per block and pooled, so degradation over time is visible.
- Hold out a final untouched block (most recent 6–12 months, including recent tournaments) as a true test set never seen during hyperparameter search.
- Tune `ξ`, the L2 weight, and any calibration *inside* the walk-forward loop, never on the final test block.

#### 4.6.5 Calibration

A model can rank well and still be over/under-confident, and the Monte Carlo compounds per-match probabilities across seven rounds, so small biases blow up.

- **Reliability diagrams** per outcome class (predicted bucket vs observed frequency).
- **Expected Calibration Error (ECE)** as a single reported number.
- If miscalibrated, apply and document a post-hoc step (temperature scaling or isotonic regression fit on a validation block, never the test block).

#### 4.6.6 Deliverable

`model/evaluation/` plus an `evaluate.py` CLI emitting a metrics report (JSON + human-readable markdown table with reliability plots as PNGs). CI runs a quick version; the full backtest is a documented scheduled/manual run. The README publishes current numbers and baselines so anyone can see exactly how good the model is.

### 4.7 Tests for the model

- Every scoreline matrix sums to ~1.0 (within tolerance, after truncation at `max_goals`).
- `predict_outcome` probabilities sum to 1.0.
- A clearly stronger team gets a higher win probability than the reverse fixture.
- Fitting is deterministic given a fixed dataset and seed.
- A sparse/new team is pulled toward its confederation prior (assert its parameters sit within a sane band).

---

## 5. Data (`data/`)

### 5.1 Historical results

Primary source: the **`martj42/international_results`** dataset (GitHub, mirrored on Kaggle) — ~49,000 men's full international results from 1872 to present, covering World Cups through friendlies, continuously updated via pull requests. It is the de-facto standard open dataset for this work, which aids credibility and reproducibility.

Schema (`results.csv`):

| column | meaning |
|--------|---------|
| `date` | match date (YYYY-MM-DD) |
| `home_team` / `away_team` | team names (current canonical names) |
| `home_score` / `away_score` | full-time goals |
| `tournament` | competition (World Cup, friendly, etc.) |
| `city` / `country` | venue |
| `neutral` | bool, whether played at a neutral venue |

### 5.2 Filtering choices (document these)

- Rely on time-decay weighting (tuned, §4.6.4) rather than a hard training-window cutoff, or combine both.
- Optionally up-weight competitive matches vs friendlies.
- Map team-name mismatches between the results dataset and the 2026 group list via `data/aliases.json`.

### 5.3 Groups

`groups.json` encodes the 12 official groups from the final draw:

```json
{
  "A": ["Mexico", "...", "...", "..."],
  "B": ["Canada", "...", "...", "..."],
  "...": []
}
```

Keep a `provisional` boolean so the app can label predictions accordingly if anything is unsettled (e.g. intercontinental playoff slots — represent these as explicit placeholders, never a silently guessed team).

---

## 6. The simulator (`simulation/`)

The showpiece. Run one full tournament correctly, then run it N times and aggregate.

### 6.1 One group (`group_stage.py`)

```python
def simulate_group(teams: list[str], model, rng) -> list[TeamResult]:
    # play all 6 matches (round-robin of 4)
    # accumulate points, goals for, goals against, head-to-head records
    # return teams sorted by the tiebreaker cascade (§2.1)
```

Each match: sample a scoreline from the model using the rng. Record full results — head-to-head needs the actual scores, not just points.

### 6.2 Third place (`third_place.py`)

```python
def select_best_thirds(all_groups: dict[str, list[TeamResult]], rng) -> dict[str, str]:
    # gather the 12 third-placed teams
    # rank by points -> GD -> GF -> lots
    # take top 8
    # map the sorted set of their 8 source-group letters to bracket slots
    #   via data/third_place_allocation.json
    # return {bracket_slot: team_name}
```

This is where most bugs will live; it deserves the most tests.

### 6.3 Knockout match resolution (`knockout.py`) — regulation → ET → penalties

Specify the three stages explicitly. Collapsing them into one coin flip systematically under-rewards strong teams and biases title odds toward parity.

```python
def play_knockout_match(team_a, team_b, model, rng) -> str:
    # 1. Regulation (90'): full scoreline matrix -> P(a win), P(draw), P(b win)
    # 2. If drawn -> extra time (30'): independent low-scoring period,
    #    goal rates scaled to ~1/3 of a full match (30/90), reuse same lambda/mu,
    #    re-sample a scoreline. Stronger side is correctly more likely to win.
    # 3. If still level -> penalties: near coin-flip with a small documented
    #    skill tilt (default 50/50; optional logistic-in-strength-gap, capped ~55/45).
    # return winner
```

Provide a config flag to switch between "staged" (default) and "simple coin-flip" so the effect is measurable.

### 6.4 Knockout bracket

Single elimination: build Round-of-32 pairings from group winners, runners-up, and the 8 third-place teams per the allocation map (§2.2), then fold the bracket in halves until a champion remains. Assert no match ends in a draw.

### 6.5 One tournament (`tournament.py`)

Compose: simulate all 12 groups → select third places → seed the bracket → play to the final. Return, for every one of the 48 teams, the furthest stage reached plus the champion. For the "what if" feature, also emit a compact integer-encoded record of the bracket outcome (team indices per slot).

### 6.6 Monte Carlo (`monte_carlo.py`) — compute, memory, parallelism

```python
def run_simulations(model, groups, allocation, n: int, seed: int) -> SimResults:
    # run n independent tournaments
    # per team: P(advance), P(reach R16/QF/SF/Final), P(win) + standard errors
    # store a compact sample of bracket outcomes for the "what if" feature
    # return aggregated probabilities + manifest metadata
```

- **Vectorize across simulations, not matches.** Represent all N simulations as NumPy arrays and play each fixture for all N at once by drawing N Poisson samples per side. This turns 104 matches × N into ~104 vectorized ops. Precompute each fixture's λ/μ once; only the sampling is per-simulation.
- The knockout bracket is data-dependent per simulation, so loop over the 5 rounds while keeping per-round resolution vectorized across still-alive simulations.
- **Memory:** group-stage state for N=100k is a few arrays of 48·N floats (~tens of MB). For "what if," store a compact integer-encoded sample (5–10k sims) rather than all 100k brackets verbatim; target `predictions.json` + outcomes sample < ~2–3 MB so it loads fast on mobile.
- **Parallelism:** default single-process vectorized NumPy is enough for 100k and stays deterministic. For larger runs, parallelize across independent seeded chunks via `multiprocessing`, each with its own `Generator` derived from a master `SeedSequence`; concatenate tallies. Aggregate determinism requires fixed chunk count + master seed. *(Enhancement, post-launch.)*
- **Monte Carlo error:** every probability has a standard error ≈ `sqrt(p(1-p)/N)`. Publish it (e.g. "±X% at N=100k") so a 12.1% vs 11.8% gap is not over-read. Both rigor and good epistemics for the social audience.
- Provide a `--quick` flag (e.g. N=2000) for fast iteration and CI.

### 6.7 Configuration, reproducibility, and experiment tracking

- **Single config file** (`config.yaml`) holds every knob: training window/decay `ξ`, L2 weight, host-advantage multiplier, N, master seed, penalty cap, calibration method. The pipeline reads only from this — no magic numbers in code.
- **Run manifest.** Every run writes into `predictions.json.meta`: git commit hash, config hash, data snapshot date + row count + checksum, library versions, timestamp, N, seed. Anyone can reproduce or diff two runs.
- **Deterministic seeding** end-to-end via `numpy.random.SeedSequence` spawned to fit, simulation, and sampling.
- **Experiment ledger.** `experiments/ledger.csv` records, per run: config hash, the three eval metrics, notes. A committed ledger is enough for an open repo and is itself documentation; the manifest makes wiring up MLflow/W&B trivial later, but it is not required.
- **Pinned dependencies** (exact versions + lockfile). Commit `params.json` and a fixed data snapshot so a clean clone reproduces published numbers exactly.

### 6.8 Tests for the simulator (the credibility centrepiece)

- **Tiebreaker edge cases**, hand-built: three teams level on points resolved by GD; a head-to-head triangle; an exact tie forced to drawing-of-lots (assert determinism under a fixed seed).
- **Third-place selection:** construct 12 known third-place records, assert the right 8 advance and land in the right slots.
- **Knockout invariants:** no draws ever returned; exactly one champion; every round halves the field.
- **Knockout staging:** a much stronger team wins a knockout tie more often than a pure coin flip but less often than a single regulation match (draws inject variance); shootout resolution respects the documented cap.
- **Probability sanity:** stage probabilities are monotonic (P(SF) ≤ P(QF) ≤ …) and all 48 teams' "win" probabilities sum to ~1.0.

---

## 7. The frontend (`web/`) — a product, not a feature list

A static React + Vite + TypeScript app, Tailwind for styling, reading `public/predictions.json`. No backend. It should feel like a focused, editorial sports-analytics product, because sharing is the growth engine.

### 7.1 Positioning and design language

- **Positioning:** a polished, authoritative *predictions* microsite — closer to a major outlet's interactive than an internal dashboard. Screenshot-worthy by design.
- **Design language:** clean, data-forward, high-contrast, confident typographic hierarchy. Restrained color used to *encode meaning*, not decorate — one accent for "probability/positive," a neutral palette otherwise. Dark mode supported. No skeuomorphic stadium kitsch.

### 7.2 Information architecture and user journey

Single-page app, three primary views in a persistent top nav, plus a team drill-down and a cross-cutting overlay:

1. **Title Race (landing/default):** the headline — top contenders with championship probability, a visual ranking, and the tournament's marquee numbers. First paint must show this without interaction; it is the share target.
2. **Groups:** all 12 groups, each a compact table with advance probabilities; tap to expand standings detail.
3. **Bracket:** the 32-team knockout tree with most-likely occupants and conditional odds; horizontally scrollable on mobile.
4. **Team detail (drill-down):** per-team stage-by-stage probabilities, projected path, strength parameters, and the `data_confidence` flag (§4.4). Reached by tapping any team anywhere.
5. **"What If" mode:** a cross-cutting overlay (not a page) to pin outcomes and watch every view recompute (§7.6).

Primary journey: land on Title Race → recognize a team → tap to Team detail or jump to Bracket → toggle a "what if" → share a screenshot.

### 7.3 Routing and state

- **Routing:** lightweight client routing (`react-router`) with real URLs per view (`/`, `/groups`, `/bracket`, `/team/:id`) so views are shareable and back/forward works. Encode active "what if" conditions in the URL query string so a forced-scenario view is itself a shareable link — a strong growth feature.
- **State:** a single top-level store (React context + reducer, or Zustand — not Redux). Holds loaded predictions, active view, selected team, pinned "what if" conditions. Derived probabilities come from memoized selectors, never stored redundantly.
- **Data loading:** fetch `predictions.json` once at start; branded loading state; render progressively (Title Race first); cache in memory for the session.

### 7.4 Visualization standards

- **Charting:** one consistent approach — Recharts for standard charts, hand-rolled SVG/flex for the bespoke bracket and probability bars. Do not mix multiple chart libraries.
- **Probability encoding:** horizontal bars with the numeric percentage always shown as text beside the bar (accessibility + screenshot legibility). Consistent 0–100% scale across the app. Color intensity may reinforce magnitude but never replaces the number.
- **No misleading visuals:** bars start at zero; no 3D; round percentages consistently (one decimal); show the Monte Carlo error note (§6.6) somewhere honest.

### 7.5 Responsiveness, accessibility, motion

- **Mobile-first, breakpoint-tested.** The two hard mobile problems: the Title Race table collapses to a stacked card list under a breakpoint; the bracket becomes horizontally scrollable with a sticky round-label header. Both usable one-handed.
- **Accessibility (required):** semantic HTML, WCAG AA contrast, full keyboard navigation, focus states, ARIA labels on controls and on probability bars (the percentage is announced, not just shown), and respect for `prefers-reduced-motion`.
- **Motion principles:** motion communicates change, never decorates. It earns its keep on the **"what if" recompute** — bars grow/shrink and numbers tween so the user sees cause and effect. Fast (~300–400ms), disabled under reduced-motion.
- **Loading / empty / error states** explicitly designed for: initial load, a failed `predictions.json` fetch, and a "what if" combination with too few matching simulations (show uncertainty, not a fake precise number).

### 7.6 "What if" interaction model (the signature feature)

- Pin conditions from any view (tap a team in the bracket → "assume they win this tie"; tap a group → "assume X tops it").
- The client filters the stored simulation sample (§6.6) to the matching subset and recomputes all displayed probabilities as conditional frequencies, with transitions. Exact conditional probabilities, instant, no model in the browser.
- A persistent, visible "conditions" chip bar shows what is pinned, each removable; a "reset" clears all.
- **Honesty guardrail:** if the matching subset falls below a sample threshold (e.g. < 200 sims), show a clear low-confidence warning instead of a falsely precise number, and suggest removing a condition.

### 7.7 Component system

A small, documented, typed component library: `Bar`, `ProbabilityValue`, `TeamRow`, `GroupTable`, `BracketSlot`, `ConditionChip`, `StatCallout`, `ViewNav`. Each with defined props and states. Define a typography scale (5–6 step modular scale) and semantic color tokens (`--surface`, `--text`, `--accent`, `--prob-fill`, `--warning`) up front in `web/README.md` so the look stays consistent and contributors do not improvise.

---

## 8. Pipeline, home advantage, governance, provisional logic

### 8.1 Pipeline (`scripts/run_pipeline.py`)

One command, end to end:

```
results.csv ──▶ model.train ──▶ params.json
                                    │
groups.json ───────────────────────┼──▶ monte_carlo.run_simulations ──▶ predictions.json
third_place_allocation.json ────────┘                                         │
                                                              web/public/predictions.json
```

`predictions.json` schema (the contract between Python and React):

```json
{
  "meta": { "n_simulations": 100000, "seed": 42, "model_version": "1.0",
            "data_snapshot": "2026-05-30", "git_commit": "...", "config_hash": "...",
            "data_checksum": "...", "provisional": false, "generated_at": "..." },
  "groups": {
    "A": [ { "team": "Mexico", "p_advance": 0.78, "exp_points": 6.1 } ]
  },
  "teams": [
    { "team": "Brazil", "group": "G", "data_confidence": "high",
      "p_advance": 0.93, "p_r16": 0.74, "p_qf": 0.51,
      "p_sf": 0.31, "p_final": 0.19, "p_win": 0.12, "se_win": 0.001 }
  ],
  "matchups": {
    "Brazil|Argentina": { "home_win": 0.41, "draw": 0.27, "away_win": 0.32 }
  }
}
```

Keep `matchups` small — only pairings the UI needs.

**Provisional logic is a release gate.** Until FIFA's official third-place allocation table is encoded (§2.2), set `meta.provisional = true`, label it in the UI footer, and state the assumption in the README. Replacing the provisional table with the official one is a gate before any "final" launch. Unresolved qualifier/playoff slots are explicit placeholders with their own flag, never silently guessed teams.

### 8.2 Home advantage in a three-host tournament

- **Fit** `γ` from historical data where home/away/neutral is meaningful (the `neutral` flag enables this). Estimate a generic home term and how much to trust it at neutral sites.
- **Apply at tournament time by host status:**
  - Co-hosts (USA, Canada, Mexico) playing in their own country: a *reduced* home term (World Cup home effects are real but smaller than club football; size it from the historical neutral-vs-home split and document the multiplier).
  - All other matches: neutral, `γ = 0` for both sides.
- Make the multiplier a single documented config value so its impact is auditable and sensitivity-testable (§8.3).
- Edge case: a co-host playing in a *different* host country (e.g. Mexico in the USA) is neutral, not home. Encode venue→country and resolve host advantage per match, not per team.

### 8.3 Sensitivity analysis (`scripts/sensitivity.py`)

Because several inputs are uncertain (host multiplier, `ξ`, penalty cap, provisional allocation), re-run the pipeline across a small grid and report how much top-team title odds move. Publishing "top-4 ordering is stable under these assumptions; team X swings ±Y% with host advantage" is rigor *and* content — it quantifies the effect of provisional assumptions instead of hand-waving. *(Grid sweep can be post-launch; the host-multiplier sensitivity is worth showing at launch.)*

### 8.4 Data governance (full lifecycle)

- **Refresh:** `scripts/refresh_data.py` pulls the latest upstream snapshot, records new checksum + row count + date into the manifest, and fails loudly if the schema changed.
- **Schema validation on ingest** (e.g. `pandera` or a hand-rolled validator): required columns present, correct types, parseable dates, non-negative integer scores, team names resolvable against `aliases.json`, `neutral` boolean. Reject and report on violation; never train on silently malformed data.
- **Data quality checks:** flag duplicate fixtures, impossible scores, unmapped names, sudden row-count drops between snapshots. Emit a short data-quality report each refresh.
- **Schema evolution:** pin expected schema version in config; upstream column changes fail the validator and force an explicit, reviewed mapping update.
- **Licensing:** confirm the dataset license permits redistribution; if uncertain, ship a downloader script instead of the CSV. Record the license in `data/README.md`.
- **Long-term maintenance:** the upstream updates continuously; re-run the pipeline each matchday during the tournament. The git history of `predictions.json` becomes the public, auditable track record.

---

## 9. Success criteria

Two distinct definitions; keep them separate.

### 9.1 Model success (falsifiable, pre-tournament)

- Meets at least the **Target tier** (§4.6.2: RPS ≤ 0.215, accuracy ≥ 0.50) on the held-out test block.
- Beats all baselines (§4.6.3) except the bookmaker ceiling.
- ECE below a stated threshold (e.g. < 0.05) after calibration.
- Walk-forward metrics stable (no severe degradation in recent blocks).

These are gates: the model does not ship as "good" until it clears them, and the README publishes the actual numbers.

### 9.2 Engineering / product success (acceptance checklist)

- All model + simulation tests pass in CI; tiebreaker/third-place/knockout coverage is explicit.
- Benchmarks published with real numbers; the 100k run is within the stated time/memory budget.
- A clean clone reproduces the published `predictions.json` metrics exactly from committed config + snapshot.
- Frontend passes a WCAG AA accessibility audit, works one-handed on a phone, renders meaningful Title Race content on first paint, and the "what if" recompute is correct against a brute-force check on a small case.

### 9.3 Tournament-outcome accuracy is explicitly NOT a success metric

A single tournament cannot validate a probabilistic model — if the model says the favorite wins 14% of the time and they lose, the model was not "wrong." State this prominently. Validation lives at the match level (§4.6) and in calibration over many matches. During the tournament, track **match-level RPS live** as the honest scoreboard and own the calibration plot publicly. This protects the project from the inevitable "your model said X and was wrong" takes.

---

## 10. Documentation plan (half the point of the project)

The repo is marketed on readability, so docs are a first-class deliverable:

- **Root `README.md`:** one-paragraph what/why, an animated demo GIF, a one-command quickstart, the current published eval metrics + baselines, the live top-10 title-odds table (regenerated each matchday), an architecture diagram, CI badges, and links to each module README.
- **`model/README.md`:** Dixon-Coles math from first principles, why time-decay and the low-score correction, the evaluation framework and current numbers, how to interpret parameters, a worked example fixture.
- **`simulation/README.md`:** qualification flow diagram (groups → third-place ranking → bracket), the tiebreaker cascade, knockout staging, and notes on the allocation table.
- **`data/README.md`:** provenance, schema, license, snapshot date, refresh + validation commands.
- **`web/README.md`:** local dev, build, GitHub Pages deploy, the design tokens (typography scale + color tokens), and how the "what if" recompute works.
- **`CONTRIBUTING.md`:** environment setup, running tests, code style (ruff + a TS linter), PR expectations.
- Docstrings and type hints throughout Python; tests double as executable documentation of the tricky rules.

---

## 11. CI (`.github/workflows/ci.yml`)

On every push and PR:
1. Set up Python 3.11, install pinned `requirements.txt`.
2. `ruff check` (lint) + `ruff format --check`.
3. `pytest` (model + simulation tests, using the `--quick` simulation path).
4. Build the web app to catch TypeScript breakage.

Green CI badges in the README are part of the marketing.

---

## 12. Launch / social loop

- The Title Race table and bracket are inherently shareable; design them as shareable images.
- "Our model gives X a Y% chance" posts are debate-bait — lean in, but always show the Monte Carlo error note and the "this is a model, not a prophecy" framing.
- Re-run the pipeline after each matchday and post updated odds; the git history of `predictions.json` is a public track record — own the misses too, with the live match-level RPS as the honest scoreboard.
- A short thread explaining the Dixon-Coles math and the evaluation numbers draws the technical crowd to the repo.

---

## 13. Open items (external / to confirm)

1. **FIFA official 2026 third-place allocation table** — release gate (§2.2, §8.1).
2. **Unresolved qualifier/playoff slots** — placeholders until known (§5.3, §8.1).
3. **Final tuned values** of `ξ`, L2 weight, host multiplier, penalty cap — *determined by the walk-forward search*, not guessed; record the chosen values + justification in the experiment ledger once fit.
4. **Dataset redistribution license** — confirm; ship a downloader if uncertain (§8.4).
