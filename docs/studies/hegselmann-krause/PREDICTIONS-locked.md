# Hegselmann–Krause Opinion — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Hegselmann & Krause (2002), not tuned.
Genuine agent-based (synchronous opinion agents).

**Model:** N=1000 agents, opinions ~U[0,1]. Synchronous update:
x_i ← mean{x_j : |x_i−x_j| ≤ ε} (incl. self). Run to a stationary state; count final
clusters (tol 0.01). Sweep ε∈{0.05,0.1,0.15,0.2,0.3}. Mean over ≥20 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Consensus above the confidence threshold. | ε≥0.25 → 1 cluster (consensus) in ≥90% of runs |
| P2 | #clusters non-increasing as ε rises. | mean #clusters monotonically non-increasing across the ε grid |
| P3 | Fragmentation at low ε. | ε≤0.1 → ≥2 clusters (mean) |

**Discipline:** N, ε-grid, cluster tol, seeds FIXED + metric locked before run; no tuning.
Falsified → MISS. (Distinct from Deffuant: synchronous all-neighbours-average vs pairwise.)
