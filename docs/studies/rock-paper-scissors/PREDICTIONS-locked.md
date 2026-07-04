# Spatial Rock-Paper-Scissors — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Reichenbach, Mobilia & Frey (2007/2008),
not tuned. Genuine agent-based (species agents on a lattice).

**Model:** L×L periodic lattice (L=100), cells empty or species R/P/S. Random events:
predation (R→S→P→R: predator converts prey site to empty), reproduction (fill empty
neighbour), pair-exchange/mobility ε. Run long; outcome = #surviving species + per-species
fractions. ≥5 seeds. Well-mixed control = random global partners (structure destroyed).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Spatial structure preserves coexistence. | spatial (low mobility): all 3 species fraction > 0.05 at end, in ≥80% of seeds |
| P2 | Well-mixed loses biodiversity. | well-mixed: ≥1 species extinct (typically down to 1) |
| P3 | Contrast. | spatial #surviving species > well-mixed #surviving species |

**Discipline:** L, rates, mobility, run length, seeds FIXED + metric locked; the only
difference between arms is locality/structure (FAIR). No tuning. Falsified → MISS.
