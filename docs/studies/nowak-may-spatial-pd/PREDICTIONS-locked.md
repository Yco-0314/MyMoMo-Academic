# Nowak & May 1992 Spatial Prisoner's Dilemma — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claims are Nowak & May (1992), not tuned. Source:
Nature 359:826–829.

**Model (faithful):** square lattice (~99×99, periodic), each site AllC or AllD. Payoff vs
each of the 8 Moore neighbors: T=b (1<b<2), R=1, P=0, S=0; each agent accumulates payoff
over its neighbors (Nowak-May self-interaction convention as implemented — document the
choice), then adopts the strategy of the highest-scoring agent in its neighborhood
(including itself). Synchronous update. Run to a statistical steady state; outcome =
cooperator fraction (mean over late ticks). Temptation b=1.85 (the canonical value).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Spatial cooperation PERSISTS via clusters (not extinct) at b=1.85. | steady-state cooperator fraction > 0.10 |
| P2 | Well-mixed control (neighbours re-randomized each step) collapses to all-defect. | well-mixed cooperator fraction < 0.02 |
| P3 | Contrast: spatial structure sustains cooperation that well-mixing kills. | spatial fraction ≫ well-mixed (ratio ≥ 5×, or spatial>0.1 & well-mixed<0.02) |

**Discipline:** lattice size, b=1.85, Moore-8, update rule, init density fixed before run.
Report mean cooperator fraction over late ticks + seeds. A falsified clause → MISS.
(Canonical: b=1.85 spatial ≈ 0.31 cooperators; reported as measured.)
