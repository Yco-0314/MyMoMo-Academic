# Story: Hotelling'S Law

## Research Motivation

This model is a representation of Hotelling's law (1929), which examines the optimal placement of stores and pricing of their goods in order to maximize profit. In Hotelling's original paper, the stores were confined to a single dimension.  This model replicates and extends Hotelling's law, by allowing the stores to move freely on a plane.

In this model, several stores attempt to maximize their profits by moving and changing their prices.  Each consumer chooses their store of preference based on the distance to the store and the price of the goods it offers.

## Research Goal

Each consumer adds up the price and distance from each store, and then chooses to go to the store that offers the lowest sum. In the event of a tie, the consumer chooses randomly. The stores can either be constrained to one dimension, in which case all stores operate on a line, or they can be placed on a plane. Under the normal rule, each store tries to move randomly in the four cardinal directions to see if it can gain a larger market share; if not, it does not move. Then each store checks if it can earn a greater profit by increasing or decreasing the price of their goods; if not, it does not change the price. This decision is made without any knowledge of their competitors' strategies. There are two other conditions under which one can run this model: stores can either only change prices, or only move their location.

## Agent Description

**Turtle** agent with properties:
- `price`
- `area-count`

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

Press SETUP to create the stores and a visualization of their starting market share areas.
Press GO to have the model run continuously.
Press GO-ONCE to have the model run once.
The NUMBER-OF-STORES slider decides how many stores are in the world.

If the LAYOUT chooser is on LINE, then the stores will operate only on one dimension. If it is on PLANE, then the stores will operate in a two dimensional space.

## Parameters of Interest

- `number-of-stores`: range [2.0, 10.0], default=2.0, step=1.0

## Output of Interest

- revenues
- prices
- areas

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Hotelling's Law.nlogo`
