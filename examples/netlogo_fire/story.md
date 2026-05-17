# Story: Forest Fire Percolation Model

## Research Motivation

This model simulates fire spreading through a forest to study percolation thresholds.
The fire's chance of reaching the right edge depends critically on tree density — a classic
example of a non-linear threshold (critical parameter) in complex systems.

## Research Goal

Simulate fire spreading through a 50×50 forest grid with variable tree density.
Identify the critical density threshold where fire percolation transitions from
failing to reaching the far edge. Measure the percentage of forest burned as a
function of density.

## Agent Description

Each agent is a **Tree** on the grid with one state:
- **empty** (0): No tree at this cell
- **tree** (1): Green, alive, can catch fire from burning neighbors
- **burning** (2): Currently on fire, will ignite adjacent trees
- **burned** (3): Burnt out, cannot catch fire again

Initial infected agents: All trees in the leftmost column (x=0) start as burning (state=2).
Other cells are randomly populated with trees at probability = `density / 100`.

## Spatial Structure

Use a **grid** of size 50×50. Each cell holds one agent. Boundaries are **non-wrapping** (bounded).
Fire spreads to Von Neumann neighbors (4 directions: N, S, E, W).

## Dynamics

Each time step:
1. Each **burning** tree ignites all adjacent **tree** neighbors (Von Neumann, radius=1)
2. Each **burning** tree transitions to **burned** (state=3)
3. Simulation ends when no burning trees remain

## Parameters of Interest

- `density`: Percentage of cells initially occupied by trees (range 1–99, default 57)
- `grid_size`: Grid width and height (default 50)

## Output of Interest

- Percentage of forest burned (burned / total trees)
- Whether fire reached the right edge (x = grid_size - 1)
- Number of time steps until fire extinction

## Mode

Simulator (no calibration needed)

## Source

Based on NetLogo Models Library: Fire model (percolation study)
