"""Vectorised Monte Carlo over N tournaments (§6.6).

Strategy: vectorise across *simulations*, not matches. Group scorelines are
sampled for all N sims at once from each fixture's precomputed scoreline CDF; the
knockout is resolved by a precomputed 48×48 win-probability matrix plus Bernoulli
draws, so no knockout goals are sampled. The two genuinely data-dependent,
hard-to-vectorise steps — group standings that tie on the primary key, and
third-place slot conflicts — fall back to per-sim Python on just the affected
sims, reusing the exact tiebreaker code the single-tournament path uses.

Output: per-team P(advance / R16 / QF / SF / final / win) with Monte Carlo
standard errors, plus a compact integer-encoded sample of bracket+group outcomes
for the client-side "what if" feature.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from simulation.group_stage import rank_group
from simulation.knockout import KnockoutParams, build_winprob_matrix
from simulation.third_place import assign_thirds_to_slots, third_slot_groups

# Packing constants for the (points, GD, GF) primary key into one sortable int.
_K_POINTS = 1_000_000
_K_GD = 1_000
_K_GD_OFFSET = 500  # keeps (GD + offset) positive


@dataclass
class SimResults:
    teams: list[str]
    group_of: dict[str, str]
    n: int
    seed: int
    provisional: bool
    p_advance: np.ndarray
    p_r16: np.ndarray
    p_qf: np.ndarray
    p_sf: np.ndarray
    p_final: np.ndarray
    p_win: np.ndarray
    se_win: np.ndarray
    exp_points: np.ndarray
    # compact what-if sample
    whatif_stage: np.ndarray  # uint8 [K, 48], furthest-stage code per team
    whatif_group_rank: np.ndarray  # uint8 [K, 48], 1..4 group finish per team
    whatif_slots: np.ndarray  # uint8 [K, 32], team index occupying each R32 slot


def _sample_fixture(model, home, away, home_adv, rng, n) -> tuple[np.ndarray, np.ndarray]:
    """Sample N (home_goals, away_goals) from a fixture's DC scoreline matrix."""
    P = model.predict_scoreline_matrix(home, away, home_advantage=home_adv)
    flat = P.ravel()
    cdf = np.cumsum(flat)
    cdf[-1] = 1.0
    u = rng.random(n)
    idx = np.searchsorted(cdf, u, side="right")
    np.clip(idx, 0, flat.size - 1, out=idx)
    ncols = P.shape[1]
    return idx // ncols, idx % ncols


def run_simulations(
    model,
    sim_inputs: dict,
    params: KnockoutParams,
    n: int,
    seed: int,
    whatif_sample_size: int = 8000,
    verbose: bool = True,
) -> SimResults:
    groups = sim_inputs["groups"]
    fixtures_by_group = sim_inputs["fixtures_by_group"]
    allocation = sim_inputs["allocation"]
    provisional = sim_inputs["provisional"]
    rng = np.random.default_rng(seed)

    wc_teams = sorted({t for ts in groups.values() for t in ts})
    gidx = {t: i for i, t in enumerate(wc_teams)}
    n_teams = len(wc_teams)
    group_of = {t: g for g, ts in groups.items() for t in ts}

    if verbose:
        print(f"  precomputing {n_teams}×{n_teams} knockout win-prob matrix...")
    W = build_winprob_matrix(model, params, wc_teams)

    rows = np.arange(n)
    winner_g: dict[str, np.ndarray] = {}
    runner_g: dict[str, np.ndarray] = {}
    points_global = np.zeros((n, n_teams), dtype=np.int32)
    group_rank_global = np.zeros((n, n_teams), dtype=np.uint8)
    thirds_global = np.zeros((n, len(groups)), dtype=np.int64)
    thirds_key = np.zeros((n, len(groups)), dtype=np.int64)
    thirds_group_letter: list[str] = []

    if verbose:
        print(f"  simulating {len(groups)} groups × {n} sims...")
    for col, letter in enumerate(sorted(groups)):
        teams_local = groups[letter]
        lidx = {t: k for k, t in enumerate(teams_local)}
        local_to_global = np.array([gidx[t] for t in teams_local])

        points = np.zeros((n, 4), dtype=np.int64)
        gf = np.zeros((n, 4), dtype=np.int64)
        ga = np.zeros((n, 4), dtype=np.int64)
        fixtures_data = []
        for home, away, home_adv in fixtures_by_group[letter]:
            gh, gaa = _sample_fixture(model, home, away, home_adv, rng, n)
            ih, ia = lidx[home], lidx[away]
            gf[:, ih] += gh
            ga[:, ih] += gaa
            gf[:, ia] += gaa
            ga[:, ia] += gh
            home_win = gh > gaa
            away_win = gaa > gh
            draw = gh == gaa
            points[:, ih] += 3 * home_win + draw
            points[:, ia] += 3 * away_win + draw
            fixtures_data.append((ih, ia, gh, gaa))

        gd = gf - ga
        key = points * _K_POINTS + (gd + _K_GD_OFFSET) * _K_GD + gf
        order = np.argsort(-key, axis=1, kind="stable")
        sorted_key = np.take_along_axis(key, order, axis=1)
        tie_mask = np.any(sorted_key[:, :-1] == sorted_key[:, 1:], axis=1)

        # patch sims that tie on the primary key with the full cascade
        if tie_mask.any():
            lots = rng.random((n, 4))
            for s in np.nonzero(tie_mask)[0]:
                results = [(ih, ia, int(gh[s]), int(gaa[s])) for ih, ia, gh, gaa in fixtures_data]
                order[s] = rank_group(points[s], gf[s], ga[s], results, lots[s])

        # scatter results to global structures
        winner_g[letter] = local_to_global[order[:, 0]]
        runner_g[letter] = local_to_global[order[:, 1]]
        third_local = order[:, 2]
        thirds_global[:, col] = local_to_global[third_local]
        thirds_key[:, col] = np.take_along_axis(key, order[:, 2:3], axis=1)[:, 0]
        thirds_group_letter.append(letter)
        points_global[rows[:, None], local_to_global[None, :]] = points
        for pos in range(4):
            group_rank_global[rows, local_to_global[order[:, pos]]] = pos + 1

    # --- best-third selection + slot allocation ---
    if verbose:
        print("  selecting best thirds + allocating bracket slots...")
    # Break exact (points,GD,GF) ties at the 8/9 qualification boundary with
    # seeded lots, exactly like the single-tournament reference — NOT by group
    # letter (which a stable argsort on the packed key alone would do, biasing
    # qualification toward alphabetically-earlier groups). thirds_key is integer
    # with gaps >= 1, so adding lots in [0,1) only reorders genuine ties.
    sel_lots = rng.random(thirds_key.shape)
    composite = thirds_key.astype(np.float64) + sel_lots
    top8_cols = np.argsort(-composite, axis=1, kind="stable")[:, :8]
    sel_team = np.take_along_axis(thirds_global, top8_cols, axis=1)  # [n,8] in rank order
    letters_arr = np.array(thirds_group_letter)
    sel_group = letters_arr[top8_cols]  # [n,8]

    slot_info = third_slot_groups(allocation)  # [(match_no, winner_group)] in order
    fb = [wg for _m, wg in slot_info]  # forbidden group per third-slot
    slot_col_of_match = {m: r for r, (m, _wg) in enumerate(slot_info)}

    assign_team = sel_team.copy()  # naive: slot r <- rank-r third (correct when no conflict)
    conflict = np.zeros(n, dtype=bool)
    for r, wg in enumerate(fb):
        conflict |= sel_group[:, r] == wg
    # patch only the conflicting sims, with the same conflict-free matching the
    # reference path uses (no same-group Round-of-32 meeting).
    for s in np.nonzero(conflict)[0]:
        slot_to_rank = assign_thirds_to_slots(fb, list(sel_group[s]))
        for r in range(len(fb)):
            assign_team[s, r] = sel_team[s, slot_to_rank[r]]

    # --- build the 32-slot bracket array (bracket order) ---
    slots = np.zeros((n, 32), dtype=np.int64)

    def resolve(label: str) -> np.ndarray:
        kind, grp = label.split("_")
        return winner_g[grp] if kind == "W" else runner_g[grp]

    for m in sorted(allocation["r32"], key=lambda x: x["match"]):
        mi = m["match"] - 1
        slots[:, 2 * mi] = resolve(m["top"])
        if m["bottom"] == "3RD":
            slots[:, 2 * mi + 1] = assign_team[:, slot_col_of_match[m["match"]]]
        else:
            slots[:, 2 * mi + 1] = resolve(m["bottom"])

    # --- fold the bracket, vectorised across sims ---
    if verbose:
        print("  folding knockout bracket...")
    stage = np.zeros((n, n_teams), dtype=np.uint8)
    stage[rows[:, None], slots] = 1  # all 32 participants reached the Round of 32
    cur = slots
    round_code = 2
    while cur.shape[1] > 1:
        a = cur[:, 0::2]
        b = cur[:, 1::2]
        pa = W[a, b]
        u = rng.random(pa.shape)
        winners = np.where(u < pa, a, b)
        stage[rows[:, None], winners] = round_code
        cur = winners
        round_code += 1

    # --- tally probabilities + standard errors ---
    def frac(mask_code: int) -> np.ndarray:
        return (stage >= mask_code).mean(axis=0)

    p_advance = frac(1)
    p_win = (stage >= 6).mean(axis=0)
    se_win = np.sqrt(np.clip(p_win * (1 - p_win), 0, None) / n)
    exp_points = points_global.mean(axis=0)

    k = min(whatif_sample_size, n)
    return SimResults(
        teams=wc_teams,
        group_of=group_of,
        n=n,
        seed=seed,
        provisional=provisional,
        p_advance=p_advance,
        p_r16=frac(2),
        p_qf=frac(3),
        p_sf=frac(4),
        p_final=frac(5),
        p_win=p_win,
        se_win=se_win,
        exp_points=exp_points,
        whatif_stage=stage[:k].copy(),
        whatif_group_rank=group_rank_global[:k].copy(),
        whatif_slots=slots[:k].astype(np.uint8),
    )
