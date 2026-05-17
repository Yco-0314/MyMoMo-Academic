# Story: Termites

## Research Motivation

This project is inspired by the behavior of termites gathering wood chips into piles. The termites follow a set of simple rules. Each termite starts wandering randomly. If it bumps into a wood chip, it picks the chip up, and continues to wander randomly. When it bumps into another wood chip, it finds a nearby empty space and puts its wood chip down.  With these simple rules, the wood chips eventually end up in a single pile.

## Research Goal

Simulate the Termites model and observe emergent dynamics. Identify key parameters driving system behavior through parameter sweeps.

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

Click the SETUP button to set up the termites (white) and wood chips (yellow). Click the GO button to start the simulation.  The termites turn orange when they are carrying a wood chip.

The NUMBER slider controls the number of termites. (Note: Changes in the NUMBER slider do not take effect until the next setup.) The DENSITY slider controls the initial density of wood chips.

## Parameters of Interest

- `number`: range [1.0, 2000.0], default=400.0, step=1.0
- `density`: range [0.0, 100.0], default=20.0, step=1.0

## Output of Interest

- Time series of key aggregate metrics
- Emergent spatial patterns

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Termites.nlogo`
