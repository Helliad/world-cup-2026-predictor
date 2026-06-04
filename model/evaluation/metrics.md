# Model evaluation — held-out test block

Config: ξ=0.0018, L2=0.05, pooling=1.0, holdout=9mo

| Method | RPS ↓ | Brier ↓ | LogLoss ↓ | Top-pick acc ↑ | n |
|--------|------:|--------:|----------:|---------------:|--:|
| **Dixon-Coles (ours)** | 0.1608 | 0.4891 | 0.8337 | 0.604 | 782 |
| Double-Poisson | 0.1637 | 0.4939 | 0.8426 | 0.619 | 782 |
| Base rate | 0.2299 | 0.6342 | 1.0512 | 0.474 | 782 |
| Uniform | 0.2403 | 0.6667 | 1.0986 | 0.474 | 782 |

**Calibration** (temperature): test ECE 0.0464 → 0.0441 after; params={'method': 'temperature', 'temperature': 0.8898722871127629}

**Acceptance gates** (§4.6.2): achieved tier = **STRETCH**

| Tier | RPS ≤ | Acc ≥ | Pass |
|------|------:|------:|:----:|
| floor | 0.23 | 0.47 | ✅ |
| target | 0.215 | 0.5 | ✅ |
| stretch | 0.208 | 0.52 | ✅ |

Walk-forward pooled (dev): RPS=0.1763, acc=0.587, n=17795 across 38 blocks.
