# Story: Sugarscape 2 Constant Growback

## Research Motivation

This second model in the NetLogo Sugarscape suite implements Epstein & Axtell's Sugarscape Constant Growback model, as described in chapter 2 of their book Growing Artificial Societies: Social Science from the Bottom Up. It simulates a population with limited, spatially-distributed resources available. It differs from Sugarscape 1 Immediate Growback in that the growback of sugar is gradual rather than instantaneous.

## Research Goal

Each patch contains some sugar, the maximum amount of which is predetermined. At each tick, each patch regains one unit of sugar, until it reaches the maximum amount. The amount of sugar a patch currently contains is indicated by its color; the darker the yellow, the more sugar.

At setup, agents are placed at random within the world. Each agent can only see a certain distance horizontally and vertically. At each tick, each agent will move to the nearest unoccupied location within their vision range with the most sugar, and collect all the sugar there.  If its current location has as much or more sugar than any unoccupied location it can see, it will stay put.

## Agent Description

**Turtle** agent with properties:
- `sugar`
- `metabolism`
- `vision`
- `vision-points`

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

Set the INITIAL-POPULATION slider before pressing SETUP. This determines the number of agents in the world.

Press SETUP to populate the world with agents and import the sugar map data. GO will run the simulation continuously, while GO ONCE will run one tick.

## Parameters of Interest

- `initial-population`: range [10.0, 1000.0], default=400.0, step=10.0

## Output of Interest

- Population
- Wealth distribution
- Average vision
- Average metabolism

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Sugarscape 2 Constant Growback.nlogo`
