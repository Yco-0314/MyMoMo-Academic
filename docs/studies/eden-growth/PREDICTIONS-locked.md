# Eden Growth Model (KPZ interface) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Eden 1961 + Family-Vicsek/KPZ scaling, not tuned.
Hybrid (stochastic particle growth on a grid). Verified; gate-checked (wide KPZ exponent tolerances).

**Model:** a cluster grows by adding one particle at a time to a RANDOMLY chosen unoccupied site on the
current perimeter (all perimeter sites equally likely). Flat 1+1D strip geometry: lattice strip of width
L (128-512), periodic along the width, growing upward from a seed row; height h(x,t) = max occupied
height in column x; interface width W(L,t) = std of h(x,t). ≥ several seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | COMPACT bulk (D=2), NOT a fractal (the DLA contrast). | bulk fractal dimension D ≥ 1.85 (target 2.0); interior density non-decaying (std/mean of annular density < 0.15). |
| P2 | Rough interface grows as a power law (KPZ β=1/3). | growth exponent β (W ~ t^β before saturation) ∈ [0.24, 0.42] (KPZ target 0.333). |
| P3 | Saturated width scales with system size (KPZ α=1/2). | roughness exponent α (W_sat ~ L^α) ∈ [0.35, 0.60] (KPZ target 0.5); W_sat increases monotonically with L. |

**Discipline:** L grid, growth rule, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** the DLA contrast is the whole point — Eden fills space (D=2 compact bulk) while
its INTERFACE is a rough self-affine KPZ surface (α≈0.5, β≈0.33); DLA is D≈1.71 fractal in the bulk. No
built model has a growing rough interface with KPZ exponents.
