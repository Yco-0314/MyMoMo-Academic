# Abrams-Strogatz Language Competition - FINDINGS

**Run 2026-07-01, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
The fixed runner is `examples/repro_abrams_strogatz_language/run.py`; constants were not
tuned after seeing results. Verdict: **3/3 locked clauses REPRO**.

## Model

This is the two-language Abrams-Strogatz competition model:

- N agents speak A or B.
- One update picks a speaker uniformly.
- A B speaker switches to A with probability `s_A * x_A^alpha`.
- An A speaker switches to B with probability `(1 - s_A) * x_B^alpha`.
- For `alpha > 1`, the mean-field model has stable monolingual endpoints and an
  unstable interior basin boundary.

The implementation uses one seeded RNG chain per run for speaker choice and transition
draws. No empirical language data are used.

## Configuration

| param | value |
|---|---|
| population | N = 500 |
| alpha | 1.31 |
| unequal status | `s_A = 0.6` |
| equal status | `s_A = 0.5` |
| initial A-share grid | 0.2, 0.3, 0.4, 0.5, 0.6 |
| runs per cell | 80 |
| seed base | 0 |
| max sweeps | 1200 |

## Results

### Unequal status sweep (`s_A = 0.6`)

| initial A-share | P(A wins) | P(B wins) | P(interior) | mean final A-share |
|---:|---:|---:|---:|---:|
| 0.2 | 0.225 | 0.775 | 0.000 | 0.253 |
| 0.3 | 0.988 | 0.013 | 0.000 | 0.939 |
| 0.4 | 1.000 | 0.000 | 0.000 | 0.950 |
| 0.5 | 1.000 | 0.000 | 0.000 | 0.950 |
| 0.6 | 1.000 | 0.000 | 0.000 | 0.950 |

The measured A-win basin boundary is **0.2361**. The mean-field unstable fixed point is
**0.2128**, so the error is **0.0232**, inside the locked +/-0.08 band.

### Equal status (`s_A = 0.5`, initial A-share = 0.5)

| P(A wins) | P(B wins) | P(interior) |
|---:|---:|---:|
| 0.5375 | 0.4625 | 0.0000 |

The A-win fraction is 0.0375 away from 0.5, inside the locked +/-0.10 symmetry band.

## Verdicts

| # | Locked clause | Verdict | Salient numbers |
|---|---|---|---|
| P1 | With unequal status, late interior fraction below 0.15 | **REPRO** | interior fraction = 0.0000 |
| P2 | Measured A-win basin boundary within +/-0.08 of mean-field unstable fixed point | **REPRO** | measured = 0.2361, theoretical = 0.2128, error = 0.0232 |
| P3 | Equal status and initial A-share 0.5 gives A-win fraction within +/-0.10 of 0.5 | **REPRO** | P(A wins) = 0.5375, error = 0.0375 |

**3/3 locked clauses REPRO.**

## Interpretation

The reproduction recovers the two core Abrams-Strogatz signatures for this locked
well-mixed stochastic version:

- There is no stable coexistence in the two-language model under the fixed endpoint
  classification; every run in the unequal-status sweep ended near A-only or B-only.
- Higher-status A has a larger basin than B: the A-win boundary sits near 0.236, far below
  0.5 and close to the mean-field unstable fixed point.
- With equal status and symmetric initial condition, the finite ensemble is close to a
  coin flip between A and B.

## Caveats

- This is a synthetic model reproduction, not empirical validation of real language death.
- Endpoint classification uses the locked `x_A <= 0.05` / `x_A >= 0.95` thresholds, not
  literal all-agent monolinguality.
- The measured boundary is linearly interpolated from the locked coarse initial-share
  grid; it is not a refined critical estimate.
- Refutation-tier verdicts mean "not refuted by this gate" when they pass, not verified
  truth.

## Artifacts

- `results.json` contains per-run outcomes, sweep summaries, evaluation metrics, and
  verdict rows.
- `verdict-bundle.json` fingerprints this findings file, the locked predictions, the Batch
  7 design spec, and the result artifact.
