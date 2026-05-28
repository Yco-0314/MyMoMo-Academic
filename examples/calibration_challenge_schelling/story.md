# Phenomenon: Schelling residential segregation

## Research motivation

I want to model how individual tolerance preferences produce macro-level
residential segregation on a 2D grid, and calibrate the tolerance threshold
from observed segregation dynamics.

This is the canonical Schelling (1971) segregation model. Goal: parameter
estimation of the tolerance threshold from time-series of segregation metrics.

## Empirical data

Observed time series at `observed.csv`:
  - 100 rows × 4 columns: `tick`, `n_unhappy`, `segregation_index`, `fraction_segregated`
  - Initial: random placement → ~50% same-group neighbours on average, many unhappy
  - Final: segregation increases, unhappy count drops to near zero

## Agents

**Resident** (~360 of them on a 20×20 grid, 90% density):
- `group`: 0 or 1 (two-group)

## Spatial structure

20 × 20 Moore-neighbourhood grid:
- 90% density (360 of 400 cells occupied)
- Toroidal wrap-around (default Melodie grid)

## Mechanism

Each tick:
1. For each agent, compute fraction of same-group neighbours.
2. If fraction < tolerance, the agent is unhappy.
3. Unhappy agents move to a random empty cell.
4. Continue until no one is unhappy or max periods reached.

## Parameters to estimate (calibration targets)

| Parameter | Range | Unit |
|---|---|---|
| `tolerance` | 0.10 – 0.90 | fraction of same-group required |

Fixed structural parameters:

| Parameter | Value |
|---|---|
| `grid_width` × `grid_height` | 20 × 20 |
| `density` | 0.90 |
| `fraction_minority` | 0.50 |
| `periods` | 100 |

## Output metrics (must be tracked for calibration)

- `n_unhappy` per tick
- `segregation_index` per tick (mean fraction of same-group neighbours)
- `fraction_segregated` per tick (fraction of agents with > 0.75 same-group)

## Calibration target

Reproduce the observed trajectory of segregation metrics. Fit metric: MSE
between simulated and observed columns, averaged over ticks and metrics.
