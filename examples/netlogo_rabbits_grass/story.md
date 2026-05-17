# Story: Rabbits Grass Weeds

## Research Motivation

This project explores a simple ecosystem made up of rabbits, grass, and weeds. The rabbits wander around randomly, and the grass and weeds grow randomly.   When a rabbit bumps into some grass or weeds, it eats the grass and gains energy. If the rabbit gains enough energy, it reproduces. If it doesn't gain enough energy, it dies.

The grass and weeds can be adjusted to grow at different rates and give the rabbits differing amounts of energy.  The model can be used to explore the competitive advantages of these variables.

## Research Goal

Simulate the Rabbits Grass Weeds model and observe emergent dynamics. Identify key parameters driving system behavior through parameter sweeps.

## Agent Description

**Rabbit** agent with properties:
- `energy`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

Click the SETUP button to setup the rabbits (red), grass (green), and weeds (violet). Click the GO button to start the simulation.

The NUMBER slider controls the initial number of rabbits. The BIRTH-THRESHOLD slider sets the energy level at which the rabbits reproduce.  The GRASS-GROWTH-RATE slider controls the rate at which the grass grows.  The WEEDS-GROWTH-RATE slider controls the rate at which the weeds grow.

## Parameters of Interest

- `grass-grow-rate`: range [0.0, 20.0], default=15.0, step=1.0
- `weeds-grow-rate`: range [0.0, 20.0], default=0.0, step=1.0
- `grass-energy`: range [0.0, 10.0], default=5.0, step=0.5
- `weed-energy`: range [0.0, 10.0], default=0.0, step=0.5
- `number`: range [0.0, 500.0], default=150.0, step=1.0
- `birth-threshold`: range [0.0, 20.0], default=15.0, step=1.0

## Output of Interest

- Populations

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Rabbits Grass Weeds.nlogo`
