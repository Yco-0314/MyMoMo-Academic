# Story: Axelrod Cultural Dissemination Model

## Research Motivation

Robert Axelrod (1997) showed that local cultural convergence can paradoxically produce global cultural polarization. When agents interact only with culturally similar neighbors, homogeneous regions emerge separated by sharp cultural boundaries — even though every interaction makes agents more alike.

## Research Goal

Simulate cultural dissemination on a grid to study how the number of stable cultural regions depends on the number of cultural features (F) and the number of traits per feature (Q). Identify the phase transition between monoculture and fragmented multi-culture.

## Agent Description

Each agent occupies one cell and carries a **culture vector** of length F, where each element takes an integer value in [0, Q-1]. Two agents are **culturally similar** if they share at least one matching feature. Similarity = (number of matching features) / F.

Attributes:
- `culture`: list of F integers, each in [0, Q-1]
- `x`, `y`: grid position

## Spatial Structure

Grid of 20x20 (400 agents). Non-toroidal (bounded edges). Each agent has 4 neighbors (von Neumann neighborhood).

## Dynamics

Each time step (repeated for 2000 periods):
1. Pick a random agent and a random neighbor
2. Calculate similarity (fraction of matching features)
3. If similarity > 0 and similarity < 1 (not identical, not completely different):
   - With probability equal to similarity, copy one randomly chosen differing feature from neighbor to self
4. Track the number of distinct cultural regions (connected components of identical culture)

## Parameters of Interest

- `num_features` (F): Number of cultural dimensions (range 3-10, default 5)
- `num_traits` (Q): Possible values per feature (range 3-15, default 10)
- `grid_size`: Side length of grid (default 20)

## Output of Interest

- Number of distinct cultural regions over time
- Size of the largest cultural region
- Average cultural similarity across all neighbor pairs
- Final number of stable regions (convergence indicator)

## Mode

Simulator (no calibration needed)

## Source

Axelrod, R. (1997). "The Dissemination of Culture." Journal of Conflict Resolution, 41(2), 203-226.
