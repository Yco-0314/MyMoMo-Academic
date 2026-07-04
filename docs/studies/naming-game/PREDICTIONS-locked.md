# Naming Game — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is the minimal Naming Game (Baronchelli et al.
2006 / Steels), not tuned. Genuine agent-based (namer agents, pairwise interactions).

**Model:** N=1000 agents, each a vocabulary (set of names) for one object, initially empty.
Each step: random speaker + hearer; speaker utters a name (random from its inventory, or
invents a fresh one if empty); if the hearer HAS that name → success (both collapse to just
that name); else failure (hearer adds it). Run to global consensus (all N share exactly one
common name) or a step cap. Outcome = consensus reached + #distinct names and total
vocabulary over time. Mean over ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Reaches global consensus from local interactions. | 100% of runs reach a single name held by all N (within the cap) |
| P2 | Distinct-name count peaks then collapses to 1. | max distinct names > 1 AND final distinct names = 1 |
| P3 | Total vocabulary peaks above N then collapses to N. | peak total words > N AND final total words = N (each agent ends with exactly 1) |

**Discipline:** N, interaction rule, step cap, seeds FIXED + metrics locked before run; no
tuning. Falsified → MISS.
