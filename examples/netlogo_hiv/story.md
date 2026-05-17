# Story: Hiv

## Research Motivation

This model simulates the spread of the human immunodeficiency virus (HIV), via sexual transmission, through a small isolated human population.  It therefore illustrates the effects of certain sexual practices across a population.

As is well known now, HIV is spread in a variety of ways of which sexual contact is only one.  HIV can also be spread by needle-sharing among injecting drug users, through blood transfusions (although this has become very uncommon in countries like the United States in which blood is screened for HIV antibodies), or from HIV-infected women to their babies either before or during birth, or afterwards through breast-feeding.  This model focuses only on the spread of HIV via sexual contact.

The model examines the emergent effects of four aspects of sexual behavior.  The user controls the population's tendency to practice abstinence, the amount of time an average "couple" in the population will stay together, the population's tendency to use condoms, and the population's tendency to get tested for HIV.  Exploration of the first and second variables may illustrate how changes in sexual mores in our society have contributed to increases in the prevalence of sexually transmitted diseases, while exploration of the third and fourth may provide contemporary solutions to the problem.

## Research Goal

The model uses "couples" to represent two people engaged in sexual relations.  Individuals wander around the world when they are not in couples.  Upon coming into contact with a suitable partner, there is a chance the two individuals will "couple" together.  When this happens, the two individuals no longer move about, they stand next to each other holding hands as a representation of two people in a sexual relationship.

The presence of the virus in the population is represented by the colors of individuals. Three colors are used: green individuals are uninfected, blue individuals are infected but their infection is unknown, and red individuals are infected and their infection is known.

## Agent Description

**Turtle** agent with properties:
- `infected?`
- `known?`
- `infection-length`
- `coupled?`
- `couple-length`
- `commitment`
- `coupling-tendency`
- `condom-use`
- `test-frequency`
- `partner`

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

The SETUP button creates individuals with particular behavioral tendencies according to the values of the interface's five sliders (described below).  Once the simulation has been setup, you are now ready to run it, by pushing the GO button.  GO starts the simulation and runs it continuously until GO is pushed again.  During a simulation initiated by GO, adjustments in sliders can affect the behavioral tendencies of the population.

A monitor shows the percent of the population that is infected by HIV.  In this model each time-step is considered one week; the number of weeks that have passed is shown in the toolbar.

## Parameters of Interest

- `initial-people`: range [50.0, 500.0], default=300.0, step=1.0
- `average-commitment`: range [1.0, 200.0], default=50.0, step=1.0
- `average-coupling-tendency`: range [0.0, 10.0], default=5.0, step=1.0
- `average-condom-use`: range [0.0, 10.0], default=0.0, step=1.0
- `average-test-frequency`: range [0.0, 2.0], default=0.0, step=0.01

## Output of Interest

- Populations

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `HIV.nlogo`
