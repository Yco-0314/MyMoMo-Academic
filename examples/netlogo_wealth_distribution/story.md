# Story: Wealth Distribution

## Research Motivation

This model simulates the distribution of wealth.  "The rich get richer and the poor get poorer" is a familiar saying that expresses inequity in the distribution of wealth.  In this simulation, we see Pareto's law, in which there are a large number of "poor" or red people, fewer "middle class" or green people, and many fewer "rich" or blue people.

## Research Goal

This model is adapted from Epstein & Axtell's "Sugarscape" model. It uses grain instead of sugar.  Each patch has an amount of grain and a grain capacity (the amount of grain it can grow).  People collect grain from the patches, and eat the grain to survive.  How much grain each person accumulates is his or her wealth.

The model begins with a roughly equal wealth distribution.  The people then wander around the landscape gathering as much grain as they can.  Each person attempts to move in the direction where the most grain lies.  Each time tick, each person eats a certain amount of grain.  This amount is called their metabolism.  People also have a life expectancy.  When their lifespan runs out, or they run out of grain, they die and produce a single offspring.  The offspring has a random metabolism and a random amount of grain, ranging from the poorest person's amount of grain to the richest person's amount of grain.  (There is no inheritance of wealth.)

## Agent Description

**Turtle** agent with properties:
- `age`
- `wealth`
- `life-expectancy`
- `metabolism`
- `vision`

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

The PERCENT-BEST-LAND slider determines the initial density of patches that are seeded with the maximum amount of grain.  This maximum is adjustable via the MAX-GRAIN variable in the SETUP procedure in the procedures window.  The GRAIN-GROWTH-INTERVAL slider determines how often grain grows.  The NUM-GRAIN-GROWN slider sets how much grain is grown each time GRAIN-GROWTH-INTERVAL allows grain to be grown.

The NUM-PEOPLE slider determines the initial number of people.  LIFE-EXPECTANCY-MIN is the shortest number of ticks that a person can possibly live.  LIFE-EXPECTANCY-MAX is the longest number of ticks that a person can possibly live.  The METABOLISM-MAX slider sets the highest possible amount of grain that a person could eat per clock tick.  The MAX-VISION slider is the furthest possible distance that any person could see.

## Parameters of Interest

- `max-vision`: range [1.0, 15.0], default=5.0, step=1.0
- `grain-growth-interval`: range [1.0, 10.0], default=1.0, step=1.0
- `metabolism-max`: range [1.0, 25.0], default=15.0, step=1.0
- `num-people`: range [2.0, 1000.0], default=250.0, step=1.0
- `percent-best-land`: range [5.0, 25.0], default=10.0, step=1.0
- `life-expectancy-max`: range [1.0, 100.0], default=83.0, step=1.0
- `num-grain-grown`: range [1.0, 10.0], default=4.0, step=1.0
- `life-expectancy-min`: range [1.0, 100.0], default=1.0, step=1.0

## Output of Interest

- Class Plot
- Class Histogram
- Lorenz Curve
- Gini-Index v. Time

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Wealth Distribution.nlogo`
