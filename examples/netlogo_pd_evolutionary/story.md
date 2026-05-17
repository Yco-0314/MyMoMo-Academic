# Story: Prisoner'S Dilemma Basic Evolutionary

## Research Motivation

One of the most prominently studied phenomena in Game Theory is the "Prisoner's Dilemma."  The Prisoner's Dilemma, which was formulated by Melvin Drescher and Merrill Flood and named by Albert W. Tucker, is an example of a class of games called non-zero-sum games. This model explores the dynamics of agents on a grid playing iterated prisoner's dilemma with their neighbors and then adapting their strategy to match their best performing neighbor at each iteration.

In zero-sum games, total benefit to all players add up to zero, or in other words, each player can only benefit at the expense of other players (e.g. chess, football, poker --- one person can only win when the opponent loses).  On the other hand, in non-zero-games, each person's benefit does not necessarily come at the expense of someone else.  In many non-zero-sum situations, a person can benefit only when others benefit as well.  Non-zero-sum situations exist where the supply of a resource is not fixed or limited in any way (e.g. knowledge, artwork, and trade).  Prisoner's Dilemma, as a non-zero-sum game, demonstrates a conflict between rational individual behavior and the benefits of cooperation in certain situations.  The classical prisoner's dilemma is as follows:

Two suspects are apprehended by the police.  The police do have enough evidence to convict these two suspects.  As a result, they separate the two, visit each of them, and offer both the same deal:  "If you confess, and your accomplice remains silent, he goes to jail for 10 years and you can go free.  If you both remain silent, only minor charges can be brought upon both of you and you guys get 6 months each.  If you both confess, then each of you two gets 5 years."

## Research Goal

Each patch will either cooperate (blue) or defect (red) in the initial start of the model.  At each cycle, each patch will interact with all of its 8 neighbors to determine the score for the interaction.  Should a patch have cooperated, its score will be the number of neighbors that also cooperated.  Should a patch defect, then the score for this patch will be the product of the Defection-Award multiple and the number of neighbors that cooperated (i.e. the patch has taken advantage of the patches that cooperated).

In the subsequent round, the patch will set its old-cooperate? to be the strategy it used in the previous round.  For the upcoming round, the patch will adopt the strategy of one of its neighbors that scored the highest in the previous round.

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

Decide what percentage of patches should cooperate at the initial stage of the simulation and change the INITIAL-COOPERATION slider to match what you would like.  Next, determine the DEFECTION-AWARD multiple (mentioned as alpha in the payoff matrix above) for defecting (not cooperating).  The Defection-Award multiple varies from range of 0 to 3.  Press SETUP and note that red patches (that will defect) and blue patches (cooperate) are scattered across the  .  Press GO to make the patches interact with their eight neighboring patches.  First, they count the number of neighboring patches that are cooperating.  If a patch is cooperating, then its score is number of neighboring patches that also cooperated.   If a patch is defecting, then its score is the product of the number of neighboring patches who are cooperating and the Defection-Award multiple.

## Parameters of Interest

- `initial-cooperation`: range [0.0, 100.0], default=66.6, step=0.1
- `defection-award`: range [0.0, 3.0], default=1.59, step=0.01

## Output of Interest

- Cooperation/Defection Frequency

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Prisoner's Dilemma Basic Evolutionary.nlogo`
