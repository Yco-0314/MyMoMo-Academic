# Story: Braess Paradox

## Research Motivation

This is an agent-based model intended to demonstrate a phenomenon from game theory (a subfield of economics) called Braess' paradox. The paradoxical aspect of Braess' paradox arises when an additional route is added to a traffic network that allows for very rapid transit. When this is done the traffic pattern can be changed to one that has both worse individual and global outcomes (travel times.) In short, we can open more roads and actually make traffic worse. (Braess et al., 2005)

Braess' paradox is a counter-intuitive result that arises when analyzing specific graphs through a game theoretic lens. These graphs are usually taken to be representations of traffic networks, but Braess' paradox is actually a wide-ranging phenomenon that can be applied in many contexts outside of traffic networks. For simplicity however, we will interpret and represent these graphs only as traffic networks in this model. Given a graph of a particular traffic network we can determine a stable set of strategies (routes for commuting from one point to another) that agents (autonomous commuters in this case) will prefer to adopt over all other strategies. This is called a Nash equilibrium. The strategies adopted by the commuters in the Nash equilibrium will lead to outcomes for the commuters. In this case the amount of time it takes them to reach their destination.

## Research Goal

The commuters in this model come into existence at the starting node of the traffic network in the upper left corner. The commuters are represented graphically as a car or truck, but this is just for visual effect. All commuters adhere to the same behavioral rules. Some heuristic is used by the commuters to determine the path they will take through the network before it begins its journey through the traffic grid. The commuter then moves, one road square (patch) at a time, and remains in that patch for a number of ticks before moving on to the next patch. When the commuter reaches the ending node it reports the path it took through the network and also the total number of ticks it spent in transit. This information is saved by the model and used to generate a "traffic report" which new commuters can then incorporate into their heuristic to choose the route they take.

Certain patches in this model are selected to represent roads. There are two types of road patches: static-cost roads and dynamic-cost roads. Static-cost roads require the car to stay in that patch for a fixed amount of time before moving on. Dynamic-cost roads require the car to stay in that patch for an amount of time that is based on the number of ticks since the last turtle occupied that patch, thus simulating congestion. There is also a switch in the model which allows a middle path of road patches of near zero cost to be opened or closed. As mentioned above when commuters reach the end of the traffic network they report their route choice and the time taken in ticks.

## Agent Description

**Commuter** agent with properties:
- `birth-tick`
- `ticks-here`
- `route`

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

The SETUP button initializes the model.

The GO button runs the model.

## Parameters of Interest

- `spawn-rate`: range [1.0, 10.0], default=10.0, step=1.0
- `smoothing`: range [1.0, 10.0], default=10.0, step=1.0
- `randomness`: range [0.0, 100.0], default=16.0, step=1.0

## Output of Interest

- Travel Time
- Routes Taken
- Probabilities

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Braess Paradox.nlogo`
