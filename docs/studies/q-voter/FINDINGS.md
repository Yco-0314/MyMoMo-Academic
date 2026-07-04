# q-voter Nonlinear Opinion Dynamics - FINDINGS

**Run 2026-07-01, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
The fixed runner is `examples/repro_q_voter/run.py`; the locked constants were not tuned
after seeing results. Verdict: **1/3 locked clauses REPRO**.

## Model

This is the complete-graph q-voter process from the Castellano-Munoz-Pastor-Satorras
family:

- N persistent binary opinions in {0, 1}.
- One update picks a target uniformly.
- q neighbours are sampled with replacement from all other agents.
- A unanimous q-panel makes the target adopt that panel opinion.
- A split q-panel only acts through epsilon noise, flipping the target with probability
  epsilon.
- q=1 and epsilon=0 is the ordinary linear voter copy rule.
- Runs stop at all-0/all-1 consensus or the locked sweep cap.

The implementation uses one seeded RNG chain per run for target choice, panel sampling,
and epsilon flips. No empirical opinion data are used.

## Configuration

| param | value |
|---|---|
| population | N = 400 |
| runs per cell | 120 |
| seed base | 0 |
| max sweeps | 80000 |
| q=1 linear grid | u = 0.2, 0.5, 0.8 with epsilon = 0 |
| q=4 nonlinear grid | u = 0.2, 0.5, 0.7, 0.8 with epsilon = 0 |
| noisy comparison | q = 4, u = 0.7, epsilon = 0.15 |

## Results

### q=1, epsilon=0

| u | P(all-up) | offset from u | consensus rate | capped rate |
|---:|---:|---:|---:|---:|
| 0.2 | 0.1833 | 0.0167 | 1.000 | 0.000 |
| 0.5 | 0.4083 | 0.0917 | 1.000 | 0.000 |
| 0.8 | 0.7083 | 0.0917 | 1.000 | 0.000 |

The linear-voter reduction is qualitatively present, but the locked +/-0.07 gate is not
met. The worst offset is 0.0917 at u=0.5 and u=0.8, so P1 is a MISS. This is a sampling
precision / locked-threshold miss, not a post-hoc rule change: every run reached consensus,
and the runner was not retuned.

### q=4, epsilon=0

| u | P(all-up) | deviation from linear line | consensus rate | capped rate |
|---:|---:|---:|---:|---:|
| 0.2 | 0.0000 | 0.2000 | 1.000 | 0.000 |
| 0.5 | 0.5583 | 0.0583 | 1.000 | 0.000 |
| 0.7 | 1.0000 | 0.3000 | 1.000 | 0.000 |
| 0.8 | 1.0000 | 0.2000 | 1.000 | 0.000 |

The q=4 exit curve is clearly nonlinear: off-centre deviation reaches 0.3000 while the
midpoint offset is 0.0583, within the locked +/-0.08 midpoint symmetry band. P2 REPRO.

### q=4, u=0.7, noise comparison

| epsilon | P(all-up) | consensus rate | capped rate |
|---:|---:|---:|---:|
| 0.00 | 1.0000 | 1.000 | 0.000 |
| 0.15 | 1.0000 | 1.000 | 0.000 |

At this locked point, epsilon = 0.15 did not lower all-up fixation and did not increase
capped or mixed outcomes. P3 MISS.

## Verdicts

| # | Locked clause | Verdict | Salient numbers |
|---|---|---|---|
| P1 | q=1, epsilon=0: P(all-up) within +/-0.07 of u for u in {0.2, 0.5, 0.8} | **MISS** | worst offset = 0.0917 > 0.07 |
| P2 | q=4, epsilon=0 nonlinear exit curve, with off-centre deviation >=0.08 and E(0.5) within +/-0.08 of 0.5 | **REPRO** | max off-centre deviation = 0.3000; midpoint offset = 0.0583 |
| P3 | q=4, u=0.7: epsilon=0.15 lowers P(all-up) or increases capped/mixed outcomes vs epsilon=0 | **MISS** | P(all-up) 1.0000 -> 1.0000; capped 0.0000 -> 0.0000 |

**1/3 locked clauses REPRO.**

## Interpretation

The harness did catch the distinctive q-voter signature: q=4 creates a nonlinear,
threshold-like exit curve unlike the q=1 voter line. It also caught two limits of the
locked run:

- The q=1 ensemble was not precise enough to pass the pre-locked +/-0.07 tolerance.
- The chosen noisy point was too strongly inside the all-up basin for epsilon=0.15 to
change the coarse fixation outcome.

Both are reported as MISS. The correct next step, if this model is revisited, would be a
new locked rerun with a larger q=1 ensemble or a different pre-registered noise probe; it
would not rewrite these verdicts.

## Caveats

- This is a synthetic model reproduction, not empirical validation.
- The q=1 MISS is compatible with finite ensemble noise at 120 runs per u; it still fails
  the locked threshold and is therefore recorded as MISS.
- The P3 MISS only refutes the locked coarse probe at q=4, u=0.7, epsilon=0.15. It does
  not prove that q-voter noise has no effect in other parts of parameter space.
- Refutation-tier verdicts mean "not refuted by this gate" when they pass, not verified
  truth.

## Artifacts

- `results.json` contains the full seed ensemble and verdict rows.
- `verdict-bundle.json` fingerprints this findings file, the locked predictions, the Batch
  7 design spec, and the result artifact.
