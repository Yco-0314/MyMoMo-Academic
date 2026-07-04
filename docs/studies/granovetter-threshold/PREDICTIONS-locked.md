# Granovetter 1978 Threshold Model — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running any reproduction.** Predictions are Granovetter's
(1978) published riot example, not tuned. Source: AJS 83(6):1420–1443.

**Model (faithful):** N=100 agents, fully mixed (each reads the GLOBAL count already
acting). Agent i acts iff (number already acting) ≥ its integer threshold. Lower
thresholds act first; deterministic iteration to a fixed point.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | **Uniform** thresholds {0,1,2,…,99} (one each) → cascade to **all 100**. | equilibrium count = 100 |
| P2 | **Perturbed**: remove the threshold-1 agent, add a second at threshold 2 (gap at 1) → cascade stalls at the instigator → equilibrium **= 1**. | equilibrium count = 1 |
| P3 | **Distribution, not mean:** the two distributions have nearly identical means (49.5 vs 49.51, Δ≈0.02%) yet outcomes differ ~100×. | \|mean_uniform − mean_perturbed\| < 0.1 AND equilibrium_uniform / equilibrium_perturbed ≈ 100 |

**Discipline:** N=100, the exact uniform set and the exact single-agent perturbation are
fixed BEFORE the run; the equilibria are deterministic (no RNG). A falsified clause is
reported MISS. The headline is P3 (the mean-invariant outcome swing — collective
behavior ≠ aggregation of individual preferences).
