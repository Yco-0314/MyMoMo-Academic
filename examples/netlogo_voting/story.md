# Story: Voting

## Research Motivation

This model is a simple cellular automaton that simulates voting distribution by having each patch take a "vote" of its eight surrounding neighbors, then perhaps change its own vote according to the outcome.

## Research Goal

Simulate the Voting model and observe emergent dynamics. Identify key parameters driving system behavior through parameter sweeps.

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

Click the SETUP button to create an approximately equal but random distribution of blue and green patches.  Click GO to run the simulation.

When both switches are off, the central patch changes its color to match the majority vote, but if there is a 4-4 tie, then it does not change.

## Parameters of Interest


## Output of Interest

- Time series of key aggregate metrics
- Emergent spatial patterns

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Voting.nlogo`
