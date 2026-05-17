# Story: Daisyworld

## Research Motivation

This model explores the "Gaia hypothesis", which considers the Earth as a single, self-regulating system including both living and non-living parts. In particular, this model explores how living organisms both alter and are altered by climate, which is non-living. The example organisms are daisies and the climatic factor considered is temperature.

Daisyworld is a world filled with two different types of daisies: black daisies and white daisies.  They differ in albedo, which is how much energy they absorb as heat from sunlight.  White daisies have a high surface albedo and thus reflect light and heat, thus cooling the area around them.  Black daisies have a low surface albedo and thus absorb light and heat, thus heating the area around them.  However, there is only a certain temperature range in which daisies can reproduce; if the temperature around a daisy is outside of this range, the daisy will produce no offspring and eventually die of old age.

When the climate is too cold it is necessary for the black daisies to propagate in order to raise the temperature, and vice versa -- when the climate is too warm, it is necessary for more white daisies to be produced in order to cool the temperature.  For a wide range of parameter settings, the temperature and the population of daisies will eventually stabilize.  However, it is possible for Daisyworld to get either too hot or too cold, in which case the daisies are not able to bring the temperature back under control and all of the daisies will eventually die.

## Research Goal

White daisies, black daisies, and open ground (empty patches) each have an albedo or percentage of energy they absorb as heat from sunlight. Sunlight energy can be changed with the SOLAR-LUMINOSITY slider (a value of 1.0 simulates the average solar luminosity of our sun).

Each time step, every patch will calculate the temperature at that spot based on (1) the energy absorbed by the daisy at that patch and (2) the diffusion of 50% of the temperature value at that patch between its neighbors.  Open ground patches that are adjacent to a daisy have a probability of sprouting a daisy that is the same color as the neighboring daisy, based on a parabolic probability function that depends on the local temperature (where an optimum temperature of 22.5 yields a maximum probability of 100% of sprouting a new daisy). Daisies age each step of the simulation until they reach a maximum age, at which point they die and the patch they were in becomes open.

## Agent Description

**Daisy** agent with properties:
- `age`
- `albedo`

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

START-%-WHITES and START-%-BLACKS sets the starting percentage of the patches that will be occupied by daisies (of either color) after pressing SETUP.

Selecting PAINT-DAISIES-AS and pressing PAINT-DAISIES allows the user to draw or erase daisies in the VIEW, by left clicking on patches.

## Parameters of Interest

- `albedo-of-surface`: range [0.0, 1.0], default=0.4, step=0.01
- `solar-luminosity`: range [0.001, 3.0], default=0.8, step=0.001
- `albedo-of-whites`: range [0.0, 0.99], default=0.75, step=0.01
- `albedo-of-blacks`: range [0.0, 0.99], default=0.25, step=0.01

## Output of Interest

- Luminosity
- Global Temperature
- Population

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Daisyworld.nlogo`
