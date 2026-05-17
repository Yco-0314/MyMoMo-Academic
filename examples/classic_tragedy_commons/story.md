# Story: Tragedy of the Commons

## Research Motivation

Garrett Hardin (1968) described how shared resources are depleted when individuals acting in self-interest overconsume. Elinor Ostrom later showed that communities can develop governance mechanisms to sustain commons. This model simulates resource harvesting on a spatial landscape to observe depletion dynamics and the role of harvest restraint.

## Research Goal

Simulate agents harvesting a shared renewable resource on a grid. Study how harvest rate, resource regeneration, and population density interact to produce sustainable equilibrium versus resource collapse.

## Agent Description

Each agent is a harvester with:
- `harvest_rate`: personal harvesting intensity (uniform random in [0.5, 2.0])
- `energy`: accumulated resource from harvesting (starts at 10)
- `alive`: boolean (dies if energy reaches 0)

## Spatial Structure

Grid of 25x25 (625 patches). Toroidal. Each patch has a `resource` level (float, 0 to `max_resource`). 150 agents placed randomly on the grid.

## Dynamics

Each time step (300 periods):
1. **Resource regeneration**: Each patch regenerates at rate `regrowth_rate * (1 - resource/max_resource)` (logistic growth)
2. **Harvesting**: Each agent harvests `min(harvest_rate, patch_resource)` from their current patch, adding to their energy
3. **Movement**: Each agent moves to the neighboring patch with the highest resource level (greedy foraging)
4. **Metabolism**: Each agent loses 1 energy per step for survival cost
5. **Death**: Agents with energy <= 0 die (set alive=false, skip in future steps)
6. **Environment tracking**: Record total resource, number alive agents, average energy

## Parameters of Interest

- `num_agents`: Number of harvesters (range 50-300, default 150)
- `regrowth_rate`: Resource regeneration speed (range 0.01-0.2, default 0.05)
- `max_resource`: Maximum resource per patch (range 5-50, default 20)
- `mean_harvest_rate`: Average agent harvest intensity (range 0.5-3.0, default 1.0)

## Output of Interest

- Total resource level over time
- Number of surviving agents over time
- Average agent energy over time
- Resource depletion rate
- Whether system reaches sustainable equilibrium or collapses

## Mode

Simulator (no calibration needed)

## Source

Hardin, G. (1968). "The Tragedy of the Commons." Science, 162, 1243-1248.
Ostrom, E. (1990). "Governing the Commons." Cambridge University Press.
