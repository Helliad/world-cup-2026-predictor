# `model/` — the Dixon-Coles match model

Predicts a **full scoreline-probability matrix** for any fixture, fit by
time-weighted maximum likelihood on historical international results. The
simulator samples from this matrix; the frontend renders the win/draw/loss
collapse. The model knows nothing about tournaments.

## The math, from first principles

Football goals are well-approximated by a Poisson process. For each team *i* we
fit an **attack** strength `α_i` and a **defence** weakness `β_i`; a global
**home** term `γ` applies only at non-neutral venues. For home team *i* vs away
team *j*:

```
log λ  (home expected goals) = α_i + β_j + γ · home_flag
log μ  (away expected goals) = α_j + β_i
```

The probability of an exact scoreline (x home, y away) adds the **Dixon & Coles
(1997)** low-score correction `τ`:

```
P(x, y) = τ(x, y; λ, μ, ρ) · Poisson(x; λ) · Poisson(y; μ)

τ = 1 − λμρ   (0-0)     1 + λρ   (0-1)
    1 + μρ    (1-0)     1 − ρ    (1-1)     1   otherwise
```

`τ` fixes the empirical fact that 0-0, 1-0, 0-1 and 1-1 occur at rates plain
double-Poisson gets wrong. All parameters (`α, β, γ, ρ`) are fit by **maximum
likelihood** with `scipy.optimize.minimize` (L-BFGS-B) and an **analytic
gradient** (so the walk-forward search is fast — verified against a numerical
gradient to ~1e-6 in the tests).

Two refinements beyond plain double-Poisson:

1. **Time decay.** Each match is weighted `w_t = exp(−ξ · Δt)`, Δt in days.
   The tuned `ξ = 0.0018` implies a **half-life of ~385 days (~12.6 months)** —
   a result from 2 years ago counts about half as much as one from today.
2. **The τ low-score correction** above. Fitted `ρ ≈ −0.054` (the classic small
   negative value).

**Identifiability:** attack is mean-centred (`Σα = 0`); fitted `γ ≈ 0.244`,
i.e. the home side's expected goals are multiplied by ~1.28.

## Regularization, sparsity, new teams (§4.4)

- **L2 ridge** on attack/defence shrinks teams toward the league baseline.
- **Confederation partial pooling** pulls each team toward its confederation
  mean (UEFA/CONMEBOL/CAF/AFC/CONCACAF/OFC), so thin records don't produce absurd
  parameters. The gradient of the pooling term simplifies cleanly because
  within-group deviations sum to zero (see `dixon_coles.py`).
- **Data-confidence flag** (`high`/`medium`/`low`) per team from recent match
  counts, surfaced in `predictions.json` and the UI so low-data teams are
  labelled honestly. (All 48 2026 teams clear "high" — even the thinnest have 38+
  recent matches.)

## The evaluation framework (a hard requirement, §4.6)

A model isn't "done" when it fits — it's done when it clears its acceptance gates
on held-out data. This is mandatory and enforced in CI.

- **Metrics — report all three, optimise on RPS:** Ranked Probability Score
  (respects outcome ordering), multiclass Brier (cross-check), log-loss (catches
  overconfidence). Plus top-pick accuracy and ECE.
- **Validation is temporal, never random.** Rolling-origin (walk-forward)
  backtest: train up to T, predict the next block, advance T. A final 9-month
  block is held out untouched as the true test set. `ξ`, L2 and calibration are
  tuned *inside* the walk-forward loop, never on the test block.
- **Baselines:** uniform, home/draw/away base rate, plain double-Poisson — all on
  the same test fixtures. (Bookmaker-implied odds are an aspirational ceiling, not
  shipped because the open dataset has no odds.)
- **Calibration:** reliability diagrams + ECE; temperature scaling fit on a
  validation block.

### Current numbers (held-out test block, n = 782)

| Method | RPS ↓ | Brier ↓ | Log-loss ↓ | Acc ↑ |
|--------|------:|--------:|-----------:|------:|
| **Dixon-Coles** | **0.1608** | **0.4891** | **0.8337** | 0.604 |
| Double-Poisson | 0.1637 | 0.4939 | 0.8426 | 0.619 |
| Base rate | 0.2299 | 0.6342 | 1.0512 | 0.474 |
| Uniform | 0.2403 | 0.6667 | 1.0986 | 0.474 |

**Achieved tier: STRETCH** (RPS ≤ 0.208, acc ≥ 0.52). ECE = 0.044 after
temperature scaling (T = 0.89). Pooled walk-forward RPS = 0.176 across 38 blocks,
stable. Reliability + per-block RPS plots in `model/evaluation/plots/`.

## Public API

```python
from model.dixon_coles import DixonColesModel

model = DixonColesModel.load("model/params.json")
P = model.predict_scoreline_matrix("Brazil", "Argentina")      # (11, 11) matrix, sums to 1
o = model.predict_outcome("Brazil", "Argentina")               # {home_win, draw, away_win, exp_home, exp_away}
o_neutral = model.predict_outcome("Brazil", "Argentina", home_advantage=0.0)  # neutral venue
```

`home_advantage` overrides γ per call — pass `0.0` for a neutral venue, or a
reduced γ for a co-host playing at home (the simulator does both, §8.2).

## Worked example

```python
>>> m = DixonColesModel.load("model/params.json")
>>> m.predict_outcome("Spain", "New Zealand", home_advantage=0.0)
{'home_win': ~0.89, 'draw': ~0.08, 'away_win': ~0.03, 'exp_home': ~3.2, 'exp_away': ~0.5}
```

Spain (one of the strongest fitted attacks, α ≈ +1.34) beats a much weaker side
at a neutral venue ~89% of the time with ~3.2 expected goals — exactly the kind of
lopsided-but-predictable fixture the model should nail.

## Files

| File | Role |
|------|------|
| `dixon_coles.py` | the model: NLL + analytic gradient, `fit`, `predict_*`, `save`/`load`. |
| `ratings.py` | confederation mapping, partial-pooling index, data-confidence flags. |
| `train.py` | CLI: validate → fit → write `params.json`. |
| `evaluate.py` + `evaluation/` | metrics, baselines, walk-forward backtest, calibration, gates. |
| `params.json` | committed fitted parameters (reproducible artifact). |

## Run

```bash
python -m model.train          # fit + save params.json
python -m model.evaluate       # full backtest (use --quick for the last few blocks)
pytest model/tests -q          # the model tests double as executable docs of the rules
```
