"""Run 3 — does similarity-based GENERALIZATION (P_G>0) reproduce the
semantic benefit the predict-chain (P_G=0) failed to?

Sweeps P_G and a moderate lr (0.001 was dead, 0.2 collapsed). Predictions
P-E/P-F/P-G are locked in docs/reproduce/PREDICTIONS-yaman-science.md
(committed before this runs). Writes results/experiment_run3.csv and prints
the deterministic scorecard.
"""
from __future__ import annotations

import csv
import itertools
import os
import statistics as st
import time

from run_experiment import HERE, run_one

REPS = 16
RESULTS3 = os.path.join(HERE, "results", "experiment_run3.csv")

# label, P_S, P_SL, P_G, lr
GRID = [
    ("random",       0.0, 0.0, 0.0, 0.05),
    ("social",       0.0, 0.9, 0.0, 0.05),
    ("sem_g0",       0.9, 0.0, 0.0, 0.05),   # predict-only reference
    ("sem_g5_lo",    0.9, 0.0, 0.5, 0.02),
    ("sem_g9_lo",    0.9, 0.0, 0.9, 0.02),
    ("sem_g5_hi",    0.9, 0.0, 0.5, 0.08),
    ("sem_g9_hi",    0.9, 0.0, 0.9, 0.08),
    ("semsoc_g9_lo", 0.9, 0.9, 0.9, 0.02),
    ("semsoc_g9_hi", 0.9, 0.9, 0.9, 0.08),
]


def main() -> None:
    os.makedirs(os.path.dirname(RESULTS3), exist_ok=True)
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
    with open(RESULTS3, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {RESULTS3}: {len(rows)} rows in {(time.time()-t0)/60:.1f} min\n")
    _score(rows)


def _score(rows) -> None:
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
        print(f"  {label:14} P_S={ps} P_SL={psl} P_G={pg} lr={lr:<5} | "
              f"rep {m(label):5.1f} ± {sd(label):4.1f}   max_level {lvl:.1f}")

    rnd, rnd_sd = m("random"), sd("random")
    soc = m("social")
    sem_g0 = m("sem_g0")
    sem_gen = {c: m(c) for c in ("sem_g5_lo", "sem_g9_lo", "sem_g5_hi", "sem_g9_hi")}
    best_solo_label = max(sem_gen, key=sem_gen.get)
    best_solo = sem_gen[best_solo_label]
    semsoc = max(m("semsoc_g9_lo"), m("semsoc_g9_hi"))

    print("\n=== scorecard (P-E / P-F / P-G) ===")
    pe = best_solo > rnd + rnd_sd
    print(f"P-E generalization rescues solo: best solo '{best_solo_label}' "
          f"{best_solo:.1f} > random+sd {rnd+rnd_sd:.1f}  => {'HIT' if pe else 'MISS'}")
    pf = best_solo > sem_g0
    print(f"P-F generalization > predict:    {best_solo:.1f} > sem_g0 {sem_g0:.1f}  "
          f"=> {'HIT' if pf else 'MISS'}")
    pg_hit = semsoc > soc and semsoc > best_solo
    print(f"P-G generalization+social synergy: semsoc {semsoc:.1f} > social {soc:.1f} "
          f"AND > best_solo {best_solo:.1f}  => {'HIT' if pg_hit else 'MISS'}")


if __name__ == "__main__":
    main()
