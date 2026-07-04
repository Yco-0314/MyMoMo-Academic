# q-voter Nonlinear Opinion Dynamics - PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is the
Castellano-Munoz-Pastor-Satorras q-voter family on a complete graph / well-mixed
population, not tuned after results.

**Model:** N binary agents with opinions in {0, 1}. One update picks a target and q
neighbours sampled with replacement from all other agents. If the q-neighbour panel is
unanimous, the target adopts that panel opinion. If the panel is not unanimous, the
target flips with probability epsilon. q=1, epsilon=0 reduces to the linear voter
copying process.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | q=1 reduces to linear voter fixation. | At u in {0.2, 0.5, 0.8}, P(all-up) is within +/-0.07 of u. |
| P2 | q>1 produces a nonlinear exit-probability curve. | q=4, epsilon=0 differs from the q=1 line by at least 0.08 at one off-centre u, while E(0.5) remains within +/-0.08 of 0.5. |
| P3 | noise weakens ordered fixation. | At q=4 and u=0.7, epsilon=0.15 lowers P(all-up) or increases capped/mixed outcomes relative to epsilon=0. |

**Discipline:** N, u-grid, q-grid, epsilon values, run count, cap, and metric fixed
before run; no tuning. Falsified -> MISS.
