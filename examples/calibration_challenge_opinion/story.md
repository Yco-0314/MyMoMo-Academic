# Phenomenon: Deffuant opinion dynamics on a small-world network

## Research motivation

I want to model how opinion polarization vs consensus emerges from local
agent interactions on a sparse social network, and calibrate the
underlying behavioural parameters from observed opinion-trajectory data.

This is the canonical Deffuant–Weisbuch bounded-confidence model. The
goal is parameter estimation from time-series observations of population
opinion distribution.

## Empirical data

Observed time series available at `observed.csv`:

  - 200 rows × 4 columns: `tick`, `mean_opinion`, `opinion_variance`, `n_clusters`
  - Initial state: opinions uniform [0, 1], mean ≈ 0.5, variance ≈ 0.08
  - Final state (200 ticks): consensus or polarization depending on parameters

## Agents

**Citizen** (200 of them):
- `opinion`: continuous, in [0, 1]

## Network structure

Watts-Strogatz small-world:
- Average degree = 8
- Rewiring probability = 0.10
- Set up at initialisation, fixed throughout simulation

## Mechanism

Each tick, for each agent A:
1. Pick one random neighbour B
2. If |opinion_A - opinion_B| < `confidence_threshold`:
   - Both move toward each other by `convergence_rate` × (Δopinion)
3. Else: no interaction

## Parameters to estimate (calibration targets)

| Parameter | Range | Unit |
|---|---|---|
| `confidence_threshold` | 0.05 – 0.50 | opinion units |
| `convergence_rate` | 0.05 – 0.50 | dimensionless fraction |

Fixed structural parameters (NOT to estimate):

| Parameter | Value |
|---|---|
| `num_agents` | 200 |
| `average_degree` | 8 |
| `periods` | 200 |

## Output metrics (must be tracked for calibration)

- `mean_opinion` per tick
- `opinion_variance` per tick
- `n_clusters` per tick (count of opinion clusters separated by gap > 0.10)

## Calibration target

The model should reproduce the observed trajectory of opinion summary
statistics over 200 ticks. Fit metric: MSE between simulated and observed
columns, averaged over ticks and over the 3 metrics.
