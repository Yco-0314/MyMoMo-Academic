# Story: Peppered Moths

## Research Motivation

This project models a classic example of natural selection - the peppered moths of Manchester, England. The peppered moths use their coloration as camouflage from the birds that would eat them. (Note that in this model, the birds act invisibly.) Historically, light-colored moths predominated because they blended in well against the white bark of the trees they rested on.

However, due to the intense pollution caused by the Industrial Revolution, Manchester's trees became discolored with soot, and the light-colored moths began to stick out, while the dark-colored moths blended in. Consequently, the darker moths began to predominate.

Now, in the past few decades, pollution controls have helped clean up the environment, and the trees are returning to their original color. Hence, the lighter moths are once again thriving at expense of their darker cousins.

## Research Goal

This model simulates these environmental changes, and how a population of moths, initially of all different colors, changes under the pressures of natural selection.

## Agent Description

**Moth** agent with properties:
- `age`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

The NUM-MOTHS slider controls how many moths are initially present in the world. Their coloration is randomly distributed over the possible colors of the world (white to black). Simply select how many moths you'd like to begin with (around 200 is good), and press the SETUP button. Then press the GO button to begin the simulation.

The MUTATION slider controls the rate of mutation at birth. For the purposes of the simulation, the mutation rate is much higher than it might be in real life. When MUTATION is set to 0, moths are exactly the same as the parent that hatched them. When it is set to 100, there is no correlation between a parent's color and the color of its children. (Best results are seen when MUTATION is set to around 10 or 15, but experiment with the rate and watch what happens.)

## Parameters of Interest

- `num-moths`: range [0.0, 200.0], default=100.0, step=1.0
- `mutation`: range [0.0, 100.0], default=15.0, step=1.0
- `selection`: range [0.0, 100.0], default=50.0, step=1.0
- `speed`: range [1.0, 100.0], default=10.0, step=1.0

## Output of Interest

- Moth Colors Over Time

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Peppered Moths.nlogo`
