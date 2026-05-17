# Story: Bass Innovation Diffusion Model

## Research Motivation

The Bass (1969) model is the foundational framework for understanding how new products and innovations spread through a population. It distinguishes between innovation effects (external influence from advertising/media) and imitation effects (word-of-mouth from adopters). The agent-based version adds spatial structure and heterogeneity to the original differential equation model.

## Research Goal

Simulate technology adoption on a spatial grid to reproduce the characteristic S-shaped adoption curve. Study how the innovation coefficient (p) and imitation coefficient (q) interact with spatial network structure to determine diffusion speed and final adoption level.

## Agent Description

Each agent represents a potential adopter with:
- `adopted`: boolean (0 = potential adopter, 1 = adopter)
- `adoption_time`: period when adopted (-1 if not yet)
- `innovativeness`: personal innovation susceptibility (uniform random in [0,1])

## Spatial Structure

Grid of 30x30 (900 agents). Toroidal (wrapping edges). Each agent interacts with 8 neighbors (Moore neighborhood).

## Dynamics

Each time step (200 periods):
1. For each non-adopter:
   a. Calculate `fraction_adopted_neighbors` = count of adopted neighbors / 8
   b. Innovation effect: adopt with probability `p` (external influence)
   c. Imitation effect: adopt with probability `q * fraction_adopted_neighbors`
   d. Combined: adopt with probability `p + q * fraction_adopted_neighbors`
2. Once adopted, an agent stays adopted permanently
3. Track cumulative and new adoptions per period

## Parameters of Interest

- `p`: Innovation coefficient — probability of spontaneous adoption (range 0.001-0.05, default 0.03)
- `q`: Imitation coefficient — social influence strength (range 0.1-0.5, default 0.38)
- `initial_adopters`: Number of seed adopters at start (range 1-10, default 3)

## Output of Interest

- Cumulative adoption fraction over time (S-curve)
- New adoptions per period (bell curve)
- Time to 50% adoption (tipping point)
- Final adoption fraction

## Mode

Simulator (no calibration needed)

## Source

Bass, F.M. (1969). "A New Product Growth for Model Consumer Durables." Management Science, 15(5), 215-227.
