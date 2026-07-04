# Moran Process with Selection — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is the exact Moran (1958) fixation result,
not tuned. Genuine agent-based.

**Model:** well-mixed population N=100, one mutant (fitness r) vs N−1 residents (fitness 1).
Each step: pick one to REPRODUCE ∝ fitness, one to DIE uniformly at random; offspring replaces
the dead. Run to fixation. Outcome = fixation probability of the mutant over ≥2000 runs per r.
Exact: ρ = (1−1/r)/(1−1/rᴺ); neutral r=1 → 1/N; large-N → 1−1/r.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Fixation prob matches ρ=(1−1/r)/(1−1/rᴺ). | measured fixation at r∈{1.05,1.1,1.2,2.0} within ±0.03 of ρ |
| P2 | Neutral → 1/N. | r=1.0 fixation prob ≈ 0.01 (±0.01) |
| P3 | Monotone in r. | fixation prob increases with r across the grid |

**Discipline:** N, r-grid, run count FIXED + metric + the ρ formula (from locked r,N) locked
before run; no tuning. NOTE: the Moran large-N limit is 1−1/r≈s, NOT the Wright-Fisher 2s.
Falsified → MISS.
