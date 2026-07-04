# Kuramoto Synchronization — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Kuramoto (1975), not tuned. Genuine
agent-based (phase-oscillator agents).

**Model:** N=500 oscillators, ω_i~N(0,1). dt=0.05: θ_i += (ω_i + (K/N)Σ_j sin(θ_j−θ_i))·dt.
Order parameter r = |Σe^{iθ}|/N after transient. Sweep K∈{0,0.5,1.0,1.6,2.0,3.0,4.0}. Mean
over ≥5 seeds. Mean-field K_c = 2/(π g(0)); ω~N(0,1) → K_c ≈ 1.60.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Incoherent below K_c, synchronized above. | r < 0.3 at K=0.5 AND r > 0.6 at K=3.0 |
| P2 | Onset near K_c≈1.6. | first K with r>0.3 lies in [1.0, 2.2] |
| P3 | r monotone non-decreasing in K. | r(K) non-decreasing across the grid |

**Discipline:** N, ω distribution, dt, K-grid, seeds FIXED + metric (r) locked; no tuning.
Finite-N gives r~1/√N residual below K_c — reported honestly. Falsified → MISS.
