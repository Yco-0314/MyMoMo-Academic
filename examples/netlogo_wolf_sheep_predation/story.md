# Story: Wolf Sheep Predation

## Research Motivation

This model explores the stability of predator-prey ecosystems. Such a system is called unstable if it tends to result in extinction for one or more species involved.  In contrast, a system is stable if it tends to maintain itself over time, despite fluctuations in population sizes.

## Research Goal

There are two main variations to this model.

In the first variation, the "sheep-wolves" version, wolves and sheep wander randomly around the landscape. When a wolf finds a sheep on its patch, it consumes it. Each step costs the wolves energy, and they must eat sheep in order to replenish their energy - when they run out of energy they die. To allow the population to continue, each wolf or sheep has a fixed probability of reproducing at each time step. In this variation, we model the grass as "infinite" so that sheep always have enough to eat, and we don't explicitly model the eating or growing of grass. As such, sheep don't either gain or lose energy by eating or moving. This variation produces interesting population dynamics, but is ultimately unstable. This variation of the model is particularly well-suited to modeling interacting species in a rich nutrient environment, such as two strains of bacteria in a petri dish (Gause, 1934).

## Agent Description

**A-Sheep** agent with properties:

**Wolf** agent with properties:

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.
World size: 51×51, toroidal (wrapping) boundaries.

## Dynamics

1. Set the model-version chooser to "sheep-wolves-grass" to include grass eating and growth in the model, or to "sheep-wolves" to only include wolves (black) and sheep (white).
2. Adjust the slider parameters (see below), or use the default settings.
3. Press the SETUP button.
4. Press the GO button to begin the simulation.
5. Look at the monitors to see the current population sizes
6. Look at the POPULATIONS plot to watch the populations fluctuate over time

Parameters:
MODEL-VERSION: Whether we model sheep wolves and grass or just sheep and wolves
INITIAL-NUMBER-SHEEP: The initial size of sheep population
INITIAL-NUMBER-WOLVES: The initial size of wolf population
SHEEP-GAIN-FROM-FOOD: The amount of energy sheep get for every grass patch eaten (Note this is not used in the sheep-wolves model version)
WOLF-GAIN-FROM-FOOD: The amount of energy wolves get for every sheep eaten
SHEEP-REPRODUCE: The probability of a sheep reproducing at each time step
WOLF-REPRODUCE: The probability of a wolf reproducing at each time step
GRASS-REGROWTH-TIME: How long it takes for grass to regrow once it is eaten (Note this is not used in the sheep-wolves model version)
SHOW-ENERGY?: Whether or not to show the energy of each animal as a label on the animal

## Parameters of Interest

- `sheep-reproduce`: range [1.0, 20.0], default=4.0, step=1.0
- `sheep-gain-from-food`: range [0.0, 50.0], default=4.0, step=1.0
- `grass-regrowth-time`: range [0.0, 100.0], default=30.0, step=1.0
- `wolf-reproduce`: range [0.0, 20.0], default=5.0, step=1.0
- `wolf-gain-from-food`: range [0.0, 100.0], default=20.0, step=1.0
- `initial-number-wolves`: range [0.0, 250.0], default=50.0, step=1.0
- `initial-number-sheep`: range [0.0, 250.0], default=100.0, step=1.0

## Output of Interest

- populations

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Wolf_Sheep_Predation.nlogo`
