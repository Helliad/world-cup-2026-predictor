"""Tournament simulator (§6).

The simulator knows nothing about React. It composes the 2026 format exactly:
12 groups -> third-place ranking -> 32-team knockout -> champion, run N times
and aggregated into probabilities with Monte Carlo standard errors.
"""
