# Phenomenon: cities stay segregated even when nobody wants segregation

## What I observe

I keep reading about urban neighborhoods that have stayed racially or
economically segregated for decades, even in cities where almost
nobody — surveyed individually — says they actively want to live in a
homogeneous block. Most people will tell you they'd be happy living
somewhere "diverse enough." Yet stable diversity is rare, and
clustering by group is the norm.

Three things make me suspect this isn't well-modeled by "people are
secretly more biased than they admit":

1. The pattern persists across generations, even as stated attitudes
   liberalise.
2. Cities with strong anti-discrimination policy show only slowly
   shrinking segregation indices.
3. Some informal observations suggest people DO move out when their
   immediate neighbours become too dissimilar — but the threshold for
   "too dissimilar" is modest, not extreme (people can be a small
   minority and stay; they leave when they become a tiny minority).

## Research question

What kind of agent rule, applied across a population whose individual
tolerance is genuinely high, would still produce city-scale persistent
clustering as the macro outcome?

I want a model that:

- Has a single, behaviourally plausible rule (e.g. "I move if my
  neighbours look too unlike me by some threshold T")
- Allows me to vary that threshold T and observe what level of
  individual "tolerance" still produces system-level clustering
- Captures whatever the threshold for cluster formation is, if one
  exists

I don't have a specific paper in mind. I want the system to propose a
mechanism, pick reasonable defaults, and tell me what happens at
different tolerance levels.

## What I do NOT want

- I'm not asking for a network model — neighbours here are SPATIAL
  (geographic adjacency), not "friends".
- I'm not asking for an opinion-dynamics model — agents don't change
  their group identity, they relocate.
- I'm not asking for a model with explicit racism as a parameter —
  the whole point is that individual preference can be modest yet
  macro outcome is clustered.

## Parameters I expect the model to estimate or sweep

Whatever the proposed mechanism, I want to see how the system-level
clustering metric responds to varying:

- An individual tolerance parameter (whatever shape the proposed
  mechanism gives it)
- Density / vacancy rate of the population on the grid
- Group composition ratio (e.g. 50/50 vs 70/30)

## Output

A research note explaining the proposed mechanism, the tipping-point
result (if any), and what tolerance level still permits stable
diversity vs. produces irreversible clustering.
