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

1. Every agent plays the game against 10 randomly chosen opponents and
   accumulates the resulting payoff as its score. Use a baseline fitness of
   1 + score so fitness stays positive.
2. The population then undergoes a **Moran process**: each generation about half
   the population (a per-generation death rate of 0.5) dies and is replaced by
   offspring of survivors chosen with probability proportional to fitness
   (score). Offspring inherit the parent's strategy, except that with a small
   mutation probability μ = 0.01 an offspring instead adopts a random strategy
   (Hawk or Dove). Mutation is what lets a uniform population be invaded.
   Population size is constant. A substantial turnover each generation is what
   makes selection (and mutation) act fast enough to reach the ESS within the run.

## Parameters

- Population size N = 200
- 300 generations
- V = 2, C = 4
- Opponents sampled per agent each generation = 10
- Per-generation death rate = 0.5 (about half the population is replaced)
- Mutation probability μ = 0.01
- Initial condition: every agent starts as Hawk (an all-Hawk population)

## What to reproduce

Starting from an all-Hawk population, the fraction of Hawks converges down to the
evolutionarily stable strategy p* = V / C = 0.5: mutation seeds a few invading
Doves, and fitness-proportional selection then balances the two strategies at the
ESS. (Without mutation an all-Hawk start would stay frozen — selection alone
cannot create the Doves it needs.)
