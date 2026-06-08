# Reproduce: evolution of Hawk-Dove strategies under a Moran process

A well-mixed population of agents repeatedly plays the Hawk-Dove game and evolves
by fitness-proportional reproduction. This is a textbook evolutionary-game model;
the goal is to reproduce its evolutionarily stable strategy.

## Agents

Each agent has a fixed **strategy** — Hawk (1) or Dove (0) — and an accumulated
**score** (its payoff this generation). Agents do not move or sit on a network;
the population is well-mixed.

## The game (a payoff matrix)

Agents interact pairwise via the Hawk-Dove game with resource value V = 2 and
fight cost C = 4. The payoff to the row player is:

- Hawk vs Hawk: (V − C) / 2 = −1
- Hawk vs Dove: V = 2
- Dove vs Hawk: 0
- Dove vs Dove: V / 2 = 1

## Each generation

1. Every agent plays the game against several randomly chosen opponents and
   accumulates the resulting payoff as its score. Use a baseline fitness of
   1 + score so fitness stays positive.
2. The population then undergoes a **Moran process**: some individuals die and
   are replaced by offspring of survivors chosen with probability proportional
   to fitness (score). Offspring inherit the parent's strategy. Population size
   is constant.

## Parameters

- Population size N = 200
- 300 generations
- V = 2, C = 4

## What to reproduce

The fraction of Hawks converges to the evolutionarily stable strategy
p* = V / C = 0.5, approached from either an all-Hawk or an all-Dove start.
