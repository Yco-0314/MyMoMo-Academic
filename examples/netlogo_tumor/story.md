# Story: Tumor

## Research Motivation

This model illustrates the growth of a tumor and how it resists chemical treatment.  A tumor consists of two kinds of cells: stem cells (blue turtles) and transitory cells (all other turtles).

## Research Goal

During mitosis, a stem cell can divide either asymmetrically or symmetrically. In asymmetric mitosis, one of the two daughter cells remains a stem cell, replacing its parent. So a stem cell effectively never dies - it is quasi reincarnated after each division. The other daughter cell turns into a transitory cell that moves outward.

Young transitory cells may divide, breeding other transitory cells.  The transitory cells stop dividing at a certain age and change color from red to white to black, eventually dying.

## Agent Description

**Turtle** agent with properties:
- `stem?`
- `age`
- `metastatic?`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

SETUP: Clears the world and creates two blue neoplastic (cancerous) stem cells.  One cell stays put and the other moves to the right.
GO: Runs the simulation.
KILL TRANSITORY CELLS: Kills transitory cells that are younger than 10 time steps.
KILL STEM CELL:  Kills a stem cell. If the adjacent KILL-MOVING-CELL switch is set to OFF, the original is eliminated. If the switch is set to ON, the moving stem cell is eliminated.
KILL-MOVING-CELL: Determines which stem cell is killed when the KILL STEM CELL button is pressed.
LEAVE-TRAIL: If it's ON, the cells trace their paths; if it's OFF, they do not.
CELL-COUNT: Displays the total number of living cells.
LIVING CELLS PLOT: plots the number of living cells.

## Parameters of Interest

- `cell-count`

## Output of Interest

- Living Cells

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Tumor.nlogo`
