# Miller-Page Standing Ovation — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Miller & Page (2004), not tuned. Genuine
agent-based.

**Model:** L×L auditorium (L=40) of audience agents. Each perceives quality q_i = signal s +
noise ε_i (ε~N(0,σ), σ=0.3); STANDS initially iff q_i > threshold T=0.5. Then iterate conformity:
each agent stands iff ≥ half the agents in its viewing neighbourhood are standing (Moore-8 /
front-cone — document); run to a fixed point. Compare to a no-conformity baseline (initial
standing only). ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | High quality → ovation. | s=0.8 (> T): final standing fraction > 0.8 |
| P2 | Low quality → no ovation. | s=0.2 (< T): final standing fraction < 0.2 |
| P3 | Spatial conformity amplifies. | at an intermediate signal, the conformity dynamics move the standing fraction toward an extreme (final ≠ initial pre-conformity fraction by a clear margin) |

**Discipline:** L, T, σ, neighbourhood, conformity rule, seeds FIXED + metric locked; no tuning.
Falsified → MISS.
