# Ising 2D (Glauber) — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Onsager (1944), not tuned. Genuine
agent-based (spin agents, Glauber dynamics).

**Model:** L×L periodic lattice (L=32), spins ±1, Glauber single-spin flips with prob
1/(1+exp(ΔE/T)). Measure |magnetization| after equilibration. Sweep
T∈{1.5,2.0,2.27,2.5,3.0,3.5}. Mean over ≥5 seeds. T_c = 2/ln(1+√2) ≈ 2.269.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Ordered below T_c, disordered above. | |m| > 0.7 at T=1.5 AND |m| < 0.2 at T=3.5 |
| P2 | Transition near T_c≈2.269. | the |m| half-crossing (|m|≈0.5) lies in T∈[2.0, 2.6] |
| P3 | |m| monotone non-increasing in T. | |m|(T) non-increasing across the grid |

**Discipline:** L, T-grid, dynamics, seeds FIXED + metric locked before run; no tuning.
Finite-L rounds the transition — reported honestly. Falsified → MISS.
