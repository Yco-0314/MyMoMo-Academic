# Story: Traffic Basic

## Research Motivation

This model models the movement of cars on a highway. Each car follows a simple set of rules: it slows down (decelerates) if it sees a car close ahead, and speeds up (accelerates) if it doesn't see a car ahead. The model demonstrates how traffic jams can form even without any accidents, broken bridges, or overturned trucks.  No "centralized cause" is needed for a traffic jam to form.

## Research Goal

Simulate the Traffic Basic model and observe emergent dynamics. Identify key parameters driving system behavior through parameter sweeps.

## Agent Description

**Turtle** agent with properties:
- `speed`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

Click on the SETUP button to set up the cars.

Set the NUMBER-OF-CARS slider to change the number of cars on the road.

## Parameters of Interest

- `number-of-cars`: range [1.0, 41.0], default=20.0, step=1.0
- `deceleration`: range [0.0, 0.099], default=0.026, step=0.001
- `acceleration`: range [0.0, 0.0099], default=0.0045, step=0.0001

## Output of Interest

- Car speeds

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Traffic Basic.nlogo`
