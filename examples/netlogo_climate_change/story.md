# Story: Climate Change

## Research Motivation

This is a model of energy flow in the earth, particularly heat energy. It shows the earth as rose colored, and the surface of the planet is represented by a black strip. Above the strip there is a blue atmosphere and black space at the top. Clouds and carbon dioxide (CO2) molecules can be added to the atmosphere. The CO2 molecules represent greenhouse gases that block infrared light that is emitted by the earth. Clouds block incoming or outgoing sun rays, influencing the heating up or cooling down of the planet.

## Research Goal

Yellow arrowheads stream downward representing sunlight energy. Some of the sunlight reflects off clouds and more can reflect off the earth's surface.

If sunlight is absorbed by the earth, it turns into a red dot, representing heat energy. Each dot represents the energy of one yellow sunlight arrowhead. The red dots randomly move around the earth, and its temperature is related to the total number of red dots.

## Agent Description

**Ray** agent with properties:

**Ir** agent with properties:

**Heat** agent with properties:

**Co2** agent with properties:

**Cloud** agent with properties:
- `cloud-speed`
- `cloud-id`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

The SUN-BRIGHTNESS slider controls how much sun energy enters the earth's atmosphere. A value of 1.0 corresponds to our sun. Higher values allow you to see what would happen if the earth was closer to the sun, or if the sun got brighter.

The ALBEDO slider controls how much of the sun energy hitting the earth is absorbed.
If the albedo is 1.0, the earth reflects all sunlight. This could happen if the earth froze, and it is indicated by a white surface. If the albedo is zero, the earth absorbs all sunlight. This is indicated as a black surface. The earth's albedo is about 0.6.

## Parameters of Interest

- `sun-brightness`: range [0.0, 5.0], default=1.0, step=0.2
- `albedo`: range [0.0, 1.0], default=0.6, step=0.05

## Output of Interest

- Global Temperature

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Climate Change.nlogo`
