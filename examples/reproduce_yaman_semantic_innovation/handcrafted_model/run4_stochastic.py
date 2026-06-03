"""Run 4 — does STOCHASTIC nearest rescue generalization? (one bounded test)

The agent's generalization now samples a soft-nearest owned item
(p ∝ exp(-dist/mean_dist)) instead of the single argmin. Prediction P-H is
locked in docs/reproduce/PREDICTIONS-yaman-science.md (committed before this
runs). If the best semantic-solo cell still does not clear random+sd, the
negative across runs 1-4 is robust. No temperature sweep.
"""
from __future__ import annotations

import csv
import itertools
import os
import statistics as st
import time

from run_experiment import HERE, run_one

REPS = 16
RESULTS4 = os.path.join(HERE, "results", "experiment_run4.csv")

# label, P_S, P_SL, P_G, lr
GRID = [
    ("random",       0.0, 0.0, 0.0, 0.05),
    ("social",       0.0, 0.9, 0.0, 0.05),
    ("sem_g9_lo",    0.9, 0.0, 0.9, 0.02),
    ("sem_g9_hi",    0.9, 0.0, 0.9, 0.08),
    ("semsoc_g9_lo", 0.9, 0.9, 0.9, 0.02),
    ("semsoc_g9_hi", 0.9, 0.9, 0.9, 0.08),
]


def main() -> None:
    os.makedirs(os.path.dirname(RESULTS4), exist_ok=True)
    rows = []
    t0 = time.time()
    total = len(GRID) * REPS
    done = 0
    for (label, ps, psl, pg, lr), rep in itertools.product(GRID, range(REPS)):
        traj = run_one(seed=rep, p_semantic=ps, p_social=psl, p_generalize=pg,
                       lr=lr, train_epochs=20)
        last = traj[-1]
        rows.append({"label": label, "p_semantic": ps, "p_social": psl,
                     "p_generalize": pg, "lr": lr, "rep": rep,
                     "repertoire_size": int(last["repertoire_size"]),
                     "max_level": int(last["max_level"])})
        done += 1
        if rep == REPS - 1:
            print(f"  [{done}/{total}] {label} done", flush=True)
    with open(RESULTS4, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {RESULTS4}: {len(rows)} rows in {(time.time()-t0)/60:.1f} min\n")

    def reps(label):
        return [r["repertoire_size"] for r in rows if r["label"] == label]

    def m(label):
        return st.mean(reps(label))

    def sd(label):
        v = reps(label)
        return st.pstdev(v) if len(v) > 1 else 0.0

    print("=== final repertoire by cell (n=16) ===")
    for (label, ps, psl, pg, lr) in GRID:
        lvl = st.mean([r["max_level"] for r in rows if r["label"] == label])
        print(f"  {label:14} | rep {m(label):5.1f} ± {sd(label):4.1f}   max_level {lvl:.1f}")

    rnd, rnd_sd = m("random"), sd("random")
    best_solo = max(m("sem_g9_lo"), m("sem_g9_hi"))
    print("\n=== scorecard (P-H) ===")
    ph = best_solo > rnd + rnd_sd
    print(f"P-H stochastic nearest rescues solo: best solo {best_solo:.1f} "
          f"> random+sd {rnd+rnd_sd:.1f}  => {'HIT' if ph else 'MISS'}")


if __name__ == "__main__":
    main()
