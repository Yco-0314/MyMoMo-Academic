# Abrams-Strogatz Language Competition - PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is the two-language Abrams-Strogatz
competition model with status asymmetry and volatility alpha, not tuned after results.

**Model:** N agents speak A or B. In each update, a B speaker switches to A with
probability `s_A*x_A^alpha`; an A speaker switches to B with probability
`(1-s_A)*x_B^alpha`. For alpha > 1 the interior fixed point is unstable; monolingual
endpoints are stable.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | No stable coexistence in the two-language model. | With s_A=0.6, alpha=1.31, late interior fraction is below 0.15 across the initial-share grid. |
| P2 | Higher-status A has the larger basin. | Measured A-win basin boundary is within +/-0.08 of the mean-field unstable fixed point. |
| P3 | Equal status is symmetric. | With s_A=0.5 and initial A-share 0.5, A-win fraction is within +/-0.10 of 0.5. |

**Discipline:** N, alpha, status values, initial-share grid, run count, cap, and metrics
fixed before run; no tuning. Falsified -> MISS.
