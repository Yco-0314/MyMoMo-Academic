# Story: Bounded Confidence Opinion Dynamics (Hegselmann-Krause)

## Research Motivation

Hegselmann and Krause (2002) proposed a model where agents only update their opinions by averaging with others whose opinions are sufficiently close. This "bounded confidence" mechanism produces rich dynamics: consensus when the confidence bound is large, polarization into clusters when moderate, and fragmentation when small.

## Research Goal

Simulate opinion dynamics under bounded confidence on a spatial grid. Study how the confidence bound epsilon determines the number of final opinion clusters and the transition between consensus, polarization, and fragmentation.

## Agent Description

Each agent holds a continuous opinion:
- `opinion`: float in [0, 1], initialized uniformly at random
- `x`, `y`: grid position

## Spatial Structure

Grid of 20x20 (400 agents). Toroidal. Each agent interacts with neighbors within radius 2 (up to ~12 neighbors).

## Dynamics

Each time step (500 periods):
1. For each agent:
   a. Identify all neighbors within spatial radius 2
   b. Filter to "confidence set": neighbors whose opinion differs by less than `epsilon`
   c. Update opinion to the average of own opinion and all confidence-set neighbors' opinions
2. Track number of distinct opinion clusters (opinions within 0.02 of each other are considered same cluster)
3. Record opinion variance and number of clusters

## Parameters of Interest

- `epsilon`: Confidence bound — maximum opinion distance for interaction (range 0.05-0.5, default 0.2)
- `num_agents`: Population size (default 400, on 20x20 grid)
- `interaction_radius`: Spatial radius for neighbor detection (range 1-5, default 2)

## Output of Interest

- Average opinion over time
- Opinion variance over time (convergence indicator)
- Number of opinion clusters over time
- Final number of stable clusters
- Distribution of final opinions

## Mode

Simulator (no calibration needed)

## Source

Hegselmann, R. & Krause, U. (2002). "Opinion Dynamics and Bounded Confidence: Models, Analysis and Simulation." JASSS, 5(3), 2.
