# Gray-Scott Reaction-Diffusion (Pearson 1993) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Faithful reproduction of Pearson's (F,k) pattern-selection
phase diagram. **Framing: reaction-diffusion PDE on a grid (CA), NOT agent-stepping** (disclosed).
Predictions locked BEFORE running (`PREDICTIONS-locked.md`); config fixed, not tuned.

## What was built
Two chemicals U, V on a 256×256 PERIODIC grid; U + 2V → 3V autocatalysis, feed F of U, kill (F+k)
of V. dU/dt = Du·∇²U − U·V² + F(1−U); dV/dt = Dv·∇²V + U·V² − (F+k)·V, Du=2e-5, Dv=1e-5 (Du/Dv=2),
explicit Euler (5-point periodic Laplacian, dt=1 within the stability limit). The SAME equations are
run at four of Pearson's (F,k) points from a small central V seed; morphology is measured by
connected high-V components + their bounding-box aspect ratios.

## Results (256×256, 15000 steps each)

| regime | (F,k) | # components | median aspect | max aspect | peak spots | std(V) |
|---|---|---|---|---|---|---|
| spots | (0.035, 0.065) | 112 | 1.00 | 2.40 | 112 | 0.089 |
| stripes/maze | (0.030, 0.060) | 215 | 1.17 | 7.62 | 215 | 0.106 |
| self-replicating | (0.026, 0.060) | — | 1.00 | 1.67 | **320** | 0.109 |
| homogeneous | (0.030, 0.070) | 0 | — | — | 15 | **0.00000** |

## Verdicts (refutation tier) — 3/3 REPRO
- **P1 REPRO** — pattern SELECTION by (F,k): the spot regime yields 112 COMPACT blobs (median aspect
  1.00 < 2.0), while the stripe/maze regime is ELONGATED (max aspect 7.62 ≥ 2.0) — the same equations
  produce qualitatively different morphologies selected by (F,k).
- **P2 REPRO** — self-replication: in the mitosis regime the peak spot count reaches 320 (≥ 4), i.e.
  spots repeatedly divide (Pearson's signature).
- **P3 REPRO** — a homogeneous regime exists: at (0.030, 0.070) the V field collapses flat (final
  spatial std = 0.000 < 0.02), no pattern.

No honest MISS. Pearson's central claim — the (F,k) plane is a phase diagram of distinct self-organized
patterns (spots, stripes, self-replication, homogeneous) — reproduces.
