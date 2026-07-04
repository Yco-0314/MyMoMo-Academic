# Agent Lotka-Volterra Predator-Prey — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is the Lotka-Volterra predator-prey result,
not tuned. Genuine agent-based.

**Model:** L×L grid (L=100), prey + predator agents. Prey reproduce (with a
growth/carrying-capacity term); predators move, eat prey on their cell (gain energy),
reproduce when energy high, die when energy ≤ 0. Outcome = prey & predator population time
series. ≥5 seeds. (Agent LV is extinction-prone — survival fraction reported honestly.)

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Sustained oscillations, no extinction. | both populations show ≥2 peaks AND neither extinct over the run, in ≥60% of seeds |
| P2 | Predator lags prey. | cross-correlation(prey, predator) maximized at a POSITIVE lag (predator peak after prey) |
| P3 | Persistence (not a single transient spike). | oscillations continue into the last third of the run (multiple peaks throughout) |

**Discipline:** L, rates, energy params, run length, seeds FIXED + metrics locked; no tuning.
Survival fraction across seeds reported honestly. Falsified → MISS.
