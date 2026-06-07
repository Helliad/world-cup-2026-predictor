# Contributing

Thanks for your interest! This project is built to demonstrate clean, documented,
rigorous engineering — contributions that keep that bar are very welcome.

## Environment

- **Python 3.11+** (developed on 3.13). `pip install -r requirements.txt`.
- **Node 20+** for the frontend. `cd web && npm install`.

Dependencies are pinned. The committed `data/results.csv`, `model/params.json`,
and `web/public/predictions.json` let a clean clone reproduce the published
numbers exactly — please keep them in sync when you change the model or pipeline.

## Running things

```bash
python -m scripts.validate_data        # validate the data snapshot
python -m model.train                  # fit -> model/params.json
python -m model.evaluate --quick       # fast backtest + gates
python -m scripts.run_pipeline --quick # fast Monte Carlo -> predictions.json
cd web && npm run dev                  # frontend
```

## Tests & style

```bash
ruff check . && ruff format --check .   # Python lint + format
pytest -q                               # model + simulation tests
cd web && npm run build                 # TypeScript typecheck + build
```

All four run in CI on every push and PR (`.github/workflows/ci.yml`). Please:

- Keep **ruff** clean (`ruff format` before committing).
- Add or update **tests** for behaviour changes — the simulator's
  tiebreaker / third-place / knockout tests are the credibility centrepiece and
  double as executable documentation of the rules. New tests should be fast and
  deterministic (seed all RNG).
- Use **type hints + docstrings** on Python; the frontend is `strict` TypeScript.
- If you change the model or simulation, re-run the pipeline and commit the
  refreshed `params.json` / `predictions.json`, and update the published metrics
  in the READMEs.

## The acceptance gate

The model "does not ship as good until it clears its gates" (§4.6.2). `model/evaluate`
exits non-zero below the Floor tier, and CI enforces it. If a change moves the
metrics, report the new numbers honestly — a regression that's a genuine finding
is worth reporting, not hiding.

## PRs

Small, focused PRs with a clear description. Be kind in review.
