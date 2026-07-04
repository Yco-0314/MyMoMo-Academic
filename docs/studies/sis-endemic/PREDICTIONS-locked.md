# SIS Endemic Threshold — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claims are the standard SIS threshold + endemic
prevalence, not tuned. Genuine agent-based (state agents step).

**Model:** well-mixed N=10,000 agents, S/I. γ recovery prob/tick (e.g. 0.1); β so R0=β/γ;
each tick each S becomes I w.p. 1−(1−β/N)^{I_count} (force βI/N), each I recovers w.p. γ
back to S (no immunity). Seed ~10 I. Run to a steady state; endemic prevalence = mean I/N
over the last ~50 ticks. Mean over ≥20 seeds. Sweep R0∈{0.8,1.0,1.5,2.0,3.0}.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Endemic threshold at R0=1. | prevalence < 0.02 at R0=0.8 AND > 0.30 at R0=2.0 |
| P2 | Endemic prevalence i*=1−1/R0. | measured prevalence at R0∈{1.5,2.0,3.0} within ±0.05 of 1−1/R0 |
| P3 | Monotone in R0, ≈0 below 1. | prevalence non-decreasing across the R0 grid; < 0.02 at R0=0.8 |

**Discipline:** N, γ, R0 grid, seeds, metric + the i*=1−1/R0 formula (from locked R0) FIXED
before run; no tuning. Near-threshold stochastic die-out reported honestly. Falsified → MISS.
