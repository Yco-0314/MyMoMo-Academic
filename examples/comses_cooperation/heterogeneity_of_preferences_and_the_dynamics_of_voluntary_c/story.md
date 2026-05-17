# Story: Public Goods Game with Heterogeneous Preferences

## Research Motivation

Amin et al. (CoMSES) modeled how different cooperative preference types affect voluntary contributions to a public good. Seven preference types (free-rider, conditional cooperator, above/below-diagonal, alternating, triangular, random) are based on experimental data.

## Research Goal

Simulate a public goods game where agents with different preference types contribute to a common pool. Study how the distribution of types affects total contributions and whether cooperation is sustained or collapses.

## Agent Description

Each agent has:
- `preference_type`: integer 0-6 (0=free-rider, 1=conditional cooperator, 2=above-diagonal, 3=below-diagonal, 4=alternating, 5=triangular, 6=random)
- `contribution`: float, current period contribution (0 to endowment)
- `payoff`: float, current period earnings
- `endowment`: fixed income per period (default 20)

## Spatial Structure

Grid of 10x10 (100 agents). Toroidal. Agents interact in 2x2 groups (4 neighbors).

## Dynamics

Each time step (100 periods):
1. Each agent receives `endowment` tokens
2. Each agent decides contribution based on preference type and average group contribution last period:
   - Free-rider: contribute 0
   - Conditional cooperator: match group average
   - Above-diagonal: group average + 2
   - Below-diagonal: max(0, group average - 2)
   - Alternating: alternate between endowment and 0
   - Triangular: ramp up then down over 20-period cycles
   - Random: uniform random [0, endowment]
3. Group return: total contribution * `multiplier` / group_size
4. Payoff = endowment - contribution + group_return
5. Track: average contribution, payoff by type

## Parameters of Interest

- `multiplier`: Public good multiplier (range 1.2-3.0, default 1.6)
- `pct_free_riders`: Percentage of free-riders (range 0-50, default 20)
- `pct_conditional_coop`: Percentage of conditional cooperators (range 0-50, default 30)
- `endowment`: Per-period income (range 10-50, default 20)

## Output of Interest

- Average contribution over time
- Total public good provision over time
- Average payoff by preference type
- Contribution trajectory (sustain or decay?)

## Mode

Simulator (no calibration needed)

## Source

Amin, E., Soliman, A., Abouelela, M. CoMSES: https://www.comses.net/codebases/5168/
