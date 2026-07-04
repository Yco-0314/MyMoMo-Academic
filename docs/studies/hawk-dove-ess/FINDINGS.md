# Hawk-Dove ESS — FINDINGS

**Run 2026-06-30, after predictions were locked** in `PREDICTIONS-locked.md`.
Faithful agent-based reproduction on the neutral platform: each individual is a
`StrategyAgent` holding a discrete Hawk/Dove strategy; generations pair agents for
contests, assign realized payoffs, then update by payoff-proportional imitation.

## Fixed Config

| param | value |
|---|---|
| population | 1000 agents |
| seeds per case | 10 |
| metric | mean steady-state hawk fraction |
| tolerance | ±0.05 from the analytic ESS |
| update | random pair contests + payoff-proportional imitation |

## Results

| case | analytic p*=V/C | measured mean | std | range |
|---|---:|---:|---:|---:|
| V=2,C=4,x0=0.1 | 0.500 | 0.4962 | 0.0108 | [0.4863, 0.5231] |
| V=2,C=4,x0=0.9 | 0.500 | 0.5001 | 0.0127 | [0.4805, 0.5242] |
| V=1,C=4,x0=0.1 | 0.250 | 0.2489 | 0.0058 | [0.2392, 0.2586] |
| V=1,C=4,x0=0.9 | 0.250 | 0.2473 | 0.0076 | [0.2366, 0.2623] |

## Verdicts

| # | Prediction | Result | Number |
|---|---|---|---|
| P1 | V=2,C=4 converges to p*=0.5 from x0=0.1 and x0=0.9 | **REPRO** | worst offset 0.0038 ≤ 0.05 |
| P2 | V=1,C=4 converges to p*=0.25 from x0=0.1 and x0=0.9 | **REPRO** | worst offset 0.0027 ≤ 0.05 |
| P3 | the equilibrium is an attractor from both interior starts | **REPRO** | V=2,C=4 low/high means differ by 0.0039 ≤ 0.05 |

**3 / 3 locked clauses REPRO.**

## Caveats

- This is a finite-population stochastic imitation model, so the steady fraction
  fluctuates around the analytic ESS rather than landing exactly on it.
- The result is synthetic-model reproduction, not real-world animal conflict
  calibration.
- The analytic target `p*=V/C` is used only for grading. It is not fed into the
  agent update rule.
