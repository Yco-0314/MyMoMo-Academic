# Story: A replication and extension of the Taylor's Simulation Model of Insurance Market Dynamics in C#

## Research Motivation

A simple model is constructed using C\# in order to to capture key features of market dynamics, while also producing reasonable results for the individual insurers. A replication of Taylor's model is also constructed in order to compare results with the new premium setting mechanism. To enable the comparison of the two premium mechanisms, the rest of the model set-up is maintained as in the Taylor model. As in the Taylor example, homogeneous customers represented as a total market exposure which is allocated amongst the insurers.

In each time period, the model undergoes the following steps:
1. Insurers set competitive premiums per exposure unit
2. Losses are generated based on each insurer's share of the market exposure
3. Accounting results are calculated for each insurer
4. Insurers enter or exit the market based on the accounting results
5. Exposure is reallocated among the insurers based on their competitive premiums

## Research Goal

A simple model is constructed using C\# in order to to capture key features of market dynamics, while also producing reasonable results for the individual insurers. A replication of Taylor's model is also constructed in order to compare results with the new premium setting mechanism. To enable the comparison of the two premium mechanisms, the rest of the model set-up is maintained as in the Taylor model. As in the Taylor example, homogeneous customers represented as a total market exposure which is allocated amongst the insurers.

In each time period, the model undergoes the following steps:
1. Insurers set competitive premiums per exposure unit
2. Losses are generated based on each insurer's share of the market exposure
3. Accounting results are calculated for each insurer 
...

## Agent Description

Agent types and behavioral rules should be inferred from the model description above. Use the associated publication for detailed specifications if available.

## Domain Tags

model replication, market dynamics, pricing, insurance, Agent based modelling, Extension

## Parameters of Interest

To be determined from model specification.

## Output of Interest

Key aggregate metrics and time series as described in the research goal.

## Mode

Simulator

## Source

- **CoMSES URL**: https://www.comses.net/codebases/1dd9e993-6db0-4421-8aac-226825e65cab/
- **Contributors**: Rei England
