# Story: Rumor Mill

## Research Motivation

This program models the spread of a rumor.  The rumor spreads when a person who knows the rumor tells one of their neighbors.  In other words, spatial proximity is a determining factor as to how soon (and perhaps how often) a given individual will hear the rumor.

The neighbors can be defined as either the four adjacent people or the eight adjacent people.  At each time step, every person who knows the rumor randomly chooses a neighbor to tell the rumor to.  The simulation keeps track of who knows the rumor, how many people know the rumor, and how many "repeated tellings" of the rumor occur.

## Research Goal

Simulate the Rumor Mill model and observe emergent dynamics. Identify key parameters driving system behavior through parameter sweeps.

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.
World size: 101×101, toroidal (wrapping) boundaries.

## Dynamics

EIGHT-MODE? is a switch that determines whether at each time step the rumor spreads to one of four randomly chosen neighbors, or one of eight such neighbors.

As with any rumor, it has to start somewhere, with one or more individuals.  There are three ways to control the start of the rumor:

## Parameters of Interest

- `init-clique`: range [0.0, 10.0], default=0.1, step=0.1

## Output of Interest

- Successive Ratios
- Rumor Spread
- Successive Differences

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Rumor_Mill.nlogo`
