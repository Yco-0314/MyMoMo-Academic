# Diffusion-Limited Aggregation (Witten-Sander 1981) — FINDINGS

**Status: 2/3 locked clauses REPRO.** The core Witten-Sander result — a self-similar fractal with
mass dimension D ≈ 1.66 — reproduces. **On-lattice** (square lattice, von-Neumann sticking), agent-based
(random-walk particles); on-lattice geometry disclosed (mild anisotropy). Predictions locked BEFORE
running (`PREDICTIONS-locked.md`); D band [1.55,1.90] not tightened; not tuned.

## What was built (and a bug that was fixed)
A single seed at the origin; particles launched one at a time from a birth circle just outside the
cluster, doing an unbiased von-Neumann (4-direction) random walk; a walker STICKS permanently in its
current cell the moment a neighbour cell is occupied; strays beyond a kill circle are relaunched.

**On-lattice was chosen (the lock permits it) after an off-lattice draft had a real overlap bug** — its
tangent placement projected each walker to contact distance from the ONE touched particle, which could
leave it closer than contact to ANOTHER particle (a test found a 0.416 gap vs the 1.0 contact distance).
On the lattice each cell is occupied-or-empty, so particles can NEVER overlap and every stuck particle
sits at exactly one lattice step from the cluster — the invariant is structural. 8/8 faithfulness tests
pass, including an explicit no-overlap / min-separation check.

## Results (6000 particles, 4 seeds)
- mean fractal (mass) dimension **D = 1.660** (per-seed 1.653 / 1.668 / 1.596 / 1.723), fit R² > 0.99.
- interior density DECREASES from inner to outer window in all seeds (porous / screened interior).
- outer-shell (r > 0.75·R_final) attachment fraction = 0.098.

## Verdicts (refutation tier) — 2/3 REPRO
- **P1 REPRO** — fractal mass dimension D = 1.660 ∈ [1.55, 1.90] (canonical on-lattice ~1.67, off-lattice
  1.71). This is Witten-Sander's central claim: M(r) ~ r^D with non-integer D < 2.
- **P2 REPRO** — fractal, not compact: D = 1.660 ≤ 1.85 AND interior density decreasing (all seeds).
- **P3 MISS (honest metric-design miss).** outer-shell attachment fraction = 0.098 vs the 0.60 bar. The
  tip-screening MECHANISM is genuinely present (the decreasing density in P2 is exactly its fingerprint),
  but the locked metric — attachment radius vs the FINAL R_max — understates it: most particles stuck
  early when the cluster was small, so their (correct, tip-of-the-current-cluster) attachment radius is
  well below 0.75·R_FINAL. The faithful metric would compare each attachment to the cluster radius AT THE
  TIME OF STICKING. Reported as MISS rather than re-defining the metric post-hoc to force a pass.

The load-bearing Witten-Sander claim — a fractal aggregate with D ≈ 1.66 — reproduces cleanly, and the
overlap bug that would have biased D upward is fixed by the on-lattice construction.
