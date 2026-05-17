# Story: SIR Epidemic Spreading Model

## Research Motivation

I want to study how an infectious disease spreads through a population. The classic SIR
(Susceptible-Infected-Recovered) model is the foundation for understanding epidemic dynamics.

## Research Goal

Simulate the spread of an infectious disease in a closed population of 500 individuals
over 100 time steps. Observe how the infection rate and recovery rate affect the epidemic curve
(the number of infected individuals over time). Identify the threshold conditions for an epidemic
to take off versus die out.

## Agent Description

Each individual in the population is an **agent** with one of three states:
- **S (Susceptible)**: Healthy, can be infected upon contact with an Infected agent
- **I (Infected)**: Sick, can infect Susceptible agents with probability `infection_prob`
- **R (Recovered)**: Recovered, immune and cannot be re-infected

## Spatial Structure

Use a **grid** of size 20×25 (= 500 cells, one agent per cell). Agents can move randomly
to adjacent cells each time step. Infection spreads to neighboring Susceptible agents within
radius 1.

## Dynamics

Each time step:
1. Each Infected agent attempts to infect each Susceptible neighbor with probability `infection_prob`
2. Each Infected agent recovers with probability `recovery_prob` (transitions I → R)
3. Each agent moves to a random adjacent cell

## Parameters of Interest

- `infection_prob`: Probability of infection per contact (explore range 0.1 – 0.5)
- `recovery_prob`: Probability of recovery per time step (explore range 0.05 – 0.3)
- `initial_infected`: Number of initially infected agents (start with 5)

## Output of Interest

- Number of S, I, R agents at each time step (epidemic curve)
- Peak infection count and timing
- Final recovered fraction (total epidemic size)

## Mode

Simulator (no calibration needed for this study)
