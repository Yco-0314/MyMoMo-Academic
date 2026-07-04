# Hawk–Dove ESS — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Maynard Smith & Price (1973), not tuned.
Genuine agent-based (strategy agents, replicator/imitation update).

**Model:** well-mixed population; payoffs (H,H)=(V−C)/2, (H,D)=V, (D,H)=0, (D,D)=V/2 (V<C);
random pairings each generation, payoff-proportional reproduction/imitation. Outcome =
steady-state hawk fraction. Mean over ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Converges to ESS p*=V/C (V=2,C=4 → 0.5) from both x0=0.1 and x0=0.9. | both starts → hawk fraction within ±0.05 of 0.5 |
| P2 | p*=V/C tracks the ratio (V=1,C=4 → 0.25). | steady hawk fraction within ±0.05 of 0.25 |
| P3 | The ESS is an attractor. | x0=0.1 and x0=0.9 converge to the same p* (within ±0.05) |

**Discipline:** V/C values, update rule, seeds FIXED + metric locked before run; no tuning.
Falsified → MISS.
