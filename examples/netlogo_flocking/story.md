# Story: Flocking

## Research Motivation

This model is an attempt to mimic the flocking of birds.  (The resulting motion also resembles schools of fish.)  The flocks that appear in this model are not created or led in any way by special leader birds.  Rather, each bird is following exactly the same set of rules, from which flocks emerge.

## Research Goal

The birds follow three rules: "alignment", "separation", and "cohesion".

"Alignment" means that a bird tends to turn so that it is moving in the same direction that nearby birds are moving.

## Agent Description

**Turtle** agent with properties:
- `flockmates`
- `nearest-neighbor`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

First, determine the number of birds you want in the simulation and set the POPULATION slider to that value.  Press SETUP to create the birds, and press GO to have them start flying around.

The default settings for the sliders will produce reasonably good flocking behavior.  However, you can play with them to get variations:

## Parameters of Interest

- `population`: range [1.0, 1000.0], default=300.0, step=1.0
- `max-align-turn`: range [0.0, 20.0], default=5.0, step=0.25
- `max-cohere-turn`: range [0.0, 20.0], default=3.0, step=0.25
- `max-separate-turn`: range [0.0, 20.0], default=1.5, step=0.25
- `vision`: range [0.0, 10.0], default=5.0, step=0.5
- `minimum-separation`: range [0.0, 5.0], default=1.0, step=0.25

## Output of Interest

- Time series of key aggregate metrics
- Emergent spatial patterns

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Flocking.nlogo`
