# Evolution of Fairness in the Ultimatum Game (Nowak-Page-Sigmund 2000) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Nowak, Page & Sigmund 2000 (Science 289:1773),
not tuned. Genuine agent-based. Verified.

**Model:** evolutionary ultimatum game. Each agent has a genotype (p, q) ∈ [0,1]²: p = offer it
makes as proposer, q = minimum offer it accepts as responder. A proposer offers p to a responder;
accepted iff p ≥ q, giving proposer 1−p and responder p (rejected → both 0). Fitness = accumulated
payoff; reproduce ∝ fitness (Moran/replicator) with small mutation. Reputation weight w ∈ [0,1]:
with prob related to w the proposer KNOWS the responder's acceptance threshold and best-responds
(w=0 = anonymous one-shot; w=1 = full reputation). N≥100, fair random init, ≥10 seeds, long run.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | WITHOUT reputation → rational (selfish) collapse. | w=0: steady-state mean acceptance threshold q̄ < 0.15 AND mean offer p̄ < 0.20 (evolves toward the subgame-perfect near-0 offer from a fair start). |
| P2 | WITH reputation → fair offers evolve. | w ≥ 0.8: steady-state q̄ > 0.30 AND p̄ > 0.30 (offers rise toward a fair split). |
| P3 | Reputation makes the difference (monotone treatment contrast). | (q̄ at w≥0.8) − (q̄ at w=0) ≥ 0.20, and q̄ is non-decreasing in w across the swept values {0, 0.2, 0.5, 1.0}. |

**Discipline:** N, reputation grid w, mutation, init, seeds FIXED + metrics locked; no tuning.
Falsified → MISS. **Distinctness (keep):** like public_goods (an institution rescues a pro-social
outcome that otherwise collapses), but the mechanism is REPUTATION about acceptance thresholds
driving offers to fairness — a genotype-(p,q) responder-rejection game, not a public-goods
contribution+punishment game; the built model has no offer/threshold genotype or reputation channel.
