"""Experiment driver for the Yaman synergy reproduction.

The standalone DataCollector overwrites its output per model run (verified:
both runs and scenarios overwrite — only the last survives). So we drive
the sweep here: one (condition, replicate) per Simulator invocation, read
that run's output before the next overwrites it, accumulate a tidy table.

abm-auto stays the runtime (Model/Agent/Environment + FeedforwardLearner);
this file only orchestrates the conditions and aggregates results.

The 2x2 synergy design (P_semantic x P_social), P_generalize=0, is the
minimal falsifiable test of the paper's headline claims (see
docs/reproduce/PREDICTIONS-yaman-science.md, committed BEFORE this runs).

Usage:
  python run_experiment.py            # full design
  python run_experiment.py --time     # one timed run (calibration only)
"""
from __future__ import annotations

import csv
import itertools
import os
import sys
import time

from abm_auto.runtime import Config, Simulator

from core.model import YamanModel
from core.scenario import YamanScenario

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(HERE, "data", "input", "SimulatorScenarios.csv")
OUTPUT = os.path.join(HERE, "data", "output", "Result_Simulator_Environment.csv")
RESULTS = os.path.join(HERE, "results", "experiment_results.csv")

_COLS = ["id", "run_num", "periods", "agent_num", "n_attempts", "seed",
         "p_semantic", "p_social", "p_generalize", "embed_dim", "hidden_dim",
         "learning_rate", "train_epochs"]

# ── design ────────────────────────────────────────────────────────────────
PERIODS = 150
N = 50
ATTEMPTS = 10
REPS = 16
CONDITIONS = [
    # label,      p_semantic, p_social
    ("random",    0.0, 0.0),
    ("social",    0.0, 0.9),
    ("semantic",  0.9, 0.0),
    ("sem+soc",   0.9, 0.9),
]


def _write_scenario(**p) -> None:
    with open(INPUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_COLS)
        w.writeheader()
        w.writerow({c: p[c] for c in _COLS})


def run_one(seed: int, p_semantic: float, p_social: float,
            periods: int = PERIODS, n: int = N) -> list[dict]:
    _write_scenario(id=0, run_num=1, periods=periods, agent_num=n,
                    n_attempts=ATTEMPTS, seed=seed, p_semantic=p_semantic,
                    p_social=p_social, p_generalize=0.0, embed_dim=16,
                    hidden_dim=16, learning_rate=0.001, train_epochs=5)
    config = Config(project_name="YamanSemanticInnovation", project_root=HERE,
                    input_folder="data/input", output_folder="data/output")
    Simulator(config=config, model_cls=YamanModel, scenario_cls=YamanScenario).run()
    with open(OUTPUT, newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    if "--time" in sys.argv:
        t0 = time.time()
        traj = run_one(seed=0, p_semantic=0.9, p_social=0.9)
        dt = time.time() - t0
        last = traj[-1]
        print(f"one sem+soc run: {dt:.2f}s | final repertoire={last['repertoire_size']} "
              f"max_level={last['max_level']}")
        print(f"full design estimate: {len(CONDITIONS)*REPS} runs ~= "
              f"{dt*len(CONDITIONS)*REPS/60:.1f} min")
        return

    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    out_rows: list[dict] = []
    t0 = time.time()
    total = len(CONDITIONS) * REPS
    done = 0
    for (label, p_s, p_sl), rep in itertools.product(CONDITIONS, range(REPS)):
        traj = run_one(seed=rep, p_semantic=p_s, p_social=p_sl)
        for r in traj:
            out_rows.append({
                "condition": label, "p_semantic": p_s, "p_social": p_sl, "rep": rep,
                "period": int(r["period"]),
                "repertoire_size": int(r["repertoire_size"]),
                "max_level": int(r["max_level"]),
                "mean_score": float(r["mean_score"]),
            })
        done += 1
        print(f"  [{done}/{total}] {label} rep={rep} "
              f"final_rep={traj[-1]['repertoire_size']}", flush=True)
    with open(RESULTS, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["condition", "p_semantic", "p_social", "rep",
                                          "period", "repertoire_size", "max_level",
                                          "mean_score"])
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nwrote {RESULTS}: {len(out_rows)} rows, "
          f"{total} runs in {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
