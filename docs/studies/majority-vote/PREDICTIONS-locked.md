# Majority-Vote Model — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is de Oliveira (1992), not tuned. Genuine
agent-based (spin agents).

**Model:** L×L periodic lattice (L=50), spins ±1. Each update a spin takes its 4-NN
majority sign with prob (1−q), the minority with prob q (noise). Measure |magnetization|
after equilibration. Sweep q∈{0.02,0.05,0.075,0.10,0.15}. Mean over ≥5 seeds. Canonical
square-lattice q_c ≈ 0.075 (reported vs measured).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Ordered at low noise, disordered at high. | |m| > 0.7 at q=0.02 AND |m| < 0.3 at q=0.15 |
| P2 | Order–disorder transition near q_c. | the |m| half-crossing (|m|≈0.5) lies in q∈[0.04, 0.12] |
| P3 | |m| monotone non-increasing in q. | |m|(q) non-increasing across the grid |

**Discipline:** L, q-grid, update rule, seeds FIXED + metric locked before run; no tuning.
Measured q_c reported vs canonical ~0.075. Falsified → MISS.
