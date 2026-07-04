# Heider Social Balance — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Heider / Antal-Krapivsky-Redner (2005), not
tuned. **Signed-network dynamics (model-orchestrated link/triad updates)** — disclosed.

**Model:** complete signed graph, N=30 nodes, each edge ±1 (random init). Dynamics: repeatedly
pick a random IMBALANCED triad (product of its 3 edge signs < 0) and flip one edge to balance it
(reduce frustration). Run to an absorbing (fully balanced) state. ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Reaches a balanced state. | fraction of balanced triads → 1.0 (absorbing) in ≥90% of seeds |
| P2 | Final state is a valid ≤2-faction balance. | the final signs partition into all-positive OR two factions (every + intra, every − inter) — verified |
| P3 | Frustration is non-increasing. | the count of imbalanced triads is non-increasing under the dynamics |

**Discipline:** N, init, update rule, seeds FIXED + metric locked; no tuning. Falsified → MISS.
