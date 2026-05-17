# Story: El Farol Bar Problem

## Research Motivation

W. Brian Arthur (1994) introduced the El Farol Bar problem to illustrate bounded rationality and inductive reasoning. 100 people must independently decide each week whether to attend a bar, knowing it is enjoyable only when fewer than 60 people show up. No deductively rational solution exists — agents must use heuristic predictors based on past attendance.

## Research Goal

Simulate the El Farol Bar problem to observe emergent attendance oscillations around the comfort threshold. Study how predictor diversity and memory length affect attendance volatility and average welfare.

## Agent Description

Each agent has:
- `attending`: boolean, whether attending this week
- `predictors`: list of K simple prediction strategies (e.g., "same as last week", "opposite of last week", "average of last 4 weeks", "trend extrapolation")
- `best_predictor`: index of currently best-performing predictor
- `score`: cumulative payoff

Each predictor is a simple function mapping recent attendance history to a predicted attendance number.

## Spatial Structure

No spatial structure needed. Place 100 agents on a 10x10 grid for bookkeeping purposes only. Agents do not interact spatially — the only shared information is aggregate attendance history.

## Dynamics

Each time step (200 periods):
1. Each agent uses their best predictor to predict this week's attendance
2. If predicted attendance < `comfort_threshold`: attend. Otherwise: stay home.
3. Record actual attendance
4. Each agent evaluates all their predictors against actual outcome
5. Each agent switches to their most accurate predictor (lowest recent prediction error)
6. Environment records attendance in history buffer

## Parameters of Interest

- `num_agents`: Number of potential bar-goers (default 100)
- `comfort_threshold`: Maximum comfortable attendance (range 40-80, default 60)
- `num_predictors`: Predictors per agent (range 3-10, default 5)
- `memory_length`: How many past weeks agents remember (range 3-20, default 10)

## Output of Interest

- Weekly attendance over time
- Mean attendance (should fluctuate around comfort_threshold)
- Attendance volatility (standard deviation)
- Average agent payoff (welfare)

## Mode

Simulator (no calibration needed)

## Source

Arthur, W.B. (1994). "Inductive Reasoning and Bounded Rationality (The El Farol Problem)." American Economic Review Papers and Proceedings, 84, 406-411.
