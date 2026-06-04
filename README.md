# World Cup 2026 Predictor & Simulator

[![CI](https://github.com/OWNER/worldcup-2026-predictor/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/worldcup-2026-predictor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Model tier: STRETCH](https://img.shields.io/badge/eval-STRETCH%20tier-success.svg)](#how-good-is-the-model)

A **Dixon-Coles statistical model** fit on ~49,000 historical international matches, a **vectorised Monte-Carlo simulator** that plays the full 48-team 2026 World Cup 100,000 times, and a **polished React microsite** that turns the results into live title odds, group and bracket probabilities, and instant conditional "what if" scenarios.

Three layers, deliberately decoupled: the model knows nothing about tournaments, the simulator knows nothing about React, and the frontend reads one static `predictions.json` and never calls Python at runtime.

> **Status:** predictions are flagged **provisional** until FIFA's official third-place → bracket allocation table is encoded (a documented release gate, [§8.1 of the spec](worldcup-2026-predictor-SPEC.md)). Group memberships are official, reconstructed from the published fixture list.

---

## Current title odds

Top 10 of 48, from N = 100,000 simulations (±0.1% Monte-Carlo error at this N). Regenerated every run; the git history of `predictions.json` is the public track record.

| # | Team | Win title | Reach final | Advance |
|--:|------|----------:|------------:|--------:|
| 1 | Argentina | 15.1% | 22.6% | 97% |
| 2 | Spain | 14.3% | 22.1% | 99% |
| 3 | Brazil | 8.7% | 16.4% | 96% |
| 4 | Morocco | 6.9% | 12.9% | 92% |
| 5 | France | 6.2% | 11.5% | 91% |
| 6 | England | 5.5% | 10.8% | 97% |
| 7 | Portugal | 4.7% | 9.4% | 89% |
| 8 | Germany | 4.2% | 9.0% | 97% |
| 9 | Colombia | 3.7% | 7.8% | 87% |
| 10 | Netherlands | 3.7% | 7.4% | 88% |

*A model, not a prophecy: a 15% favourite is far more likely **not** to win than to win. See [§9.3](#tournament-accuracy-is-not-the-scoreboard).*

---

## How good is the model?

Evaluated by a **rolling-origin (walk-forward) backtest** — never random k-fold, which would leak the future into the past. Metrics on a held-out test block of 782 recent international matches (never seen during tuning):

| Method | RPS ↓ | Brier ↓ | Log-loss ↓ | Top-pick acc ↑ |
|--------|------:|--------:|-----------:|---------------:|
| **Dixon-Coles (this repo)** | **0.1608** | **0.4891** | **0.8337** | 0.604 |
| Plain double-Poisson | 0.1637 | 0.4939 | 0.8426 | 0.619 |
| Home/draw/away base rate | 0.2299 | 0.6342 | 1.0512 | 0.474 |
| Uniform (1/3 each) | 0.2403 | 0.6667 | 1.0986 | 0.474 |

- **Beats every baseline** on RPS (the field-standard proper scoring rule for football), Brier, and log-loss. The Dixon-Coles refinements (low-score correction + time decay) earn their complexity over plain double-Poisson on all three proper scores — honestly, double-Poisson edges it on raw top-pick *accuracy* (0.619 vs 0.604), which is exactly the kind of nuance RPS is designed to see past.
- **Acceptance gate: STRETCH tier** — RPS ≤ 0.208 and accuracy ≥ 0.52 (it does not "ship as good" until it clears its gates, enforced in CI).
- **Well calibrated:** ECE = 0.044 after temperature scaling (T = 0.89), under the 0.05 gate.
- **Stable across 18 years:** pooled walk-forward RPS = 0.176 across 38 six-month blocks, no degradation in recent windows.

> RPS ≈ 0.16 is lower (better) than the ~0.205 often cited as state-of-the-art for top-flight *club* leagues — not because this model is better than those, but because the full international fixture mix contains many lopsided qualifiers and friendlies that are genuinely more predictable. The honest headline is "beats every baseline and clears its gates," not "beats SOTA." Full report: [`model/evaluation/metrics.md`](model/evaluation/metrics.md).

---

## Quickstart

```bash
# 1. Python model + simulator
python -m pip install -r requirements.txt
python -m scripts.refresh_data        # download + validate the latest results.csv
python -m model.train                 # fit Dixon-Coles -> model/params.json
python -m model.evaluate              # walk-forward backtest + gates + plots
python -m scripts.run_pipeline        # 100k-sim Monte Carlo -> web/public/predictions.json

# 2. Frontend
cd web && npm install && npm run dev   # http://localhost:5173
```

A clean clone reproduces the published numbers exactly from the committed config + data snapshot + `params.json`. Use `--quick` on the pipeline/eval for a fast iteration loop (and in CI).

---

## Architecture

```
data/results.csv ──▶ model.train ──▶ model/params.json
   (martj42, ~49k matches)               │
                                         ▼
data/groups.json ───────────▶ simulation.monte_carlo ──▶ web/public/predictions.json
data/third_place_allocation.json ──┘   (100k tournaments)   web/public/outcomes_sample.json
                                                                      │
                                                          web/  (React + Vite + TS)
                                                          Title Race · Groups · Bracket · Team · "What if"
```

| Layer | Stack | What it does |
|-------|-------|--------------|
| **Model** ([`model/`](model/README.md)) | Python · NumPy · SciPy | Dixon-Coles fit by time-weighted MLE with an analytic gradient; full evaluation framework. |
| **Simulator** ([`simulation/`](simulation/README.md)) | Python (NumPy-vectorised) | Exact 2026 format: 12 groups → best-8-thirds → 32-team knockout, 100k times in ~6s. |
| **Frontend** ([`web/`](web/README.md)) | React · Vite · TypeScript · Tailwind | Static, editorial, accessible; instant conditional "what if" recompute in the browser. |

The Python ↔ React contract is [`predictions.json`](web/public/predictions.json) (schema in [§8.1 of the spec](worldcup-2026-predictor-SPEC.md)). Every run writes a full manifest (git commit, config hash, data checksum, seed, N) into `meta` so any two runs can be diffed and reproduced.

---

## Tournament accuracy is *not* the scoreboard

A single tournament cannot validate a probabilistic model — if the model says the favourite wins 15% of the time and they lose, the model was not "wrong." Validation lives at the **match level** (the RPS/calibration numbers above) over many matches. During the tournament we track **match-level RPS live** as the honest scoreboard and own the calibration plot publicly.

---

## Repository layout

See the [technical specification](worldcup-2026-predictor-SPEC.md) for the full design. Module docs: [model](model/README.md) · [simulation](simulation/README.md) · [data](data/README.md) · [web](web/README.md) · [contributing](CONTRIBUTING.md).

## Data & license

Code is MIT. The historical match data is [`martj42/international_results`](https://github.com/martj42/international_results) (CC BY-NC-SA 4.0) — see [`data/README.md`](data/README.md) for provenance, the schema, and refresh/validation commands.
