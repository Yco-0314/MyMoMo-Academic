# Story: Standing Ovation Model

## Research Motivation

Miller and Page (2004) proposed the Standing Ovation Problem to study how individual quality judgments interact with social influence to produce collective binary decisions. The model illustrates how audience members decide to stand or remain seated after a performance, producing cascading behavior.

## Research Goal

Simulate an auditorium where agents decide to stand or sit based on perceived performance quality and the fraction of visible neighbors standing. Study how signal quality, social threshold, and vision range affect the emergence of standing ovations versus mixed outcomes.

## Agent Description

Each agent represents an audience member with:
- `standing`: boolean, whether currently standing (0 or 1)
- `quality_threshold`: personal quality threshold for standing (uniform random in [0,1])
- `social_threshold`: fraction of visible neighbors that must be standing to trigger social standing (default 0.5)

## Spatial Structure

Grid of 20x20 (400 audience members). Non-toroidal (bounded auditorium). Each agent can see neighbors within a configurable vision radius.

## Dynamics

**Initialization**: Each agent stands if `signal_quality > quality_threshold`, otherwise sits.

Each subsequent time step (100 periods):
1. Each agent counts the fraction of standing agents within their vision radius
2. If sitting and fraction_standing > `social_threshold`: stand up
3. If standing and fraction_standing < `social_threshold * 0.5`: sit down (minority pressure)
4. Record total fraction standing

## Parameters of Interest

- `signal_quality`: Overall performance quality broadcast to all (range 0.1-0.9, default 0.5)
- `social_threshold`: Fraction of neighbors needed to trigger social standing (range 0.1-0.8, default 0.5)
- `vision_radius`: How far each agent can see (range 1-5, default 2)

## Output of Interest

- Fraction of audience standing over time
- Final standing fraction (equilibrium)
- Time to reach equilibrium
- Spatial pattern of standing/sitting clusters

## Mode

Simulator (no calibration needed)

## Source

Miller, J.H. & Page, S.E. (2004). "The Standing Ovation Problem." Complexity, 9(5), 8-16.
