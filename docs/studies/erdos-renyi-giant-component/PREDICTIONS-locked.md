# Erdős–Rényi Giant Component — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is the classic ER phase transition, not tuned.
**Network-GENERATION model, not agent-stepping** (disclosed in FINDINGS).

**Model:** G(n,p), n=10,000, mean degree z=p(n−1) swept. Outcome = fraction of nodes in the
largest connected component, mean over ≥10 seeds. Theoretical giant fraction S solves
S=1−e^{−zS}.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Giant component absent below z=1, present above. | largest-comp fraction < 0.05 at z=0.5 AND > 0.40 at z=2.0 |
| P2 | Sharp transition near z=1. | fraction rises from <0.05 (z=0.5) to >0.40 (z=2.0) crossing z=1 |
| P3 | Matches the self-consistent S=1−e^{−zS}. | measured fraction at z∈{1.5,2.0,3.0} within ±0.05 of S |

**Discipline:** n, z-grid, seeds, metric FIXED before run; no tuning. Falsified → MISS.
