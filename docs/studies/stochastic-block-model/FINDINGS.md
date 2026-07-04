# Stochastic Block Model Detectability Threshold — FINDINGS

**Status: 3/3 locked clauses REPRO.** Synthetic network-generation plus
community-inference reproduction of the two-block stochastic block model detectability
claim. Predictions were locked before running; the detector receives only the adjacency
matrix, not the planted labels.

## What was built

The generator creates two equal planted groups with average degree `c = 3`. Within-group
edges appear with rate `c_in / N`; between-group edges with rate `c_out / N`; and
`epsilon = c_out / c_in`, with `c_in + c_out = 2c`.

The theoretical threshold for two equal groups is:

`epsilon_c = (sqrt(c) - 1) / (sqrt(c) + 1) = 0.268` at `c = 3`.

Community recovery uses a **Bethe Hessian spectral detector**:

- build `H(r) = (r^2 - 1)I - rA + D`, with `r = sqrt(mean_degree)`;
- compute the lowest algebraic eigenvectors;
- use the second negative vector when present, because the most negative vector is often
  localized in sparse graphs;
- split by the vector median to get a balanced two-label partition.

The planted labels are used only after detection to score overlap:

`Q = 2 * max(accuracy, 1 - accuracy) - 1`.

Matched Erdős-Rényi controls use the same N and realized mean degree, but no planted
community structure.

## Locked config

| Param | Value |
|---|---|
| N | 5000 |
| groups | 2 equal groups |
| c | 3.0 |
| epsilon grid | 0.05, 0.10, 0.15, 0.20, 0.35, 0.50 |
| seeds | 0-4 |
| detector | Bethe Hessian spectral detector |
| control | matched ER at same realized mean degree |

## Results

| epsilon | Mean overlap Q | Matched ER Q | Mean degree |
|---:|---:|---:|---:|
| 0.05 | 0.8818 | 0.0128 | 3.002 |
| 0.10 | 0.7590 | 0.0086 | 3.003 |
| 0.15 | 0.6176 | 0.0144 | 3.003 |
| 0.20 | 0.4634 | 0.0102 | 3.002 |
| 0.35 | 0.0168 | 0.0061 | 3.002 |
| 0.50 | 0.0245 | 0.0075 | 3.012 |

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| P1 | Deep-detectable recovery | Q(eps=0.1) >= 0.5; matched ER Q <= 0.1 | Q=0.7590; ER=0.0086 | **REPRO** |
| P2 | Deep-undetectable failure | Q(eps=0.5) <= 0.15 and near ER | Q=0.0245; ER=0.0075 | **REPRO** |
| P3 | Detectability sweep | Q(0.05)-Q(0.50) >= 0.4; low eps >=0.5; eps=0.50 <=0.15 | gap=0.8573; low eps pass; eps=0.50 pass | **REPRO** |

## Honest interpretation

- **P1 reproduces.** At `epsilon = 0.10`, well below the theoretical threshold
  `epsilon_c = 0.268`, the Bethe Hessian detector recovers the planted partition with
  mean overlap **Q = 0.7590**. A matched ER graph at the same realized mean degree gives
  **Q = 0.0086**, essentially chance. This shows the detector is using planted community
  structure in the SBM, not a generic sparse-graph artifact.

- **P2 reproduces.** At `epsilon = 0.50`, well above threshold, mean overlap falls to
  **Q = 0.0245**, indistinguishable from the matched ER control (**Q = 0.0075**) under
  the locked tolerance. The planted partition still exists in the data-generating
  process, but it is algorithmically unrecoverable by this spectral detector at this
  signal level.

- **P3 reproduces the phase-transition sweep.** Overlap drops from **0.8818** at
  `epsilon = 0.05` to **0.0245** at `epsilon = 0.50`, a gap of **0.8573**. The sweep is
  monotone in the expected broad sense: strong recovery below the threshold, marginal
  recovery near `epsilon = 0.20`, and chance-level recovery above it. The finite-N
  transition is smeared, as expected, so the gate does not require the empirical
  crossover to sit exactly at 0.268.

- **Detector boundary:** this is not an oracle detector. The implementation uses the
  adjacency matrix and realized mean degree only. Labels enter only in the final overlap
  calculation and in the matched-ER no-signal control. The second negative Bethe Hessian
  eigenvector is used because sparse graphs often have a localized most-negative vector;
  this choice is fixed in the tests and not tuned per epsilon.

## Bottom line

The reproduction captures the core SBM detectability phenomenon: below threshold,
community recovery is strong; above threshold, the planted partition is present but
practically unrecoverable and matches the ER no-signal baseline. Final verdict:
**3/3 REPRO**.

## Source

Decelle, A., Krzakala, F., Moore, C. & Zdeborová, L. (2011). *Asymptotic analysis of
the stochastic block model for modular networks and its algorithmic applications.*
Physical Review E 84:066106. doi:10.1103/PhysRevE.84.066106.

Scope: synthetic network-generation plus community-inference reproduction. No real-world
data. The contribution is whether the lock-first harness can reproduce a structural
detectability threshold and distinguish it from a matched no-community control.
