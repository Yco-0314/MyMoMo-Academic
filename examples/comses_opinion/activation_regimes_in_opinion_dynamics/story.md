# Story: Opinion Dynamics with Activation Regimes

## Research Motivation

Alizadeh and Cioffi-Revilla (2015, JASSS) investigated how different agent activation orders affect opinion dynamics. Using Huet et al.'s 2D opinion model, they showed that activation regimes significantly affect clustering statistics and radicalization, even when qualitative aggregate patterns appear similar.

## Research Goal

Simulate agents with 2-dimensional continuous opinions interacting under bounded confidence. Study how the confidence threshold affects the number of emergent opinion clusters, radicalization (drift to extremes), and convergence speed.

## Agent Description

Each agent holds a 2-dimensional opinion vector:
- `opinion_x`: float in [0, 1] (first opinion dimension)
- `opinion_y`: float in [0, 1] (second opinion dimension)
- `state`: integer (0 = moderate, 1 = radicalized if opinion is within 0.05 of 0 or 1 on either dimension)

## Spatial Structure

Grid of 20x20 (400 agents). Toroidal. Each agent interacts with neighbors within radius 2.

## Dynamics

Each time step (500 periods):
1. Select agents in random order
2. For each selected agent:
   a. Find neighbors within spatial radius 2
   b. Filter to those within Euclidean opinion distance < `confidence_bound`
   c. If confidence set is non-empty: update opinion to average of self and confidence-set neighbors
   d. If confidence set is empty but there are very different neighbors (distance > `rejection_bound`): move opinion AWAY from them by a small step (negative influence)
3. Track: number of opinion clusters, max cluster size, number of radicalized agents

## Parameters of Interest

- `confidence_bound`: Maximum opinion distance for positive influence (range 0.1-0.5, default 0.3)
- `rejection_bound`: Minimum distance triggering negative influence (range 0.6-1.0, default 0.8)
- `negative_influence_strength`: Step size for rejection (range 0.0-0.1, default 0.02)

## Output of Interest

- Number of opinion clusters over time
- Number of radicalized agents (opinions near 0 or 1)
- Maximum cluster size
- Opinion variance over time
- Convergence time

## Mode

Simulator (no calibration needed)

## Source

Alizadeh, M. & Cioffi-Revilla, C. (2015). JASSS 18(3)8. CoMSES: https://www.comses.net/codebases/4327/
