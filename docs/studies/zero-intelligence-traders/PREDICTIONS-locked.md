# Gode–Sunder Zero-Intelligence Traders — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Gode & Sunder (1993), not tuned. Genuine
agent-based (trader agents in a continuous double auction).

**Model:** continuous double auction, M buyers (private values) + M sellers (private costs),
drawn to define a known competitive-equilibrium max surplus. **ZI-C** (budget-constrained):
buyer bids ~U(0, value), seller asks ~U(cost, pmax) — never violates the budget; a trade
clears when a standing bid ≥ ask (at the earlier price). **ZI-U** (unconstrained): bids/asks
~U(0, pmax) ignoring value/cost. Outcome = allocative efficiency = realized surplus / max
competitive surplus. Mean over ≥20 seeds (fresh random value/cost schedules + random orders).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | ZI-C achieves near-100% efficiency. | mean ZI-C efficiency > 0.95 |
| P2 | ZI-U is much lower. | mean ZI-U efficiency < 0.90 |
| P3 | The budget constraint is the cause. | ZI-C − ZI-U mean efficiency ≥ 0.10 |

**Discipline:** value/cost schedule generation, M, price range, order/clearing rules, seeds
FIXED + metric (efficiency) locked before run; the ONLY difference between arms is the budget
constraint (FAIR). No tuning. Falsified → MISS.
