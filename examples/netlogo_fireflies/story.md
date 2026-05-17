# Story: Fireflies

## Research Motivation

This model demonstrates a population of fireflies which synchronize their flashing using only the interactions between the individual fireflies. It is a good example of how a distributed system (i.e. a system with many interacting elements, but no 'leader') can coordinate itself without any central coordinator.

Though most species of firefly are not generally known to synchronize in groups, there are some (for example, Pteroptyx cribellata, Luciola pupilla,and Pteroptyx malaccae) that have been observed to do so in certain settings. This model generalizes two main strategies used by such insects to synchronize with each other (phase delay and phase advance synchronization, as described below), retaining the essentials of the strategies while downplaying biological detail.

## Research Goal

Each firefly constantly cycles through its own clock, flashing at the beginning of each cycle and then resetting the clock to zero once it has reached the maximum. At the start of each simulation all fireflies begin at a random point in their cycles (though they all have the same cycle lengths) and so flashing will occur erratically through the population. As fireflies perceive other flashes around them they are able to use this information to reset their own clocks to try and synchronize with the other fireflies in their vicinity. Each firefly uses the same set of rules to govern its own clock, and depending on the parameters of the simulation, the population may synchronize more or less effectively.

## Agent Description

**Turtle** agent with properties:
- `clock`
- `threshold`
- `reset-level`
- `window`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

GO: starts and stops the simulation.

SETUP: resets the simulation according to the parameters set by the sliders.

## Parameters of Interest

- `number`: range [0.0, 2000.0], default=1500.0, step=1.0
- `cycle-length`: range [5.0, 100.0], default=10.0, step=1.0
- `flash-length`: range [1.0, 10.0], default=1.0, step=1.0
- `flashes-to-reset`: range [1.0, 3.0], default=1.0, step=1.0

## Output of Interest

- Flashing Fireflies

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Fireflies.nlogo`
