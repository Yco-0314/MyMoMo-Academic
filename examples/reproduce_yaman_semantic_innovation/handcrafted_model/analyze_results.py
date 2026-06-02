"""Score the pre-registered predictions against the real experiment output.

Deterministic judge (ADR-013 style): this file only operationalizes the
falsification conditions already locked in
`docs/reproduce/PREDICTIONS-yaman-science.md`. It reads
`results/experiment_results.csv`, takes the final-generation repertoire per
(condition, rep), computes the four cell means, and reports each prediction
hit/miss with its margin. Misses print as misses.
"""
from __future__ import annotations

import csv
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results", "experiment_results.csv")


def _final_rows(rows):
    last_period = max(int(r["period"]) for r in rows)
    return [r for r in rows if int(r["period"]) == last_period], last_period


def main() -> None:
    with open(RESULTS, newline="") as f:
        rows = list(csv.DictReader(f))
    final, last_period = _final_rows(rows)

    # group final repertoire_size + max_level by condition
    by_cond: dict[str, dict[str, list]] = {}
    for r in final:
        d = by_cond.setdefault(r["condition"], {"rep": [], "lvl": [], "score": []})
        d["rep"].append(int(r["repertoire_size"]))
        d["lvl"].append(int(r["max_level"]))
        d["score"].append(float(r["mean_score"]))

    def m(c, k="rep"):
        return st.mean(by_cond[c][k])

    def sd(c, k="rep"):
        v = by_cond[c][k]
        return st.pstdev(v) if len(v) > 1 else 0.0

    order = ["random", "social", "semantic", "sem+soc"]
    print(f"=== final-generation repertoire (gen {last_period}), "
          f"n={len(by_cond[order[0]]['rep'])} reps/cell ===")
    print(f"{'condition':10} {'P_S':>4} {'P_SL':>4} | {'repertoire':>12} "
          f"{'max_level':>10} {'mean_score':>11}")
    cells = {"random": (0, 0), "social": (0, 0.9), "semantic": (0.9, 0), "sem+soc": (0.9, 0.9)}
    for c in order:
        ps, psl = cells[c]
        print(f"{c:10} {ps:>4} {psl:>4} | {m(c):>6.1f} ± {sd(c):>4.1f}  "
              f"{m(c,'lvl'):>8.1f}   {m(c,'score'):>10.0f}")

    R00, R09s, R90, R99 = m("random"), m("social"), m("semantic"), m("sem+soc")
    print("\n=== prediction scorecard ===")

    # P-A: semantic helps in both settings
    a1 = R90 > R00
    a2 = R99 > R09s
    print(f"P-A semantic helps:   R(.9,0)>R(0,0): {R90:.1f}>{R00:.1f} {'HIT' if a1 else 'MISS'} | "
          f"R(.9,.9)>R(0,.9): {R99:.1f}>{R09s:.1f} {'HIT' if a2 else 'MISS'}  "
          f"=> {'HIT' if a1 and a2 else 'MISS'}")

    # P-B: super-additive interaction
    inter = R99 - R90 - R09s + R00
    print(f"P-B synergy:          interaction R99-R90-R09+R00 = "
          f"{R99:.1f}-{R90:.1f}-{R09s:.1f}+{R00:.1f} = {inter:+.1f}  "
          f"=> {'HIT' if inter > 0 else 'MISS'}")

    # P-C: social-only lift << semantic lift
    social_lift = R09s - R00
    semantic_lift = R90 - R00
    pc = social_lift < 0.5 * semantic_lift if semantic_lift > 0 else False
    print(f"P-C no-sem≈random:    social lift {social_lift:+.1f}  vs  semantic lift "
          f"{semantic_lift:+.1f}  (social << semantic?)  "
          f"=> {'HIT' if pc else 'MISS'}")

    # P-D: sem+soc top cell + deepest
    top = max(order, key=lambda c: m(c))
    deepest = max(order, key=lambda c: m(c, "lvl"))
    pd = (top == "sem+soc")
    print(f"P-D sem+soc best:     top repertoire cell = '{top}', deepest = '{deepest}'  "
          f"=> {'HIT' if pd else 'MISS'}")


if __name__ == "__main__":
    main()
