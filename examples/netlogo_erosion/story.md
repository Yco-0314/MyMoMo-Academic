# Story: Erosion

## Research Motivation

This model is a simulation of soil erosion by water.  The user is presented with an empty terrain.  Rain falls on the terrain and starts to flow downhill.  As it flows, it erodes the terrain below.  The patterns of water flow change as the terrain is reshaped by erosion.  Eventually, a river system emerges.

## Research Goal

The soil is represented by gray patches.  The lighter the patch, the higher the elevation. Water is represented by blue patches.  Deeper water is represented by a darker blue.  Around the edge of the world is a "drain" into which water and sediment disappear.

Each patch has a certain chance per time step of receiving rain.  If it does receive rain, its water depth increases by one.

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

The SETUP button generates a terrain.  The smoothness of the terrain is controlled by the TERRAIN-SMOOTHNESS slider.  Lower values give rougher terrain, with more variation in elevation.  If you want a perfectly flat terrain, turn off the BUMPY? switch.  If you want to start out with a hill in the middle, turn on the HILL? switch.

The GO button runs the erosion simulation.

## Parameters of Interest

- `terrain-smoothness`: range [1.0, 30.0], default=6.0, step=1.0
- `rainfall`: range [0.0, 0.5], default=0.1, step=0.01
- `soil-hardness`: range [0.0, 1.0], default=0.8, step=0.05

## Output of Interest

- Time series of key aggregate metrics
- Emergent spatial patterns

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Erosion.nlogo`
