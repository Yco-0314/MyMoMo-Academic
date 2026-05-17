# Story: Rebellion

## Research Motivation

This project models the rebellion of a subjugated population against a central authority. It is is an adaptation of Joshua Epstein's model of civil violence (2002).

The population wanders around randomly. If their level of grievance against the central authority is high enough, and their perception of the risks involved is low enough, they openly rebel. A separate population of police officers ("cops"), acting on behalf of the central authority, seeks to suppress the rebellion. The cops wander around randomly and arrest people who are actively rebelling.

## Research Goal

Each "agent," or member of the general population, has an individual level of grievance toward the central authority. GRIEVANCE is based on the agent's PERCEIVED-HARDSHIP, which is assigned randomly at startup, and on GOVERNMENT-LEGITIMACY, which is global across agents and specified by a slider in the interface.

Each agent also calculates an individual risk of rebelling at the beginning of each turn.  This ESTIMATED-ARREST-PROBABILITY, is based on the number of cops and already rebelling agents within VISION patches, namely 1 - exp (- k * (C/A)<sub>v</sub>) --- where (C/A)<sub>v</sub> is the ratio of cops to active agents, and k is a constant set in "startup" to ensure a reasonable value when there is only one cop and one agent within a particular field of vision.  In our implementation, we changed one aspect of Epstein's description.  After dividing by C by A, we take the "floor" of the result (that is, round downwards to an integer).  Without this change, the model does not exhibit punctuated equilibrium.  The effect of the change is that if there are more rebels than cops in the neighborhood, the probability of arrest is zero, otherwise it is very nearly 1.0.  In other words, the rule could be written more simply as:

## Agent Description

**An-Agent** agent with properties:
- `risk-aversion`
- `perceived-hardship`
- `active?`
- `jail-term`

**Cop** agent with properties:

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

Use the sliders to pick the initial settings for the model. INITIAL-COP-DENSITY and POPULATION-DENSITY respectively determine the density of cops and agents in the world. VISION determines the number of patches in each direction that agents and cops can see.

Click SETUP to initialize the population. Click GO to begin the simulation.

## Parameters of Interest

- `government-legitimacy`: range [0.0, 1.0], default=0.82, step=0.01
- `max-jail-term`: range [0.0, 50.0], default=30.0, step=1.0
- `vision`: range [0.0, 10.0], default=7.0, step=0.1
- `initial-cop-density`: range [0.0, 100.0], default=4.0, step=0.1
- `initial-agent-density`: range [0.0, 100.0], default=70.0, step=1.0

## Output of Interest

- All agent types

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Rebellion.nlogo`
