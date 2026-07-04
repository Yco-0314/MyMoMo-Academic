# Ant-trail flow CA (2002) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Chowdhury, Guttal, Nishinari & Schadschneider 2002
(J Phys A 35:L573), not tuned. **CA (disclosed).** Verified; gate-checked.

**Model:** single-lane exclusion process on a periodic ring of L sites (NaSch-like, vmax = 1) coupled to a
pheromone field. Each site carries a pheromone mark that ants deposit as they pass and that evaporates with
probability f per step. An ant's hop probability is enhanced (Q → q) when pheromone is present on the target
site ahead. Fundamental diagram: flow = ρ·⟨v⟩ vs density ρ.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Velocity plateau (loose clusters). | with pheromone coupling active (small evaporation f) the mean velocity is roughly flat — it varies < 20% across an intermediate density band [0.2, 0.5] — instead of the steady monotone decline of plain NaSch. |
| P2 | Right-shifted / asymmetric flow peak. | the density of maximum flow ρ* lies at ρ* > 0.5 (peak skewed right), unlike the low-/mid-density symmetric NaSch peak at ρ ≈ 0.5. |
| P3 | Pheromone control recovers NaSch. | increasing evaporation f toward 1 removes the anomaly: the flow-peak density ρ* moves back toward ≈ 0.5 and the velocity plateau of P1 disappears (velocity variation across [0.2,0.5] rises back above 20%). |

**Discipline:** L, hop probabilities Q/q, evaporation grid f, densities, seeds FIXED; metrics locked; no
tuning. Falsified → MISS. gate_design_check: P1/P2 are the anomalous-diagram signatures and are the honest
MISS-risk clauses (the right-shift can be modest); f→1 recovery (P3) is the robust control. Peak density read
from the fundamental-diagram argmax on a fixed ρ grid.
**Distinctness (keep):** couples a NaSch-like exclusion process to an evaporating pheromone field, giving a
qualitatively ANOMALOUS fundamental diagram (velocity plateau + right-shifted flow peak) — distinct from
nagel_schreckenberg (no pheromone, symmetric diagram) and ant_foraging (2D stigmergy, not a 1D diagram).
