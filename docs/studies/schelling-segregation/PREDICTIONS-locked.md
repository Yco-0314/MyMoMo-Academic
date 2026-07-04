# Schelling 1971 Segregation — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claims are Schelling's (1971), not tuned. Source:
J. Math. Sociol. 1:143–186.

**Model (faithful):** square grid (~50×50), two equal types, ~28% empty cells. An agent is
unhappy if the fraction of its occupied Moore-8 neighbors sharing its type is < tolerance
F=1/3; unhappy agents relocate to a random empty cell. Iterate to a (near-)stable state.
Outcome = mean same-type-neighbor fraction (segregation index).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Mild preference → strong global segregation. | final mean same-type fraction ≥ 0.70 |
| P2 | Segregation rises far above the random baseline. | final − initial(random ≈0.5) ≥ +0.15 |
| P3 | Emergence: global segregation ≫ what any agent demands. | final mean same-fraction ≥ 2 × F (≥ 0.67) |

**Discipline:** grid size, vacancy, F=1/3, Moore-8 fixed before run. Deterministic given a
seed; report mean over seeds. A falsified clause → MISS.
