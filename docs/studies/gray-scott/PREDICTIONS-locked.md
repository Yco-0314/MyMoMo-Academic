# Gray-Scott Reaction-Diffusion (Pearson 1993) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Pearson 1993 (Science 261:189), not tuned.
**CA / grid PDE (disclosed, not agent-stepping).** Verified; gate-checked.

**Model:** two chemicals U, V on a 2D periodic grid; U + 2V → 3V. dU/dt = Du·∇²U − U·V² + F·(1−U);
dV/dt = Dv·∇²V + U·V² − (F+k)·V. Du=2e-5, Dv=1e-5 (Du/Dv=2), domain side 2.5, 256×256 grid, explicit
Euler. Seed a small central perturbation. Sweep (F,k) across Pearson's plane.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Pattern SELECTION by (F,k): distinct morphologies from the same equations. | a SPOT regime (≥8 distinct connected high-V components, median aspect ratio < 2.0) AND a STRIPE/labyrinth regime (elongated high-V structures, aspect ratio ≫ 2) at different (F,k) — qualitatively different stationary patterns. |
| P2 | Self-replication (Pearson's signature). | in the self-replicating regime, starting from 1 seeded spot, the maximum spot count reached during the run ≥ 4 (≥2 rounds of division). |
| P3 | A homogeneous (no-pattern) regime exists, separated from pattern regimes. | in the homogeneous regime, final spatial std of V over the grid < 0.02 (field collapses flat, no pattern). |

**Discipline:** Du, Dv, grid, (F,k) points, integrator FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** no built model is a reaction-diffusion PDE; the (F,k) phase diagram of
spots/stripes/self-replication is a continuum morphogenesis phenomenon absent from all built CA
(game_of_life, forest_fire) and lattice models.
