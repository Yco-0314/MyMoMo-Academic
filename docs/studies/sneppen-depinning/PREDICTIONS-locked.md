# Sneppen interface depinning (1992) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Sneppen 1992 (Phys Rev Lett 69:3539), not tuned.
**CA (disclosed).** Verified; gate-checked.

**Model:** Sneppen model "A" — a self-organized interface in a quenched random medium. An interface height
h(i) over a periodic 1D substrate of L columns; each site carries a random pinning force. Extremal update:
each step, advance the site with the MINIMUM pinning force (the weakest-pinned point), which increments that
column's height and re-draws random pinning forces there (and enforces a bounded slope / neighbour constraint).
Iterating grows a self-affine interface. Measure the saturated width W(L) vs L and the interface-increment
correlations; an "avalanche" = a run of advances between successive record-breaking pinning thresholds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Self-affine interface. | the saturated width scales W(L) ∝ L^χ with a fitted roughness exponent χ ∈ [0.5, 0.75] (Sneppen depinning class ≈ 0.63), with W_sat monotone increasing in L across the sweep. |
| P2 | Scale-free activity. | the avalanche / jump-size distribution between pinning configurations is heavy-tailed: spans ≥ 2 decades AND max ≥ 100× median nonzero. |
| P3 | Faceted / anticorrelated growth. | nearest-neighbour interface-height increments are spatially ANTICORRELATED — the correlation of adjacent height differences is < 0 — distinguishing self-organized depinning from uncorrelated random deposition (which gives ≈ 0). |

**Discipline:** L grid, slope constraint, pinning-force distribution, transient/collection windows, seeds
FIXED; metrics locked; no tuning. Falsified → MISS. gate_design_check: χ from the W_sat(L) log-log fit is the
honest MISS-risk clause (needs a clean L sweep to saturation); P2/P3 are the more robust scale-free/geometry
signatures.
**Distinctness (keep):** acts on an INTERFACE HEIGHT profile in a quenched random medium — the extremal rule
advances the minimum-pinning site and updates a spatial height field, yielding a measurable roughness exponent
χ. bak_sneppen (same author's extremal idea) has only a fitness ring — no spatial height field, no roughness
exponent.
