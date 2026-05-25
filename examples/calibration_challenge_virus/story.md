# Phenomenon: SIR-like virus diffusion on a sparse social network

## Research motivation

I want to build an agent-based model of a virus spreading on a network of
150 individuals and calibrate it against an observed time series of
prevalence. This is the canonical "virus on a network" diffusion problem,
but the focus here is **parameter estimation against empirical data**, not
reproducing a specific paper.

The empirical data records (susceptible, infected, resistant) counts at
every tick for 250 ticks. The total population stays at 150 throughout
(closed population). I want to estimate three behavioural parameters that
best reproduce the observed dynamics.

## Empirical data

Observed time series available at `data/observed.csv`:

  - 250 rows × 4 columns: `tick`, `susceptible`, `infected`, `resistant`
  - Total susceptible + infected + resistant = 150 at every tick
  - Initially 147 susceptible, 3 infected, 0 resistant
  - Final state: ~10 susceptible, ~27 infected, ~113 resistant

## Agents

**Person** (150 of them):
- `state`: one of "S" (susceptible), "I" (infected), "R" (resistant)
- `virus_check_timer`: integer, counts ticks since last virus check

## Network structure

Spatially clustered random network:
- Average degree ≈ 6 (each person has on average 6 connections)
- Connections set up at initialisation, fixed throughout simulation

## Mechanism

Each tick:
1. **Spread**: every infected agent has probability `virus_spread_chance`
   (in percent) of infecting each of its susceptible neighbours.
   "Susceptible" means state = "S" — resistant neighbours are immune.
2. **Recovery check**: every `virus_check_frequency` ticks (default 1),
   each infected agent independently rolls:
   - With probability `recovery_chance` (percent), recover (transition out of "I").
   - Upon recovery, with probability `gain_resistance_chance` (percent),
     become "R" (resistant); otherwise revert to "S" (susceptible again).
3. **Stop** when no infected agents remain.

## Parameters to estimate (calibration targets)

| Parameter | Range | Unit |
|---|---|---|
| `virus_spread_chance` | 0 – 20 | percent per neighbour per tick |
| `recovery_chance` | 0 – 5 | percent per infected per check |
| `gain_resistance_chance` | 0 – 100 | percent at recovery |

Fixed structural parameters (NOT to estimate):

| Parameter | Value |
|---|---|
| `num_agents` | 150 |
| `average_degree` | 6 |
| `initial_outbreak_size` | 3 |
| `virus_check_frequency` | 1 |
| `periods` | 250 |

## Output metrics (must be tracked for calibration)

- `susceptible` count per tick
- `infected` count per tick
- `resistant` count per tick

These three columns must match the structure of `data/observed.csv` so the
calibrator can compute fit per tick.

## Calibration target

The model should reproduce the observed trajectory of (susceptible, infected,
resistant) over 250 ticks. Fit metric: MSE between simulated and observed
columns, averaged over ticks and over the 3 state counts.
