# User Guide

How to run the World Cup 2026 Predictor and open the frontend in your browser.

This project has two halves that are deliberately decoupled:

- A **Python pipeline** (model + simulator) that produces a static data file, [`web/public/predictions.json`](web/public/predictions.json).
- A **React frontend** ([`web/`](web/)) that reads that file and never calls Python at runtime.

Because `predictions.json` (and `outcomes_sample.json`) are **already committed to the repo**, you do **not** need Python or any model run to see the site. If you just want to look at the frontend, jump to [Path A](#path-a-just-see-the-frontend-fastest). If you want to regenerate the predictions yourself, do [Path B](#path-b-regenerate-the-predictions-python-pipeline) first.

---

## Prerequisites

| For… | You need |
|------|----------|
| The frontend (Path A) | **Node.js 20+** and npm — check with `node --version` |
| Regenerating data (Path B) | **Python 3.11+** — check with `python --version` |

> On Windows the commands below work in **PowerShell** (the default in this repo). Where a step changes directory, it's shown explicitly.

---

## Path A — Just see the frontend (fastest)

The committed `predictions.json` already contains the published 100,000-simulation results, so this is all you need:

```powershell
cd web
npm install      # first time only — installs React/Vite/etc.
npm run dev      # starts the dev server
```

You'll see Vite print a local URL. Open it in your browser:

```
  ➜  Local:   http://localhost:5173/
```

**→ Open http://localhost:5173 — that's the frontend.**

The dev server hot-reloads on file changes; press `Ctrl+C` in the terminal to stop it.

### What you'll see

The site is a single-page app with a top nav bar. The views:

| View | URL | What it shows |
|------|-----|---------------|
| **Title Race** (landing) | `/` | Championship odds for the top contenders — the headline numbers. This is the first thing that paints. |
| **Groups** | `/groups` | All 12 groups (A–L) with each team's probability of advancing; tap a group to expand standings. |
| **Bracket** | `/bracket` | The 32-team knockout tree with the most-likely occupant of each slot. Scrolls horizontally on mobile. |
| **Team detail** | `/team/:id` | Per-team stage-by-stage probabilities, projected path, and a data-confidence flag. Reached by tapping any team anywhere. |
| **"What if"** | overlay (any view) | Pin an outcome (e.g. "assume Brazil reach the final") and watch every probability recompute instantly. Pinned conditions are saved in the URL, so the scenario is a shareable link. |

> **Note:** predictions are labelled **provisional** in the footer until FIFA's official third-place → bracket allocation table is encoded. That's expected — the group memberships are official; the bracket seeding of third-placed teams uses a documented fallback.

### Production build (optional)

To build the static bundle the way it ships (this also typechecks):

```powershell
cd web
npm run build     # outputs to web/dist/
npm run preview   # serves the built bundle locally to check it
```

`npm run preview` prints its own local URL (typically `http://localhost:4173`).

---

## Path B — Regenerate the predictions (Python pipeline)

Do this only if you want to re-fit the model or re-run the simulation yourself. It overwrites `web/public/predictions.json`, which the frontend then reads.

From the **repo root**:

```powershell
python -m pip install -r requirements.txt   # first time only

python -m scripts.validate_data             # sanity-check the committed data snapshot
python -m model.train                       # fit Dixon-Coles -> model/params.json
python -m model.evaluate --quick            # fast backtest + acceptance gates
python -m scripts.run_pipeline --quick      # Monte Carlo -> web/public/predictions.json
```

Then run the frontend as in [Path A](#path-a-just-see-the-frontend-fastest) to see the new numbers.

### `--quick` vs full

- `--quick` uses a small simulation count (`quick_n: 2000` in [`config.yaml`](config.yaml)) — seconds to run, good for iteration.
- **Drop `--quick`** to reproduce the published figures: the full `python -m scripts.run_pipeline` runs 100,000 simulations (~6s) and is what the committed `predictions.json` was generated from.

```powershell
python -m scripts.run_pipeline              # full 100k-simulation run
```

### Refreshing the historical data (optional)

The historical match data is committed and pinned, so you don't normally need this. To pull the latest upstream snapshot:

```powershell
python -m scripts.refresh_data              # download + validate latest results.csv
```

Every tunable knob (decay rate, simulation count, seed, host advantage, gates) lives in [`config.yaml`](config.yaml) — the pipeline reads only from there.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `npm: command not found` | Install Node.js 20+ from [nodejs.org](https://nodejs.org), then reopen the terminal. |
| Port 5173 already in use | Vite auto-picks the next free port and prints the new URL — use that. Or stop whatever is on 5173. |
| Blank page / "failed to load predictions" | Make sure you ran `npm run dev` from inside the `web/` directory, and that `web/public/predictions.json` exists. |
| `python: command not found` (Path B) | Install Python 3.11+, or try `python3` / `py` instead of `python`. |
| Model `evaluate` exits non-zero | That's the acceptance gate failing on purpose — the model "does not ship as good" until it clears its gates. Check the printed metrics. |
| Edited the model but the site shows old numbers | Re-run `python -m scripts.run_pipeline` to regenerate `predictions.json`, then refresh the browser (the dev server picks it up). |

---

## At a glance

```
data/results.csv ─▶ model.train ─▶ model/params.json
                                        │
data/groups.json ──────────────────────┼─▶ scripts.run_pipeline ─▶ web/public/predictions.json
data/third_place_allocation.json ──────┘                                    │
                                                          web/ (React) ◀─────┘
                                                          npm run dev  →  http://localhost:5173
```

For the full design, see the [README](README.md) and the [technical specification](worldcup-2026-predictor-SPEC.md). Module docs: [model](model/README.md) · [simulation](simulation/README.md) · [data](data/README.md) · [web](web/README.md) · [contributing](CONTRIBUTING.md).
