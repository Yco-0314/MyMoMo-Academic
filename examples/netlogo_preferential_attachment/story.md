# Story: Preferential Attachment

## Research Motivation

In some networks, a few "hubs" have lots of connections, while everybody else only has a few.  This model shows one way such networks can arise.

Such networks can be found in a surprisingly large range of real world situations, ranging from the connections between websites to the collaborations between actors.

This model generates these networks by a process of "preferential attachment", in which new network members prefer to make a connection to the more popular existing members.

## Research Goal

The model starts with two nodes connected by an edge.

At each step, a new node is added.  A new node picks an existing node to connect to randomly, but with some bias.  More specifically, a node's chance of being selected is directly proportional to the number of connections it already has, or its "degree." This is the mechanism which is called "preferential attachment."

## Agent Description

Agents are turtles on a grid.

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

Pressing the GO ONCE button adds one new node.  To continuously add nodes, press GO.

The LAYOUT? switch controls whether or not the layout procedure is run.  This procedure attempts to move the nodes around to make the structure of the network easier to see.

## Parameters of Interest


## Output of Interest

- Degree Distribution (log-log)
- Degree Distribution

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Preferential Attachment.nlogo`
