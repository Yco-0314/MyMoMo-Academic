# Story: Dominance Hierarchy Formation

## Research Motivation

Bonabeau, Theraulaz, and Deneubourg (1999) showed that linear dominance hierarchies can emerge from simple pairwise interactions with winner and loser effects: winners become more likely to win again, losers more likely to lose. This "self-reinforcing" dynamic produces stable rank orders from initially equal individuals, explaining pecking orders in animal groups.

## Research Goal

Simulate a population of initially identical agents engaging in random pairwise encounters. Study how winner/loser effects produce stable dominance hierarchies and how the strength of these effects determines hierarchy linearity and stability.

## Agent Description

Each agent represents an individual with:
- `dominance_score`: float representing accumulated dominance (starts at 50.0 for all)
- `wins`: count of encounters won
- `losses`: count of encounters lost
- `rank`: current rank in population (computed from dominance_score)

## Spatial Structure

Grid of 10x10 (100 agents). Toroidal. Agents move randomly each step and encounter neighbors.

## Dynamics

Each time step (500 periods):
1. Each agent moves to a random adjacent cell
2. For each agent, if sharing a cell with another agent, an encounter occurs:
   a. Win probability for agent A = `dominance_score_A / (dominance_score_A + dominance_score_B)`
   b. Winner gains `winner_bonus` to dominance_score
   c. Loser loses `loser_penalty` from dominance_score (minimum 1.0)
3. Every 10 steps, rank all agents by dominance_score
4. Environment tracks: Gini coefficient of dominance scores, rank stability (correlation with previous ranking), number of rank changes

## Parameters of Interest

- `num_agents`: Population size (default 100, on 10x10 grid)
- `winner_bonus`: Dominance points gained by winner (range 1-20, default 5)
- `loser_penalty`: Dominance points lost by loser (range 1-20, default 5)
- `encounter_rate`: Probability of encounter when sharing cell (range 0.1-1.0, default 0.5)

## Output of Interest

- Gini coefficient of dominance scores over time (hierarchy strength)
- Rank stability index over time (Spearman correlation of ranks between periods)
- Distribution of dominance scores at equilibrium
- Number of rank changes per period (should decrease as hierarchy stabilizes)
- Top-ranked agent's dominance score trajectory

## Mode

Simulator (no calibration needed)

## Source

Bonabeau, E., Theraulaz, G., & Deneubourg, J.-L. (1999). "Dominance Orders in Animal Societies: The Self-Organization Hypothesis Revisited." Bulletin of Mathematical Biology, 61(4), 727-757.
