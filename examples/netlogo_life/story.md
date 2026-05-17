# Story: Life

## Research Motivation

This program is an example of a two-dimensional cellular automaton.  This particular cellular automaton is called The Game of Life.

A cellular automaton is a computational machine that performs actions based on certain rules.  It can be thought of as a board which is divided into cells (such as square cells of a checkerboard).  Each cell can be either "alive" or "dead."  This is called the "state" of the cell.  According to specified rules, each cell will be alive or dead at the next time step.

## Research Goal

The rules of the game are as follows.  Each cell checks the state of itself and its eight surrounding neighbors and then sets itself to either alive or dead.  If there are less than two alive neighbors, then the cell dies.  If there are more than three alive neighbors, the cell dies.  If there are 2 alive neighbors, the cell remains in the state it is in.  If there are exactly three alive neighbors, the cell becomes alive. This is done in parallel and continues forever.

There are certain recurring shapes in Life, for example, the "glider" and the "blinker". The glider is composed of 5 cells which form a small arrow-headed shape, like this:

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Patch-based grid model. Each patch holds local state variables.

## Dynamics

The INITIAL-DENSITY slider determines the initial density of cells that are alive.  SETUP-RANDOM places these cells.  GO-FOREVER runs the rule forever.  GO-ONCE runs the rule once.

If you want to draw your own pattern, use the DRAW-CELLS button and then use the mouse to "draw" and "erase" in the view.

## Parameters of Interest

- `initial-density`: range [0.0, 100.0], default=35.0, step=0.1

## Output of Interest

- Time series of key aggregate metrics
- Emergent spatial patterns

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Life.nlogo`
