# q-voter — adversarial review

**tier: deep** (trigger: 2 honest MISSes in the bundle → miss_count≥1). Reviewed against the
verified canonical claim (Castellano, Muñoz & Pastor-Satorras 2009, Phys. Rev. E 80, 041129).

## Mandatory cheap checks
- numeric-provenance: **pass** — headline numbers match results.json.
- fair-control: **pass** — P3 compares ε=0 vs ε=0.15 at identical (N,q,u,runs,sweeps); single variable.
- no-post-lock-drift: **pass** — graded metrics match PREDICTIONS-locked.md at the locked commit; no tuning after results.
- mechanism-aliveness: **pass (with finding)** — ε IS wired into the update (`if rng.random() < epsilon: flip`, q_voter.py:102). The P3 "drop=0.000" is NOT a dead mechanism (see below).
- framing-disclosure: **pass** — genuine binary agents, asynchronous target updates; correctly disclosed.

## Verdict: model is FAITHFUL; both MISSes are honest methodology artifacts, NOT model bugs.

- **P1 MISS (q=1 worst offset 0.092 vs 0.07).** q=1, ε=0 reduces exactly to the linear voter copy
  rule (the built `voter` model passes linearity). With N_RUNS=120 the exit-probability estimate has
  binomial SE ≈ √(0.25/120) ≈ 0.046 at p=0.5; a worst-of-4-densities deviation ≈0.09 is ~2 SE of
  pure Monte-Carlo noise, not a real non-linearity. **Cause: under-powered ensemble (120 runs too few
  for a ±0.07 bar).** Principled fix (result-independent): ~800–1000 runs/cell.
- **P3 MISS (ε=0.15 lowers P(all-up) by 0.000).** For q=4 the mean-field transition sits at
  ε_c = 3/14 ≈ 0.2143 (ordered below) with disorder above 1/4 = 0.25. The locked ε=0.15 is **sub-critical**
  — both arms stay in the ordered/fixating phase, so P(all-up) cannot drop. **Cause: the locked ε does
  not cross the q=4 transition.** Principled fix (provable from the paper, result-independent): test
  ε≈0.35 (> 1/4) vs ε=0 (the verified claim specifies exactly this).
- **P2 REPRO (q=4 nonlinear deviation 0.30 vs 0.08).** The nonlinear/non-voter regime is correctly recovered.

## Discipline check: PASS
The run reported 1/3 REPRO honestly and did NOT tune ε, runs, sweeps, or bars to flip a verdict.
The low REPRO rate reflects a mis-calibrated *locked runner config* (under-powered + sub-critical ε),
not a faithfulness failure. A principled re-lock (v2: 800+ runs, ε=0.35 for P3) would confirm the
diagnosis and is NOT tuning-to-pass (both corrections derive from Monte-Carlo power + the published ε_c,
independent of the observed numbers).

REVIEW COMPLETE
