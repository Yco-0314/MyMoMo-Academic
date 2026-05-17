# Story: Ethnocentrism

## Research Motivation

This model, due to Robert Axelrod and Ross A. Hammond, suggests that "ethnocentric" behavior can evolve under a wide variety of conditions, even when there are no native "ethnocentrics" and no way to differentiate between agent types.  Agents compete for limited space via Prisoner Dilemma's type interactions. "Ethnocentric" agents treat agents within their group more beneficially than those outside their group.  The model includes a mechanism for inheritance (genetic or cultural) of strategies.

## Research Goal

Each agent has three traits: a) color, b) whether they cooperate with same colored agents, and c) whether they cooperate with different colored agents.  An "ethnocentric" agent is one which cooperates with same colored agents, but does not cooperate with different colored agents. An "altruist" cooperates with all agents, while an "egoist" cooperates with no one.  A "cosmopolitan" cooperates with agents of a different color but not of their own color.

At each time step, the following events occur:

## Agent Description

**Turtle** agent with properties:
- `ptr`
- `cooperate-with-same?`
- `cooperate-with-different?`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

To prepare the simulation for a new run, press SETUP EMPTY.  Press GO to start the simulation running, press GO again to stop it.

SETUP FULL will allow you to start with a full world of random agents.

## Parameters of Interest

- `mutation-rate`: range [0.0, 1.0], default=0.005, step=0.001
- `death-rate`: range [0.0, 1.0], default=0.1, step=0.05
- `immigrants-per-day`: range [0.0, 100.0], default=1.0, step=1.0
- `initial-PTR`: range [0.0, 1.0], default=0.12, step=0.01
- `cost-of-giving`: range [0.0, 1.0], default=0.01, step=0.01
- `gain-of-receiving`: range [0.0, 1.0], default=0.03, step=0.01
- `immigrant-chance-cooperate-with-same`: range [0.0, 1.0], default=0.5, step=0.01
- `immigrant-chance-cooperate-with-different`: range [0.0, 1.0], default=0.5, step=0.01

## Output of Interest

- Strategy Counts

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Ethnocentrism.nlogo`
