# Story: Ants

## Research Motivation

In this project, a colony of ants forages for food. Though each ant follows a set of simple rules, the colony as a whole acts in a sophisticated way.

## Research Goal

When an ant finds a piece of food, it carries the food back to the nest, dropping a chemical as it moves. When other ants "sniff" the chemical, they follow the chemical toward the food. As more ants carry food to the nest, they reinforce the chemical trail.

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

Click the SETUP button to set up the ant nest (in violet, at center) and three piles of food. Click the GO button to start the simulation. The chemical is shown in a green-to-white gradient.

The EVAPORATION-RATE slider controls the evaporation rate of the chemical. The DIFFUSION-RATE slider controls the diffusion rate of the chemical.

## Parameters of Interest

- `diffusion-rate`: range [0.0, 99.0], default=50.0, step=1.0
- `evaporation-rate`: range [0.0, 99.0], default=10.0, step=1.0
- `population`: range [0.0, 200.0], default=125.0, step=1.0

## Output of Interest

- Food in each pile

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Ants.nlogo`
