# Diffusion-Limited Aggregation (Witten-Sander 1981) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Witten & Sander 1981 (PRL 47:1400), not tuned.
Agent-based (random-walk particles). Verified; gate-checked (wide band for finite-size/anisotropy).

**Model:** single seed at the origin; particles launched one at a time from a birth circle beyond the
current cluster, unbiased random walk (off-lattice radial preferred; kill/relaunch beyond ~2-3× cluster
radius), stick permanently + irreversibly on first contact with the cluster. Grow ~2000-20000 particles,
≥ a few seeds. Fit D from enclosed mass M(r) ~ r^D over the middle decade (drop innermost few shells +
noisy outer shell).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Self-similar fractal with non-integer mass dimension. | measured mass dimension D ∈ [1.55, 1.90] (paper's 1981 estimate ~1.66; canonical off-lattice 1.71; wide band absorbs finite-size + lattice anisotropy). |
| P2 | Fractal, NOT compact. | power-law slope D ≤ 1.85 (< 2.0 = filled disk) over the fitting window; average density inside radius r DECREASES with r (screened/porous interior). |
| P3 | Tip-dominated growth by diffusive screening. | fraction of new particles attaching in the outer shell (r > 0.75·R_max) ≥ 0.60, exceeding the area-uniform null (~0.44) — branched screened structure, not uniform filling. |

**Discipline:** seed, walk rule, sticking, cluster size, seeds FIXED + metrics locked; no tuning. Do NOT
tighten D to 1.71±0.05 at accessible size (finite-size trap). Falsified → MISS. **Distinctness (keep):**
btw_sandpile / forest_fire / game_of_life are CA that fill space at D=2 with no diffusing walkers and no
seed-anchored radial growth front; none can produce a branched aggregate with D∈[1.55,1.90] or the
tip-screening signature.
