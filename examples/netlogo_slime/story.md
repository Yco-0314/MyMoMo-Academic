# Story: Slime

## Research Motivation

This model is inspired by the aggregation behavior of slime-mold cells.
The slime mold spends much of its life as thousands of distinct single-celled units, each moving separately. Under the right conditions, those many cells will coalesce into a single, larger organism. When the environment is less hospitable, the slime mold acts as a single organism; when the weather turns cooler and the mold enjoys a large food supply, "it" becomes a "they." The slime mold oscillates between being a single creature and a swarm.

This model shows how creatures can aggregate into clusters without the control of a "leader" or "pacemaker" cell. This finding was first described by Evelyn Fox Keller and Lee Segel in a paper in 1970.

Before Keller began her investigations, the conventional belief had been that slime mold swarms formed at the command of "pacemaker" cells that ordered the other cells to begin aggregating. In 1962, Shafer showed how the pacemakers could use cyclic AMP as a signal of sorts to rally the troops; the slime mold generals would release the compounds at the appropriate moments, triggering waves of cyclic AMP that washed through the entire community, as each isolated cell relayed the signal to its neighbors. Slime mold aggregation, in effect, was a giant game of Telephone — but only a few elite cells placed the original call.

## Research Goal

Simulate the Slime model and observe emergent dynamics. Identify key parameters driving system behavior through parameter sweeps.

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

Click the SETUP button to set up a collection of slime-mold cells. Click the GO button to start the simulation.

The POPULATION slider controls the number of slime mold cells in the simulation. Changes in the POPULATION slider do not have any effect until the next SETUP command.

## Parameters of Interest

- `population`: range [1.0, 1500.0], default=400.0, step=1.0
- `sniff-threshold`: range [0.0, 5.0], default=1.0, step=0.1
- `sniff-angle`: range [0.0, 180.0], default=45.0, step=1.0
- `wiggle-angle`: range [0.0, 45.0], default=40.0, step=1.0
- `wiggle-bias`: range [-40.0, 40.0], default=0.0, step=1.0

## Output of Interest

- Time series of key aggregate metrics
- Emergent spatial patterns

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Slime.nlogo`
