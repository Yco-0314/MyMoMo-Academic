# Eden Growth (KPZ interface) — FINDINGS

**Status: 3/3 locked clauses REPRO.** The Eden signature — a COMPACT bulk (D≈2) with a ROUGH,
self-affine KPZ interface (β≈1/3, α≈1/2) — reproduces, textbook-exact. Framing: hybrid (stochastic
particle growth on a grid). Predictions locked BEFORE running; the KPZ exponent bands are the locked
(wide) tolerances, not tuned.

## What was built
- **Radial Eden** (P1): a cluster grows by adding one particle at a time to a randomly chosen
  unoccupied perimeter site; the bulk fills space at dimension ≈2 (unlike the DLA fractal at 1.66).
- **Flat 1+1D strip Eden** (P2/P3): a strip of width L grows upward from a flat seed row; the
  interface width W(L,t) = std of the column heights roughens with Family-Vicsek / KPZ scaling.

## Results
- **P1 compact bulk**: mean bulk fractal dimension **D = 1.971** (≥ 1.85, target 2.0); interior
  density non-decaying — space-filling, NOT a fractal.
- **P2 KPZ growth exponent**: fitting W(t) ~ t^β over the pre-saturation window at L=512 gives
  **β = 0.346** (KPZ 1/3 = 0.333; R² = 0.996).
- **P3 KPZ roughness exponent**: fitting W_sat ~ L^α across L ∈ {64,128,256,512} (W_sat =
  2.73, 4.22, 6.35, 8.48, monotone) gives **α = 0.549** (KPZ 1/2 = 0.5; R² = 0.992).

## Verdicts (refutation tier) — 3/3 REPRO
- **P1 REPRO** — D = 1.971 ≥ 1.85 + density non-decaying (compact bulk, the DLA contrast).
- **P2 REPRO** — β = 0.346 ∈ [0.24, 0.42] (KPZ 1/3).
- **P3 REPRO** — α = 0.549 ∈ [0.35, 0.60] (KPZ 1/2), W_sat monotone in L.

No honest MISS. The Eden result — compact bulk + a rough interface in the KPZ universality class
(β≈1/3, α≈1/2) — reproduces; the DLA/Eden contrast (fractal-bulk vs compact-bulk-rough-surface) is
sharp and correct.
