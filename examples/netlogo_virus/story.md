# Story: Virus

## Research Motivation

This model simulates the transmission and perpetuation of a virus in a human population.

Ecological biologists have suggested a number of factors which may influence the survival of a directly transmitted virus within a population. (Yorke, et al. "Seasonality and the requirements for perpetuation and eradication of viruses in populations." Journal of Epidemiology, volume 109, pages 103-123)

## Research Goal

The model is initialized with 150 people, of which 10 are infected.  People move randomly about the world in one of three states: healthy but susceptible to infection (green), sick and infectious (red), and healthy and immune (gray). People may die of infection or old age.  When the population dips below the environment's "carrying capacity" (set at 300 in this model) healthy people may produce healthy (but susceptible) offspring.

Some of these factors are summarized below with an explanation of how each one is treated in this model.

## Agent Description

**Turtle** agent with properties:
- `sick?`
- `remaining-immunity`
- `sick-time`
- `age`

## Spatial Structure

Grid-based model with mobile agents.
World size: 35×35, toroidal (wrapping) boundaries.

## Dynamics

Each "tick" represents a week in the time scale of this model.

The INFECTIOUSNESS slider determines how great the chance is that virus transmission will occur when an infected person and susceptible person occupy the same patch.  For instance, when the slider is set to 50, the virus will spread roughly once every two chance encounters.

## Parameters of Interest

- `number-people`: range [10.0, 0.0], default=150.0, step=1.0
- `chance-recover`: range [0.0, 99.0], default=75.0, step=1.0
- `duration`: range [0.0, 99.0], default=20.0, step=1.0
- `infectiousness`: range [0.0, 99.0], default=65.0, step=1.0

## Output of Interest

- Populations

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Virus.nlogo`
