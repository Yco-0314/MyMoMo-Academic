# Story: Signaling Game

## Research Motivation

This is a model of a "signaling game", in which players try to use different signals to communicate about the current state of the world.

Signaling games were discussed by the philosopher David Lewis in his book _Convention_. Lewis uses the example of Paul Revere, who during the American Revolution, asked the custodian of the Old North church to use the following signals to warn the American patriots about the movements of the British army:

- If the British troops are coming by sea, hang two lanterns in the church steeple;
- If the British troops are coming by land, hang one lantern in the church steeple;
- If the British troop are not coming, don't hang any lantern.

## Research Goal

Blue circles at the top of the view represent different possible world states. They are labeled with letters.

Pink squares at the bottom represent possible signals. They are labeled with numbers. (You can think of those as the number of lanterns to hang if you want to.)

## Agent Description

**Player** agent with properties:

**State** agent with properties:

**Signal** agent with properties:

**Observation** agent with properties:

**Choice** agent with properties:

**Urn** agent with properties:
- `balls`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

There are only two parameters for this models: the NUMBER-OF-STATES and the NUMBER-OF-SIGNALS. Once you have chosen the values that you want for these two sliders, click SETUP to initialize the model and then GO (or GO ONCE) to run it.

The PROBABILITY OF SUCCESS plot (and the monitor by the same name) show how likely it is that a round of communication will be successful.

## Parameters of Interest

- `number-of-states`: range [2.0, 8.0], default=2.0, step=1.0
- `number-of-signals`: range [2.0, 8.0], default=2.0, step=1.0

## Output of Interest

- probability of success

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Signaling Game.nlogo`
