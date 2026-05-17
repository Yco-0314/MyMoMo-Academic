# Story: Segregation

## Research Motivation

This project models the behavior of two types of agents in a neighborhood. The orange agents and blue agents get along with one another. But each agent wants to make sure that it lives near some of "its own." That is, each orange agent wants to live near at least some orange agents, and each blue agent wants to live near at least some blue agents. The simulation shows how these individual preferences ripple through the neighborhood, leading to large-scale patterns.

This project was inspired by Thomas Schelling's writings about social systems (such as housing patterns in cities).

## Research Goal

Simulate the Segregation model and observe emergent dynamics. Identify key parameters driving system behavior through parameter sweeps.

## Agent Description

**Turtle** agent with properties:
- `happy?`
- `similar-nearby`
- `other-nearby`
- `total-nearby`

## Spatial Structure

Grid-based model with mobile agents.
World size: 51×51, toroidal (wrapping) boundaries.

## Dynamics

Click the SETUP button to set up the agents. There are approximately equal numbers of orange and blue agents. The agents are set up so no patch has more than one agent.  Click GO to start the simulation. If agents don't have enough same-color neighbors, they move to a nearby patch. (The topology is wrapping, so that patches on the bottom edge are neighbors with patches on the top and similar for left and right).

The DENSITY slider controls the occupancy density of the neighborhood (and thus the total number of agents). (It takes effect the next time you click SETUP.)  The %-SIMILAR-WANTED slider controls the percentage of same-color agents that each agent wants among its neighbors. For example, if the slider is set at 30, each blue agent wants at least 30% of its neighbors to be blue agents.

## Parameters of Interest

- `density`: range [50.0, 99.0], default=95.0, step=1.0
- `%-similar-wanted`: range [0.0, 100.0], default=30.0, step=1.0

## Output of Interest

- Number-unhappy
- Percent Similar

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Segregation.nlogo`
