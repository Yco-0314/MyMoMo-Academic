# Story: Minority Game

## Research Motivation

This is a simplified model of an economic market.  In each time step, agents choose one of two sides, 0 or 1, and those on the minority side win a point.  This problem is inspired by the "El Farol" bar problem.  Each agent uses a finite set of strategies to make their decision based upon past record; however, the record consists only of which side, 0 or 1, was in the minority, not the actual population count of how many chose each side.

## Research Goal

Each agent begins with a score of 0 and STRATEGIES-PER-AGENT strategies. Initially, they choose a random one of these strategies to use.  The initial historical record is generated randomly.  If their current strategy correctly predicted whether 0 or 1 would be the minority, they add one point to their score.  Each strategy also earns virtual points according to if it would have been correct or not.  From then on, the agents will then use their strategy with the highest virtual point total to predict whether they should select 0 or 1.

This strategy consist of a list of 1's and 0's that is 2<sup>MEMORY</sup> long.  The choice the turtle then makes is based off of the history of past choices.  This history is also a list of 1's and 0's that is MEMORY long, but it is encoded into a binary number.  The binary number is then used as an index into the strategy list to determine the choice.

## Agent Description

**Turtle** agent with properties:
- `score`
- `choice`
- `strategies`
- `current-strategy`
- `strategies-scores`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

GO: Starts and stops the model.

SETUP: Resets the simulation according to the parameters set by the sliders.

## Parameters of Interest

- `number`: range [1.0, 1501.0], default=501.0, step=2.0
- `memory`: range [1.0, 12.0], default=6.0, step=1.0
- `strategies-per-agent`: range [1.0, 10.0], default=5.0, step=1.0

## Output of Interest

- Success rate
- Number Picking Zero
- Scores
- Success histogram

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Minority Game.nlogo`
