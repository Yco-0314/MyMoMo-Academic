# Story: Shepherds

## Research Motivation

This project is inspired by two simpler models: one of termites gathering wood chips into piles and one of moving sheep.  In this project, sheep wander randomly while shepherds circulate trying to herd them.  Whether or not the sheep eventually end up in a single herd depends on the number of shepherds and how fast they move compared to the sheep.

## Research Goal

The shepherds follow a set of simple rules.  Each shepherd starts wandering randomly.  If it bumps into a sheep, it picks the sheep up, and continues to wander randomly. When it bumps into another sheep, it finds a nearby empty space, puts its sheep down, and looks for another one.

## Agent Description

**A-Sheep** agent with properties:

**Shepherd** agent with properties:
- `carried-sheep`
- `found-herd?`

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

Click the SETUP button to set up the shepherds (brown) and sheep (white).  Click the GO button to start the simulation.   A shepherd turns blue when it is carrying a sheep.

There are three sliders.  NUM-SHEEP and NUM-SHEPHERDS control the numbers of sheep and shepherds, respectively.   Changes in these sliders do not take effect until the next setup.

## Parameters of Interest

- `num-sheep`: range [0.0, 500.0], default=150.0, step=1.0
- `num-shepherds`: range [0.0, 100.0], default=30.0, step=1.0
- `sheep-speed`: range [0.0, 0.2], default=0.02, step=0.01

## Output of Interest

- Herding Efficiency

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Shepherds.nlogo`
