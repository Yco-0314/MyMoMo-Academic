# Story: Heatbugs

## Research Motivation

Heatbugs is an abstract model of the behavior of biologically-inspired agents that attempt to maintain an optimum temperature around themselves.  It demonstrates how simple rules defining the behavior of agents can produce several different kinds of emergent behavior.

Heatbugs has been used as a demonstration model for many agent-based modeling toolkits. We provide a NetLogo version to assist users in learning and comparing different toolkits.  It demonstrates coding techniques in NetLogo and may be useful as a starting point for building other models.

While this NetLogo model attempts to match the Repast and Swarm versions (see "Credits" below), we haven't done a rigorous comparative analysis of the different versions, so it is possible that there are small inadvertent differences in the underlying rules and behavior.

## Research Goal

The bugs move around on a grid of square "patches".  A bug may not move to a patch that already has another bug on it.

Each bug radiates a small amount of heat.  Heat gradually diffuses through the world; some heat is lost to cooling.

## Agent Description

**Turtle** agent with properties:
- `ideal-temp`
- `output-heat`
- `unhappiness`

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

After choosing the number of bugs to create, and setting the model variables, press the GO button to set the heatbugs into motion.

BUG-COUNT: The number of bugs that will inhabit the model

## Parameters of Interest

- `bug-count`: range [1.0, 500.0], default=100.0, step=1.0
- `evaporation-rate`: range [0.0, 1.0], default=0.01, step=0.01
- `diffusion-rate`: range [0.0, 1.0], default=0.9, step=0.1
- `random-move-chance`: range [0.0, 100.0], default=0.0, step=1.0
- `min-ideal-temp`: range [0.0, 200.0], default=10.0, step=1.0
- `max-ideal-temp`: range [0.0, 200.0], default=40.0, step=1.0
- `max-output-heat`: range [0.0, 100.0], default=25.0, step=1.0
- `min-output-heat`: range [0.0, 100.0], default=5.0, step=1.0

## Output of Interest

- Avg. Bug Unhappiness

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Heatbugs.nlogo`
