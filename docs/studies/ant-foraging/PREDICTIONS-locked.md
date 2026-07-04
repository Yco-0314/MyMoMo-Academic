# Ant Double-Bridge Foraging — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Deneubourg / Goss (1989), not tuned. Genuine
agent-based.

**Model:** nest + food via TWO paths (short Ls, long Ll). Ant agents leave the nest, choose a
branch at the fork with prob ∝ (pheromone+k)^α, traverse it (time ∝ length), deposit pheromone,
return. Pheromone evaporates each tick. Outcome = fraction of traffic on the short path over
time. ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Colony selects the shorter path. | asymmetric (Ll=2·Ls): short-path traffic fraction > 0.8 at steady state in ≥80% of seeds |
| P2 | Symmetric bridges → symmetry breaking. | Ll=Ls: one path wins (final fraction >0.8 on a single path, randomly which across seeds) — NOT a stable 50/50 |
| P3 | Self-reinforcement over time. | short-path fraction rises over the run (monotone trend) |

**Discipline:** lengths, α, k, deposit/evaporation, #ants, seeds FIXED + metric locked; no tuning.
Falsified → MISS.
