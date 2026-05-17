# Story: Schelling Segregation Model with Income Heterogeneity

## Research Motivation

Thomas Schelling's famous model showed that mild individual preferences for similar neighbors
can lead to strong macro-level segregation. I want to extend this to study how **income
inequality** interacts with racial/group preferences to shape urban segregation patterns.

## Research Goal

Simulate a city grid where two groups of agents (Group A and Group B) move based on:
1. Preference for neighbors of the same group (classic Schelling)
2. Preference for neighbors of similar income level

Study how the combination of group preference and income preference leads to different
segregation patterns compared to the classic model.

## Agent Description

Each agent has:
- **Group**: A or B (50% each, random assignment)
- **Income**: Drawn from a log-normal distribution (mean=1.0, std=0.5) — stable, does not change
- **Happiness**: Whether the agent's neighborhood meets their preference thresholds
- **Same-group threshold**: Minimum fraction of same-group neighbors to be happy (default 0.3)
- **Income tolerance**: Maximum income ratio difference to tolerate (default 2.0 = accept
  neighbors with income between 0.5x and 2x own income)

## Spatial Structure

A **grid** of size 30×30 with 20% empty cells (900 empty cells out of 900 total,
720 agents placed randomly). Toroidal (wrapping) boundaries.

## Dynamics

Each time step:
1. For each unhappy agent: move to a random empty cell
2. Recalculate happiness for all agents

Happiness = (fraction of same-group neighbors ≥ same_group_threshold) AND
            (fraction of income-compatible neighbors ≥ income_compatible_threshold)

## Parameters of Interest

- `same_group_threshold`: Classic Schelling tolerance (0.2 – 0.5)
- `income_tolerance`: How wide the acceptable income range is (1.5 – 3.0)
- `income_compatible_threshold`: Minimum fraction of income-compatible neighbors (0.2 – 0.5)

## Output of Interest

- Global segregation index (fraction of same-group neighbors, averaged across all agents)
- Income segregation index (Moran's I or similar)
- Number of unhappy agents per time step
- Time to equilibrium (convergence)

## Mode

Simulator
