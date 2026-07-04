# Voter Model Fixation — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is the classic mean-field voter result, not
tuned. Genuine agent-based (opinion agents step).

**Model:** complete-graph / well-mixed N=1000 agents, binary opinion, initial up-fraction
u. Each step: a random agent adopts the opinion of a random other agent. Run to consensus
(absorbing all-up or all-down). Outcome = P(fixation to all-up) over ≥200 runs per u +
consensus time. Sweep u∈{0.2,0.5,0.8}.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Every run reaches consensus (absorbing). | 100% of runs end all-up or all-down (no perpetual coexistence) |
| P2 | Fixation probability = initial density. | P(all-up) within ±0.07 of u for each u∈{0.2,0.5,0.8} |
| P3 | Mean magnetization is conserved in expectation. | mean final magnetization ≈ 2u−1 (within ±0.10) |

**Discipline:** N, u grid, run count, metric FIXED before run; no tuning. Falsified → MISS.
