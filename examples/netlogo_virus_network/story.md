# Story: Virus On A Network

## Research Motivation

This model demonstrates the spread of a virus through a network.  Although the model is somewhat abstract, one interpretation is that each node represents a computer, and we are modeling the progress of a computer virus (or worm) through this network.  Each node may be in one of three states:  susceptible, infected, or resistant.  In the academic literature such a model is sometimes referred to as an SIR model for epidemics.

## Research Goal

Each time step (tick), each infected node (colored red) attempts to infect all of its neighbors.  Susceptible neighbors (colored blue) will be infected with a probability given by the VIRUS-SPREAD-CHANCE slider.  This might correspond to the probability that someone on the susceptible system actually executes the infected email attachment.
Resistant nodes (colored gray) cannot be infected.  This might correspond to up-to-date antivirus software and security patches that make a computer immune to this particular virus.

Infected nodes are not immediately aware that they are infected.  Only every so often (determined by the VIRUS-CHECK-FREQUENCY slider) do the nodes check whether they are infected by a virus.  This might correspond to a regularly scheduled virus-scan procedure, or simply a human noticing something fishy about how the computer is behaving.  When the virus has been detected, there is a probability that the virus will be removed (determined by the RECOVERY-CHANCE slider).

## Agent Description

**Turtle** agent with properties:
- `infected?`
- `resistant?`
- `virus-check-timer`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

Using the sliders, choose the NUMBER-OF-NODES and the AVERAGE-NODE-DEGREE (average number of links coming out of each node).

The network that is created is based on proximity (Euclidean distance) between nodes.  A node is randomly chosen and connected to the nearest node that it is not already connected to.  This process is repeated until the network has the correct number of links to give the specified average node degree.

## Parameters of Interest

- `gain-resistance-chance`: range [0.0, 100.0], default=5.0, step=1.0
- `recovery-chance`: range [0.0, 10.0], default=5.0, step=0.1
- `virus-spread-chance`: range [0.0, 10.0], default=2.5, step=0.1
- `number-of-nodes`: range [10.0, 300.0], default=150.0, step=5.0
- `virus-check-frequency`: range [1.0, 20.0], default=1.0, step=1.0
- `initial-outbreak-size`: range [1.0, 0.0], default=3.0, step=1.0
- `average-node-degree`: range [1.0, 0.0], default=6.0, step=1.0

## Output of Interest

- Network Status

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Virus on a Network.nlogo`
