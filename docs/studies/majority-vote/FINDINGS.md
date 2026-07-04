# Majority-Vote Model (de Oliveira 1992) - FINDINGS

**Run 2026-06-30, refreshed after canonical tie-rule reconciliation. Verdict: 3/3 locked clauses REPRO.**
Predictions were locked before the run in `PREDICTIONS-locked.md`; the q-grid, seeds,
equilibration, measurement window, and grading gates were not tuned after seeing results.

## Model

This is a genuine spin-site ABM on the neutral platform: each lattice site is a
`VoterAgent` carrying spin +1 or -1, while `MajorityVoteModel` owns the periodic
von-Neumann neighbourhood, seeded RNG, random-sequential sweep, and `DataCollector`.

The reconciled local rule is the canonical majority-vote rule:

- `S = sign(sum of the 4 von-Neumann neighbour spins)`.
- If `S != 0`, the site aligns with `S` with probability `1-q`, and takes `-S` with
  probability `q`.
- If `S == 0`, the 2-2 tie uses the canonical `S(0)=0` convention: the current spin flips
  with probability 1/2, independent of `q`.

## Configuration

| param | value |
|---|---|
| lattice | L x L periodic torus, L = 50 |
| q-grid | 0.02, 0.05, 0.075, 0.10, 0.15 |
| seeds per q | 5, seed base 0 |
| equilibration | 300 sweeps |
| measurement | 300 sweeps |
| metric | seed-mean time-averaged absolute magnetization, `|m| = |sum(s)| / N` |

## Results

| q | seed-mean `|m|` | min..max over seeds | std |
|---:|---:|---:|---:|
| 0.020 | 0.905 | 0.743 .. 0.957 | 0.082 |
| 0.050 | 0.621 | 0.204 .. 0.864 | 0.245 |
| 0.075 | 0.607 | 0.588 .. 0.625 | 0.016 |
| 0.100 | 0.103 | 0.054 .. 0.188 | 0.045 |
| 0.150 | 0.046 | 0.041 .. 0.053 | 0.005 |

Measured `|m| = 0.5` half-crossing: **q_c = 0.0803**, close to the canonical square-lattice
reference q_c about 0.075.

## Verdicts

| # | Locked clause | Verdict | Salient numbers |
|---|---|---|---|
| P1 | `|m| > 0.7` at q=0.02 and `|m| < 0.3` at q=0.15 | **REPRO** | 0.905 and 0.046 |
| P2 | half-crossing lies in q in [0.04, 0.12] | **REPRO** | q_c = 0.0803 |
| P3 | `|m|` non-increasing across q-grid | **REPRO** | [0.905, 0.621, 0.607, 0.103, 0.046] |

## Interpretation

The reconciliation matters because the old tie implementation treated a 2-2 neighbourhood
as a randomly invented majority sign and then applied `q`; the canonical `S(0)=0` rule
instead makes ties a q-independent half flip of the current spin. That small local semantic
change changes RNG consumption and the finite-lattice trajectory. With the reconciled rule,
the locked coarse order-disorder signature reproduces cleanly.

## Caveats

- This is a synthetic model reproduction, not empirical validation.
- The q-grid is coarse; the reported q_c is a linear half-crossing between locked grid
  points, not a refined critical-noise estimate.
- The q=0.05 ensemble has high seed spread, so the mean should be read with the per-seed
  values in `results.json`.

## Artifacts

- `results.json` contains the full seed ensemble and verdict rows.
- `verdict-bundle.json` fingerprints this findings file, the locked predictions, the design
  spec, and the result artifact.
