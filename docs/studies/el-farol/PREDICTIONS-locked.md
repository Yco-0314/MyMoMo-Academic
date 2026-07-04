# El Farol Bar — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Arthur (1994), not tuned. Genuine
agent-based (bar agents with adaptive predictors).

**Model:** N=100 agents, capacity = 60. Each holds a small set of predictors (history →
forecast); each week each agent uses its currently best-scoring predictor, GOES iff forecast
< 60; realized attendance updates history; predictors re-scored. Run long; outcome =
attendance time series. ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Attendance self-organizes near capacity. | mean attendance (after transient) ∈ [50, 65] |
| P2 | Attendance fluctuates. | std of attendance > 2 (not pinned) |
| P3 | Efficient level emerges without coordination. | the long-run mean sits in [50,65] across seeds (≈ capacity 60) |

**Discipline:** N, capacity, predictor repertoire, run length, seeds FIXED + metric locked;
no tuning. (Arthur's original long-run mean ~56–60.) Falsified → MISS.
