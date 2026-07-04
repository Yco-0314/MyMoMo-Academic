# Sznajd 2000 Opinion Dynamics — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Sznajd-Weron & Sznajd's (2000), not tuned.
Source: Int. J. Mod. Phys. C 11(6):1157–1165.

**Model (faithful, 2D variant):** L×L periodic lattice, opinions ∈ {−1,+1}, initial
up-density d. Rule ("united we stand"): pick a random 2×2 plaquette; if all four share the
same opinion, set all 8 of their outer neighbours to that opinion; else no change. Run to a
frozen state (or a large step cap). Outcome = final magnetization (mean opinion) + which
consensus. Average over ≥20 seeds per d.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | The system reaches complete consensus. | from d=0.5: |final magnetization| ≥ 0.95 in ≥80% of runs |
| P2 | Phase transition at d = 1/2. | P(all-UP) ≈ 0 for d≤0.4 and ≈1 for d≥0.6 (steep step at 0.5) |
| P3 | Majority initial opinion wins. | P(all-UP \| d=0.7) > 0.8 AND P(all-UP \| d=0.3) < 0.2 |

**Discipline:** L, the d-grid, the plaquette rule, frozen-state stop, seeds FIXED + the
metric (final magnetization / P(all-up)) locked before the run; no tuning. Falsified → MISS.
