"""End-to-end pipeline: params + groups → simulate → predictions.json (§8.1).

    results.csv ─▶ (already trained) params.json
    groups.json + third_place_allocation.json ─▶ monte_carlo ─▶ predictions.json
                                                              └▶ outcomes_sample.json (what-if)

Writes a full run manifest (git commit, config hash, data checksum, versions,
N, seed, timestamp) into predictions.json.meta so any run is reproducible and
diffable, and appends a row to experiments/ledger.csv.

Usage:
  python -m scripts.run_pipeline           # full N from config
  python -m scripts.run_pipeline --quick    # quick_n from config (fast)
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

import numpy as np

from config import config_hash, load_config, resolve_path
from model.dixon_coles import DixonColesModel
from simulation.group_stage import rank_group, tally
from simulation.knockout import KnockoutParams
from simulation.monte_carlo import SimResults, run_simulations
from simulation.setup import load_sim_inputs
from simulation.tournament import STAGES

ROOT = Path(__file__).resolve().parents[1]
N_MARQUEE_MATCHUPS = 16  # pairwise 1X2 among the top-N teams by title odds
LAST_GROUP_MATCH = 72  # matches 1..72 are group games; 73..104 are knockout


def _git_commit() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:  # noqa: BLE001
        return "unknown"


def _round1(x: float) -> float:
    return round(float(x), 4)


def build_fixtures(model: DixonColesModel, cfg: dict) -> list[dict]:
    """The 72 group-stage fixtures with their 1X2 match probabilities.

    Computed with the model + the per-fixture co-host home advantage (§8.2), so
    the frontend can show the chance of each result without a model in the browser.
    """
    groups_data = json.loads((ROOT / "data" / "groups.json").read_text(encoding="utf-8"))
    cohost_mult = cfg["home_advantage"]["cohost_multiplier"]
    out: list[dict] = []
    for f in groups_data["fixtures"]:
        home_adv = cohost_mult * model.gamma if f["home_advantage"] else 0.0
        o = model.predict_outcome(f["home"], f["away"], home_advantage=home_adv)
        out.append(
            {
                "group": f["group"],
                "date": f["date"],
                "home": f["home"],
                "away": f["away"],
                "home_win": _round1(o["home_win"]),
                "draw": _round1(o["draw"]),
                "away_win": _round1(o["away_win"]),
                "exp_home": round(float(o["exp_home"]), 2),
                "exp_away": round(float(o["exp_away"]), 2),
                "host": f["home_advantage"],  # home team name if co-host advantage, else null
            }
        )
    return out


def _resolve_label(label: str | None, ctx: dict) -> str | None:
    """Resolve a knockout slot descriptor to an actual team, when known.

    Handles the deterministic descriptors — group winner/runner (once a group is
    fully played) and Winner/Loser of an earlier match (once it is played). The
    best-third descriptors ("3rd Group A/B/C/D/F") depend on the provisional
    allocation table and are left unresolved (the UI keeps the descriptor).
    """
    if not label:
        return None
    if label.startswith("Winner Group "):
        return ctx["group_winner"].get(label.rsplit(" ", 1)[-1])
    if label.startswith("Runner-up Group "):
        return ctx["group_runner"].get(label.rsplit(" ", 1)[-1])
    if label.startswith("Winner Match "):
        return ctx["winner_of"].get(int(label.rsplit(" ", 1)[-1]))
    if label.startswith("Loser Match "):
        return ctx["loser_of"].get(int(label.rsplit(" ", 1)[-1]))
    return None


def build_schedule() -> list[dict]:
    """The full 104-match schedule (data/schedule.json) merged with any actual
    results (data/results_2026.json): each entry gains a status/score, and
    knockout participants are filled in as results determine them.

    The pipeline only records *facts* here (played scores, and teams a result has
    decided); pre-result "most-likely occupant" projections are left to the
    frontend, which reads them from the simulation's bracket sample.
    """
    schedule = json.loads((ROOT / "data" / "schedule.json").read_text(encoding="utf-8"))["matches"]
    results_path = ROOT / "data" / "results_2026.json"
    played_list = (
        json.loads(results_path.read_text(encoding="utf-8")).get("matches", [])
        if results_path.exists()
        else []
    )
    played = {r["match"]: r for r in played_list if "match" in r}
    groups = json.loads((ROOT / "data" / "groups.json").read_text(encoding="utf-8"))["groups"]

    # Group winner/runner-up, resolved only for groups whose 6 games are all played.
    group_matches: dict[str, list[dict]] = {}
    for m in schedule:
        if m["round"] == "group":
            group_matches.setdefault(m["group"], []).append(m)
    group_winner: dict[str, str] = {}
    group_runner: dict[str, str] = {}
    for letter, ms in group_matches.items():
        if not all(m["match"] in played for m in ms):
            continue
        members = groups[letter]
        lidx = {t: i for i, t in enumerate(members)}
        res = [
            (
                lidx[played[m["match"]]["home"]],
                lidx[played[m["match"]]["away"]],
                int(played[m["match"]]["home_score"]),
                int(played[m["match"]]["away_score"]),
            )
            for m in ms
        ]
        points, gf, ga = tally(len(members), res)
        order = rank_group(points, gf, ga, res, np.zeros(len(members)))
        group_winner[letter] = members[order[0]]
        group_runner[letter] = members[order[1]]

    ctx = {
        "group_winner": group_winner,
        "group_runner": group_runner,
        "winner_of": {},  # match_no -> winning team (knockout, from results)
        "loser_of": {},
    }

    out: list[dict] = []
    for m in sorted(schedule, key=lambda x: x["match"]):
        played_r = played.get(m["match"])
        entry: dict = {
            "match": m["match"],
            "round": m["round"],
            "date": m["date"],
            "venue": m["venue"],
            "group": m.get("group"),
            "host": m.get("host"),
            "top_label": m.get("top_label"),
            "bottom_label": m.get("bottom_label"),
            "feeds": m.get("feeds"),
        }
        if m["round"] == "group":
            home, away = m["home"], m["away"]
            if played_r:
                hs, as_ = int(played_r["home_score"]), int(played_r["away_score"])
                if (played_r["home"], played_r["away"]) != (home, away):
                    hs, as_ = as_, hs  # normalise to the schedule's orientation
                winner = home if hs > as_ else away if as_ > hs else None
                entry.update(status="played", score={"home": hs, "away": as_}, winner=winner)
            else:
                entry.update(status="scheduled", score=None, winner=None)
        else:
            home = _resolve_label(m.get("top_label"), ctx)
            away = _resolve_label(m.get("bottom_label"), ctx)
            if played_r:
                home, away = played_r["home"], played_r["away"]
                winner = played_r["winner"]
                ctx["winner_of"][m["match"]] = winner
                ctx["loser_of"][m["match"]] = away if winner == home else home
                entry.update(
                    status="played",
                    score={
                        "home": int(played_r["home_score"]),
                        "away": int(played_r["away_score"]),
                    },
                    winner=winner,
                    decided_by=played_r.get("decided_by"),
                )
            else:
                entry.update(status="scheduled", score=None, winner=None, decided_by=None)
        entry["home"] = home
        entry["away"] = away
        out.append(entry)
    return out


def build_predictions(
    sim: SimResults, model: DixonColesModel, cfg: dict, manifest: dict, allocation: dict
) -> dict:
    gi = {t: i for i, t in enumerate(sim.teams)}
    data_conf = model.meta.get("data_confidence", {})

    teams_out = []
    for t in sim.teams:
        i = gi[t]
        teams_out.append(
            {
                "team": t,
                "group": sim.group_of[t],
                "data_confidence": data_conf.get(t, "high"),
                "p_advance": _round1(sim.p_advance[i]),
                "p_r16": _round1(sim.p_r16[i]),
                "p_qf": _round1(sim.p_qf[i]),
                "p_sf": _round1(sim.p_sf[i]),
                "p_final": _round1(sim.p_final[i]),
                "p_win": _round1(sim.p_win[i]),
                "se_win": round(float(sim.se_win[i]), 5),
                "alpha": round(float(model.attack[model.team_index[t]]), 4),
                "beta": round(float(model.defence[model.team_index[t]]), 4),
            }
        )
    teams_out.sort(key=lambda d: -d["p_win"])

    groups_out: dict[str, list[dict]] = {}
    for letter in sorted(set(sim.group_of.values())):
        members = [t for t in sim.teams if sim.group_of[t] == letter]
        rows = [
            {
                "team": t,
                "p_advance": _round1(sim.p_advance[gi[t]]),
                "exp_points": round(float(sim.exp_points[gi[t]]), 2),
                "data_confidence": data_conf.get(t, "high"),
            }
            for t in members
        ]
        rows.sort(key=lambda d: -d["p_advance"])
        groups_out[letter] = rows

    # marquee matchups: neutral 1X2 among the top-N title contenders
    top = [d["team"] for d in teams_out[:N_MARQUEE_MATCHUPS]]
    matchups: dict[str, dict] = {}
    for a, b in combinations(top, 2):
        o = model.predict_outcome(a, b, home_advantage=0.0)
        matchups[f"{a}|{b}"] = {
            "home_win": _round1(o["home_win"]),
            "draw": _round1(o["draw"]),
            "away_win": _round1(o["away_win"]),
        }

    bracket_r32 = [
        {"match": m["match"], "top": m["top"], "bottom": m["bottom"]}
        for m in sorted(allocation["r32"], key=lambda x: x["match"])
    ]

    return {
        "meta": manifest,
        "groups": groups_out,
        "teams": teams_out,
        "matchups": matchups,
        "bracket_r32": bracket_r32,
        "fixtures": build_fixtures(model, cfg),
        "schedule": build_schedule(),
    }


def build_manifest(sim: SimResults, model: DixonColesModel, cfg: dict, quick: bool) -> dict:
    snap = json.loads((ROOT / "data" / "snapshot_manifest.json").read_text(encoding="utf-8"))
    metrics_path = resolve_path(cfg["output"]["metrics_path"])
    model_metrics = None
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        model_metrics = {
            "rps_test": m["test"]["model"]["rps"],
            "accuracy_test": m["test"]["model"]["accuracy"],
            "achieved_tier": m.get("gates", {}).get("achieved"),
        }
    return {
        "n_simulations": sim.n,
        "quick": quick,
        "seed": sim.seed,
        "model_version": model.meta.get("model_version", cfg["model"]["version"]),
        "data_snapshot": snap["max_date"],
        "data_checksum": snap["sha256"],
        "data_rows": snap["rows"],
        "git_commit": _git_commit(),
        "config_hash": config_hash(cfg),
        "provisional": sim.provisional,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "home_advantage_gamma": round(model.gamma, 4),
        "cohost_multiplier": cfg["home_advantage"]["cohost_multiplier"],
        # Extra model params the frontend needs to reproduce the Dixon-Coles
        # scoreline distribution in the browser (any matchup, incl. knockouts).
        "rho": round(float(model.rho), 5),
        "max_goals": int(model.max_goals),
        "knockout": {
            "mode": cfg["simulation"]["knockout"]["mode"],
            "extra_time_fraction": cfg["simulation"]["knockout"]["extra_time_fraction"],
            "penalty_skill_tilt": cfg["simulation"]["knockout"]["penalty_skill_tilt"],
            "penalty_cap": cfg["simulation"]["knockout"]["penalty_cap"],
        },
        "half_life_days": model.meta.get("half_life_days"),
        "se_note": f"Monte Carlo standard error ≈ sqrt(p(1-p)/N); at N={sim.n} a title "
        f"probability of 10% carries ±{100 * np.sqrt(0.1 * 0.9 / sim.n):.2f}%.",
        "model_metrics": model_metrics,
        "libraries": {"numpy": np.__version__, "python": platform.python_version()},
    }


def write_outcomes_sample(sim: SimResults, path: Path) -> int:
    payload = {
        "n": int(sim.whatif_stage.shape[0]),
        "teams": sim.teams,
        "stage_codes": {s: i for i, s in enumerate(STAGES)},
        "stage_b64": base64.b64encode(sim.whatif_stage.tobytes()).decode("ascii"),
        "group_rank_b64": base64.b64encode(sim.whatif_group_rank.tobytes()).decode("ascii"),
        "slots_b64": base64.b64encode(sim.whatif_slots.tobytes()).decode("ascii"),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path.stat().st_size


def append_ledger(manifest: dict, sim: SimResults, top_team: str, ledger_path: Path) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    new = not ledger_path.exists()
    mm = manifest.get("model_metrics") or {}
    with open(ledger_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(
                [
                    "generated_at",
                    "git_commit",
                    "config_hash",
                    "n",
                    "seed",
                    "rps_test",
                    "accuracy_test",
                    "achieved_tier",
                    "champion_top1",
                    "p_win_top1",
                    "provisional",
                ]
            )
        w.writerow(
            [
                manifest["generated_at"],
                manifest["git_commit"][:12],
                manifest["config_hash"],
                sim.n,
                sim.seed,
                mm.get("rps_test"),
                mm.get("accuracy_test"),
                mm.get("achieved_tier"),
                top_team,
                round(float(sim.p_win.max()), 4),
                sim.provisional,
            ]
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the full simulation pipeline.")
    ap.add_argument("--config", default=None)
    ap.add_argument("--quick", action="store_true", help="Use quick_n from config.")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    cfg = load_config(args.config)
    model = DixonColesModel.load(resolve_path(cfg["output"]["params_path"]))
    sim_inputs = load_sim_inputs(cfg, model)
    params = KnockoutParams.from_config(cfg)
    n = cfg["simulation"]["quick_n"] if args.quick else cfg["simulation"]["n_simulations"]

    print(
        f"Running Monte Carlo: N={n}, seed={cfg['simulation']['master_seed']}, "
        f"mode={params.mode}, provisional={sim_inputs['provisional']}"
    )
    sim = run_simulations(
        model,
        sim_inputs,
        params,
        n=n,
        seed=cfg["simulation"]["master_seed"],
        whatif_sample_size=cfg["simulation"]["whatif_sample_size"],
    )

    manifest = build_manifest(sim, model, cfg, quick=args.quick)
    predictions = build_predictions(sim, model, cfg, manifest, sim_inputs["allocation"])

    out = resolve_path(cfg["output"]["predictions_path"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(predictions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pred_kb = out.stat().st_size / 1024

    outcomes_path = out.parent / "outcomes_sample.json"
    oc_kb = write_outcomes_sample(sim, outcomes_path) / 1024

    top_team = predictions["teams"][0]["team"]
    append_ledger(manifest, sim, top_team, resolve_path(cfg["output"]["ledger_path"]))

    print(
        f"\nWrote {out.relative_to(ROOT)} ({pred_kb:.0f} KB) and "
        f"{outcomes_path.relative_to(ROOT)} ({oc_kb:.0f} KB)."
    )
    print(
        f"Title favourite: {top_team} {predictions['teams'][0]['p_win'] * 100:.1f}% "
        f"(±{predictions['teams'][0]['se_win'] * 100:.2f}%)"
    )
    print(
        "Top 5:",
        ", ".join(f"{d['team']} {d['p_win'] * 100:.1f}%" for d in predictions["teams"][:5]),
    )
    if sim.provisional:
        print("NOTE: predictions flagged PROVISIONAL (official third-place table pending, §8.1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
