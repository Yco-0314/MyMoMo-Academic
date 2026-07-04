# Drossel-Schwabl Forest Fire (SOC) - FINDINGS

**Run 2026-06-30, refreshed after fire-size boundary reconciliation. Verdict: 3/3 locked clauses REPRO.**
Predictions were locked in `PREDICTIONS-locked.md`; L, p, f, transient, fire count, fit
method, and gates were not tuned after seeing results.

## Honesty

This is a cellular automaton / self-organized-criticality model, not an agent-decision ABM.
Cells are empty/tree/burning states updated by local rules. There are no agents that
perceive, decide, or act.

## Model And Metric

The literal synchronous CA remains open-boundary and is covered by faithful-rule tests:
burning cells become empty; trees adjacent to burning cells ignite; empty cells grow trees
with probability `p`; trees can ignite by lightning with probability `f`.

The graded fire-size metric uses the standard scale-separated, instantaneous-burning
proxy: between strikes, plant exactly `theta = p/f = 1000` trees on random empty cells;
then one lightning strike burns the whole connected von-Neumann cluster it lands on. The
reconciled component accounting treats that fire-size cluster on the periodic lattice, so
clusters crossing left/right or top/bottom edges are counted as one connected fire.

## Configuration

| param | value |
|---|---|
| L | 128 |
| p | 0.05 |
| f | p/1000 = 0.00005 |
| transient | 5,000 fires |
| recorded fires | 20,000 |
| seed | 0 |
| inits for P3 | `empty`, `trees` |
| fit method | exact discrete power-law MLE, zeta likelihood, fixed kmin = 1 |

## Results

| Quantity | Value |
|---|---:|
| tau, kmin=1 | 1.1990 +/- 0.0022 |
| n_tail | 7,980 |
| tau by kmin | 1.1990 (1), 1.2333 (5), 1.2434 (10), 1.2530 (20) |
| stationary density, empty init | 0.3486 |
| stationary density, trees init | 0.3374 |
| density delta | 0.0112 |
| zero-size fires | 12,020 / 20,000 |
| nonzero span | 4.17 decades, 1 .. 14,900 |
| median nonzero fire size | 41 |
| max / median nonzero | 363.4x |

## Verdicts

| # | Locked clause | Verdict | Salient numbers |
|---|---|---|---|
| P1 | fitted tau in [1.0, 2.5] | **REPRO** | tau = 1.1990 |
| P2 | span >= 2 decades and max >= 100x median nonzero | **REPRO** | 4.17 decades, 363.4x |
| P3 | stationary density from two inits within 0.05 | **REPRO** | delta = 0.0112 |

## Caveats

- This is a synthetic SOC reproduction, not empirical forest validation.
- The Drossel-Schwabl model is only approximately scale-free; large-size deviations and
  finite-size effects are known. The broad tau gate is a coarse refutation-tier check, not
  a precise thermodynamic-limit exponent claim.
- Fire-size accounting is a documented scale-separated proxy. It gives a clean event size
  for one lightning strike, but it is not a real wildfire spread model.

## Artifacts

- `results.json` contains the numeric run outputs and verdict rows.
- `verdict-bundle.json` fingerprints this findings file, the locked predictions, the design
  spec, and the result artifact.
