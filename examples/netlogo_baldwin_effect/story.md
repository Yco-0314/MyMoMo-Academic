# Story: Baldwin Effect

## Research Motivation

The purpose of this model is to investigate, in a quantitative manner, how learning can affect evolution. This model aims to demonstrate that "better learning" organisms, in certain environments, are more effective in expediting the evolutionary search to find good genotypes, even when the specific adaptations that are learned are not communicated to the genotype.

The relationship between evolution and learning has been debated at length. The two concepts are most commonly related by what is known as the Baldwin effect. The Baldwin effect suggests that phenotypic plasticity, a more general term that includes learning, can enhance evolution. More specifically the Baldwin effect states: (1) organisms adapt to the environment individually, (2) genetic factors produce hereditary characteristics similar to the ones made available by individual adaptation, and (3) these hereditary traits are favoured by natural selection and spread in the population.

Using a computational model, Hinton & Nowlan (1996) influentially suggested that learning can qualitatively speed up evolution. Taking Hinton & Nowlan’s study as a starting point, in addition to showing the difference between the evolution of learning and non-learning populations, this model considers three populations: two populations that learn in different ways such that one population is better at learning than the other one and one non-learning population. In other words, this model investigates to what extent the Baldwin effect might manifest itself with different learning abilities.

## Research Goal

At each timestep, each agent

* tries to learn phenotypes of high fitness based on their learning rules
* has a chance of dying if it has a low fitness value
* has a chance of reproducing if they have a high fitness value.

## Agent Description

**Non-Learner** agent with properties:

**Random-Learner** agent with properties:

**Smart-Learner** agent with properties:

## Spatial Structure

Grid-based model with mobile agents.

## Dynamics

The SETUP button initializes the model.

The GO button runs the model.

## Parameters of Interest

- `num-pop`: range [1.0, 500.0], default=200.0, step=1.0
- `gene-length`: range [1.0, 100.0], default=30.0, step=1.0
- `plasticity`: range [0.0, 1.0], default=0.5, step=0.01
- `num-trials`: range [1.0, 100.0], default=20.0, step=1.0
- `mutation-rate`: range [0.0, 10.0], default=5.0, step=0.1
- `smoothness`: range [0.0, 1.0], default=0.15, step=0.01

## Output of Interest

- Average Fitness
- Percentage of Plastic Alleles
- Percentage of Correct Alleles

## Mode

Simulator (no calibration needed)

## Source

Converted from NetLogo Models Library: `Baldwin Effect.nlogo`
