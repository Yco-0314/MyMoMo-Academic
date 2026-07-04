# Noisy Voter / Kirman Model - FINDINGS

**Run 2026-07-01, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
The fixed runner is `examples/repro_noisy_voter_kirman/run.py`; constants were not tuned
after seeing results. Verdict: **1/3 locked clauses REPRO**.

## Model

This is a complete-graph noisy voter / Kirman process:

- N binary agents hold states in {0, 1}.
- One update picks a target uniformly.
- With probability `a`, the target flips spontaneously.
- Otherwise the target copies a random other agent.
- The spontaneous flip term removes the all-0/all-1 absorbing states of the ordinary
  voter model.
- Stationary behaviour is summarized through magnetization `m = (n_up - n_down) / N`.

The implementation uses one seeded RNG chain per run for target choice, source choice,
and spontaneous-vs-copy branching. No empirical opinion or market data are used.

## Configuration

| regime | N | a | a*N |
|---|---:|---:|---:|
| weak | 400 | 0.001 | 0.4 |
| strong | 400 | 0.020 | 8.0 |
| matched-small | 100 | 0.004 | 0.4 |
| matched-large | 400 | 0.001 | 0.4 |

Shared settings: initial up-fraction `u = 0.5`, 8 seeds, burn-in 20000 updates, 800
samples per seed, record every 20 updates.

## Results

| regime | edge mass `|m| > 0.6` | centre mass `|m| < 0.2` | edge/centre ratio | mean m | std m |
|---|---:|---:|---:|---:|---:|
| weak | 0.2306 | 0.3617 | 0.6376 | 0.0624 | 0.4604 |
| strong | 0.0445 | 0.5275 | 0.0844 | -0.0483 | 0.2782 |
| matched-small | 0.6334 | 0.1183 | 5.3554 | -0.4718 | 0.3252 |
| matched-large | 0.2306 | 0.3617 | 0.6376 | 0.0624 | 0.4604 |

## Verdicts

| # | Locked clause | Verdict | Salient numbers |
|---|---|---|---|
| P1 | Weak noise with a*N < 1 has more edge mass than centre mass | **MISS** | edge - centre = -0.1311 |
| P2 | Strong noise with a*N > 1 has more centre mass than edge mass and `|mean m| <= 0.15` | **REPRO** | centre - edge = 0.4830; mean m = -0.0483 |
| P3 | Matched a*N runs at N=100 and N=400 have edge/centre ratios within 0.35 | **MISS** | ratio diff = 4.7178 |

**1/3 locked clauses REPRO.**

## Interpretation

The strong-noise centred regime reproduced cleanly: at a*N = 8, the stationary trace is
center-heavy and mean magnetization remains near zero. The weak-noise and finite-size
scaling clauses did not reproduce under the locked aggregate gates:

- P1 missed because the aggregate weak trace at N=400, a*N=0.4 spent more mass near the
  centre than at the edges, despite some individual seeds showing herding-like edge
  residence.
- P3 missed because the matched-small N=100 run was much more edge-heavy than the
  matched-large N=400 run even though both had a*N = 0.4.

These misses are retained. A future rerun could lock a longer stationary window, different
sampling cadence, or a more exact theoretical stationary-distribution gate, but that would
be a new locked study rather than a reinterpretation of this one.

## Caveats

- This is a synthetic model reproduction, not empirical validation of financial herding or
  social opinion dynamics.
- The P1/P3 MISS verdicts are about the locked aggregate trace gates, not about every
  possible noisy-voter/Kirman formulation.
- Matched a*N scaling is sensitive to update convention, finite sample windows, and how
  stationary mass is estimated; the broad 0.35 tolerance still failed here.
- Refutation-tier verdicts mean "not refuted by this gate" when they pass, not verified
  truth.

## Artifacts

- `results.json` contains the stationary traces, per-seed summaries, regime metrics, and
  verdict rows.
- `verdict-bundle.json` fingerprints this findings file, the locked predictions, the Batch
  7 design spec, and the result artifact.
