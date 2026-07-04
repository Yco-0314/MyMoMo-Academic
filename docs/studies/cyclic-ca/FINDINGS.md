# Cyclic cellular automaton (Fisch, Gravner & Griffeath 1991) — FINDINGS

**Framing: CELLULAR AUTOMATON (disclosed).** This is a synchronous n-colour cyclic
cellular automaton on a 256×256 torus (Moore-8 neighbourhood, threshold 1), not an
agent-stepping ABM. Deterministic given the seed. Predictions were locked in
`PREDICTIONS-locked.md` BEFORE this run; the clauses below are graded honestly. A
falsified clause is a valid MISS — nothing was tuned to pass.

## Configuration (fixed before running)

| Parameter | Value |
|---|---|
| Grid | 256 × 256 torus |
| Neighbourhood | Moore-8 (orthogonal + diagonal), toroidal wrap |
| Threshold | 1 (one successor neighbour is enough) |
| Rule | colour k advances to (k+1) mod n iff ≥1 Moore neighbour holds (k+1) mod n |
| Steps | 500 |
| Seeds | 2 (seed_base = 0) |
| Colour counts | n = 8 (locked "spiral"), n = 16 (locked "fixation") |
| Plateau window | last 25% of the run (tail-mean change fraction) |
| Period window | 40 further steps; a cell is "active" if it advances on ≥75% of them |

The ONLY knob dialled between the two arms is the number of colours n. Everything else
(grid, neighbourhood, threshold, steps, seeds, metrics) is identical and fixed.

## Verdicts

| # | Clause | Result | Salient number |
|---|---|---|---|
| P1 | Spiral plateau at n=8: tail change-fraction > 0.2, non-decaying | **REPRO** | 1.0000 (> 0.2) |
| P2 | Fixation at n=16: change-fraction decays to < 0.01 | **MISS** | 1.0000 (need < 0.01) |
| P3 | Colour-return period = n at n=8 (± 1) | **REPRO** | 8.0 (= n) |

**2 / 3 locked clauses REPRO. P2 is an honest MISS.**

## What the run showed

### P1 — spiral plateau at n=8 (REPRO)
From the random initial colour soup the field self-organises within a few steps into a
persistently active state. The change fraction dips only to ≈0.61 at step 1 (the initial
soup already has many matched successor neighbours), then climbs and settles at a flat
plateau of **1.0000** by step ~50 and holds it to step 500. Both seeds: tail-mean change
fraction = 1.0000, active fraction = 1.000, second-half activity ≥ first-half (non-decaying).
The system does not freeze — a nonzero (in fact maximal) fraction of cells keeps advancing
forever, exactly the spiral-phase signature. Plateau 1.0000 ≫ the locked 0.2 bar. **REPRO.**

### P3 — colour-return period equals n at n=8 (REPRO)
Over a 40-step window on the settled field, essentially every cell (active fraction 1.000)
advances by exactly one colour on every step (median steps-per-advance = 1.0), so it returns
to its own starting colour every n = 8 steps. The median colour-return period over active
cells is **8.00** for both seeds — dead-on n, well inside the ±1 tolerance. **REPRO.**

### P2 — fixation at n=16 (honest MISS)
The locked clause predicted that n=16 is above the critical colour count n_c and therefore
fixates (change fraction → < 0.01, frozen debris). **It does not.** At n=16 the change
fraction shows a deeper early transient — it dips to ≈0.15 around step 7 (larger n makes an
immediate successor match rarer, so more cells sit still at first) — but it then *recovers*,
climbing back through ≈0.54 at step 50 to a full **1.0000** plateau by step ~100 and holding
it to step 500. Final change fraction = 1.0000 on both seeds (need < 0.01). n=16 is firmly
inside the **spiral** regime, not the fixating one.

**Cause (physics, not a bug).** The FGG spiral→fixation dichotomy exists, but its critical
colour count n_c is a strong function of the neighbourhood range and the threshold. For the
Moore *range-1, threshold-1* rule used here, n_c lies well **above** 16 — a colour sweep on
this exact implementation shows full activity persisting through n≈20 and fixation only
setting in around n≈24–30. The locked design note asserted "n=16 inside the fixating regime";
that assumption is falsified by the dynamics of this specific rule. The correct fixation
demonstration would need either a larger n (≈30) or a shorter interaction range/higher
threshold. We report the MISS rather than move the colour count to make P2 pass — the
faithful rule at the locked n=16 simply does not fixate.

## Determinism
Same seed ⇒ byte-identical colour orbit (the transition rule has no randomness; only the
initial field is seeded). Verified in `tests/classics/test_cyclic_ca.py`
(`test_determinism_same_seed_identical_evolution`, `test_random_grid_same_seed_identical_field`).

## Honesty notes
- Disclosed CELLULAR AUTOMATON, not agent-stepping — same disclosure discipline as the
  BTW-sandpile / Game-of-Life reproductions.
- P3 is graded as a *population* colour-return period over all steadily-cycling cells
  (median over the active mask), not by tracking one hand-picked spiral core.
- No threshold, colour count, grid size, seed, or step count was changed after seeing
  results. P2's MISS stands as the honest outcome for the locked n=16 under this rule.
