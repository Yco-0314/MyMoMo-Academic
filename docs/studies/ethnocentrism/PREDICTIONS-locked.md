# Axelrod-Hammond Ethnocentrism — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Hammond & Axelrod (2006), not tuned.
Genuine agent-based.

**Model:** L×L grid (L=50) with empty sites. Each agent: TAG (1 of 4) + strategy = (coop
with same tag?, coop with diff tag?) → 4 phenotypes (ethnocentric C-in/D-out, humanitarian
C/C, egoist D/D, traitorous D-in/C-out). Each tick: immigration to a random empty site;
pairwise one-shot PD with 4 NN (give-cost c=0.01, receive-benefit b=0.03); reproduction ∝
accumulated payoff (offspring inherits tag+strategy, small mutation, into an empty neighbour);
death at a fixed rate. Run long; outcome = strategy shares + in/out-group cooperation. ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Ethnocentric dominates. | ethnocentric is the most common strategy at steady state (largest share) |
| P2 | Ethnocentric share is large. | ethnocentric share > 0.40 |
| P3 | In-group favoritism. | in-group cooperation rate > out-group cooperation rate |

**Discipline:** L, tags, b/c, rates, run length, seeds FIXED + metrics locked; no tuning.
Falsified → MISS.
