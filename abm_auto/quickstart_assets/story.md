# SIR epidemic on a small-world network

## The phenomenon

A disease spreads through a population connected in a small-world social
network. Each person is Susceptible, Infected, or Recovered. We want the
classic epidemic curve: infections rise, peak, then fall as the population
gains immunity.

## Agents

The population is 200 people. Each person has:
- a **state**: one of `S` (susceptible), `I` (infected), `R` (recovered);
- a fixed set of **neighbours** in the network.

## Network

A Watts–Strogatz small-world network: each person connected to `k = 6`
nearest neighbours, with rewiring probability `0.1`.

## Mechanism (each time step)

1. **Infection.** For every infected person, each susceptible neighbour
   becomes infected with probability `beta = 0.15` per contact this step.
2. **Recovery.** Every infected person recovers with probability
   `gamma = 0.05` per step. Recovered people are immune and never reinfected.

## Initial condition

5 randomly chosen people start Infected; everyone else starts Susceptible.

## What to observe

Record, at each time step, the count of people in each state (S, I, R).
Run for 100 steps. Expected result: a single epidemic wave — the infected
count rises to a peak, then decays toward zero as the susceptible pool is
depleted.
