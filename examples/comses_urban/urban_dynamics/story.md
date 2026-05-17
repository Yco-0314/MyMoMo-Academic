# Story: Urban Dynamics and Sprawl

## Research Motivation

Urban sprawl is a major global challenge, as cities expand outward consuming farmland and increasing commute distances. This model simulates how residents' activity choices (walking, cycling, driving) and facility placement policies affect urban spatial structure and sprawl patterns.

## Research Goal

Simulate an abstract city with residents choosing where to live and how to commute. Study how pedestrian-friendly policies, bicycle promotion, and automobile restrictions affect urban density, sprawl extent, and resident satisfaction.

## Agent Description

Each agent represents a household with:
- `location_x`, `location_y`: current residence on grid
- `mode`: transport mode (0=walk, 1=bike, 2=car)
- `satisfaction`: float measuring happiness with current location (0-1)
- `income`: float affecting transport choice (uniform random 20-100)

## Spatial Structure

Grid of 30x30 (900 patches). Non-toroidal. Each patch has:
- `land_type`: 0=empty, 1=residential, 2=commercial, 3=park
- `accessibility`: float measuring proximity to facilities (0-1)

200 agents initially clustered near center.

## Dynamics

Each time step (200 periods):
1. Satisfaction update: Each agent calculates satisfaction based on accessibility to facilities, local density, commute cost based on transport mode
2. Relocation: Agents with satisfaction < `move_threshold` search for better location within search radius and move if found
3. Mode choice: Agents update transport mode based on distance to nearest facility and income
4. Environment tracks: urban extent (furthest occupied patch from center), average density, average satisfaction, mode share

## Parameters of Interest

- `num_agents`: Number of households (range 100-400, default 200)
- `move_threshold`: Satisfaction below which agent relocates (range 0.2-0.6, default 0.3)
- `car_cost_factor`: Relative cost penalty for driving (range 0.5-3.0, default 1.0)
- `bike_infrastructure`: Bonus satisfaction for cycling (range 0.0-0.5, default 0.1)

## Output of Interest

- Urban extent over time
- Average density over time
- Mode share (walk/bike/car fractions) over time
- Average satisfaction over time

## Mode

Simulator (no calibration needed)

## Source

CoMSES: https://www.comses.net/codebases/20a1e7dc-0ab9-4e41-bb53-14a1da86e088/
