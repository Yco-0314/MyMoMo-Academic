# Story: Rock Paper Scissors

## Research Motivation

This model explores the role of movement and space in a three species ecosystem. The system consists of three species, represented by red patches, green patches, and blue patches, which compete over space. The interactions between the species are based on the game Rock-Paper-Scissors. That is, red beats green, green beats blue, and blue beats red. Organisms compete with their neighbors, move throughout the environment, and reproduce. These interactions result in spiral patterns whose size and stability depends on the movement rate of the organisms.

The model is written in an event-based fashion, to reflect the formulation of the published model. See HOW IT WORKS and EXTENDING THE MODEL.

## Research Goal

Each patch can be occupied by one of three species or can be blank. The species are represented by three colors: red, green, and blue. Each tick, the following types of events happen at defined average rates:

- Select event: Two random neighbors compete with each other. In competition, red beats green, green beats blue, and blue beats red, like in rock paper scissors. The losing patch becomes blanks.
- Reproduce event: Two random neighbors attempt to reproduce. If one of the neighbors is blank, it acquires the color of the other. Nothing happens if neither neighbor is blank.
- Swap event: Two random neighbors swap color. This represents the organisms moving.

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

Press SETUP to initialize the model and GO to run it.

SWAP-RATE-EXPONENT, REPRODUCE-RATE-EXPONENT, and SELECT-RATE-EXPONENT each control the rate at which their respective actions are performed. There will be an average of `count patches * 10 ^ rate-exponent` events each tick for each event type. This means that increasing a slider by `1.0` will result in that event type occurring 10 times more often, no matter what the other sliders are set to. The SWAP-%, REPRODUCE-%, and SELECT-% monitors indicate what percentage of events will be swap, reproduce, and select events (respectively) each tick.

## Parameters of Interest

- `swap-rate-exponent`: range [-1.0, 1.0], default=0.0, step=0.1
- `reproduce-rate-exponent`: range [-1.0, 1.0], default=0.0, step=0.1
- `select-rate-exponent`: range [-1.0, 1.0], default=0.0, step=0.1

## Output of Interest

- Populations

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Rock Paper Scissors.nlogo`
