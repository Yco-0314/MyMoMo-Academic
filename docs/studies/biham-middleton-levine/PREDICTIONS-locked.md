# Biham-Middleton-Levine traffic CA (1992) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Biham, Middleton & Levine 1992 (Phys Rev A 46:R6124),
not tuned. **CA (disclosed).** Verified; gate-checked.

**Model:** 2D two-species traffic cellular automaton on a periodic L×L grid. Red (→) cars move east, blue
(↑) cars move north. Cars of one colour all attempt to advance on alternating ticks; a car moves iff the
target cell (with wraparound) is empty, else it stays. Equal numbers of each colour placed at random to a
global density ρ (fraction of occupied cells). Steady-state mean velocity = fraction of cars that move.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Density-driven free-flow→jam transition, ρ_c in [0.30, 0.40]. | asymptotic mean velocity falls from ≈ 1 (free flow) at low ρ to ≈ 0 (gridlock) at high ρ across a narrow window; the transition density ρ_c (velocity crossing 0.5) lies in [0.30, 0.40]. |
| P2 | Sharp two-phase order. | for ρ well below ρ_c (ρ = 0.20) steady-state mean velocity ≥ 0.95 (near-perfect free flow); for ρ well above ρ_c (ρ = 0.55) steady-state mean velocity ≤ 0.05 (near-full gridlock). |
| P3 | Sharp (non-linear) transition, not a gradual decline. | the velocity-vs-density curve is a near-step: the drop from ≥ 0.9 to ≤ 0.1 happens across a density interval ≤ 0.15 wide (much sharper than a linear v = 1−ρ decline). |

**Discipline:** grid size L, densities swept, tie-break/update order, seeds FIXED; metrics locked; no tuning.
Falsified → MISS. gate_design_check: L ≥ 128 to keep finite-size metastability from smearing the step; "well
below/above" bands (0.20 / 0.55) sit clear of the transition window so P2 is not read inside the coexistence
region.
**Distinctness (keep):** intrinsically 2D with two interleaved species on alternating ticks; its signature is
a genuine sharp jamming PHASE TRANSITION (velocity 1→0), absent from nagel_schreckenberg (1D ring, vmax 0..5,
smooth fundamental diagram, no true phase transition).
