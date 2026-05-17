# Story: Modern Wage Dynamics

## Research Motivation

The Modern Wage Dynamics Model (Applegate, CoMSES peer-reviewed) explores how coupled economic production and allocation systems generate wage and employment dynamics. A single firm interacts with heterogeneous households through labor and goods markets, allowing study of minimum wage, tax credits, and universal income policies.

## Research Goal

Simulate a labor market with one firm and many households. The firm sets wages and prices; households choose work hours based on utility for leisure vs. consumption. Study how policy interventions affect employment, wages, output, and inequality.

## Agent Description

Each agent represents a household with:
- `hours_worked`: float (0-40), hours of labor supplied per period
- `consumption`: float, goods consumed per period
- `income`: float, wage * hours_worked + transfers
- `utility_leisure`: personal preference weight for leisure (uniform random 0.3-0.7)
- `employed`: boolean (1 if hours_worked > 0)

## Spatial Structure

Grid of 10x10 (100 households). Spatial structure is for bookkeeping; economic interactions are global.

## Dynamics

Each time step (200 periods):
1. Environment (firm) sets `wage` and `price` based on previous period demand
2. Each household chooses `hours_worked` based on utility maximization: higher wage -> more hours, but leisure preference varies
3. Labor market: actual hours = min(firm demand, aggregate supply)
4. Production: output = `productivity` * total_hours
5. Goods market: households spend income, market clears
6. Track: average wage, employment rate, output, Gini of income

## Parameters of Interest

- `productivity`: Output per labor hour (range 1.0-5.0, default 2.0)
- `minimum_wage`: Floor on wage (range 0-20, default 0)
- `transfer_amount`: Universal transfer per period (range 0-10, default 0)
- `num_households`: Worker count (default 100)

## Output of Interest

- Average wage over time
- Employment rate over time
- Total output over time
- Income Gini coefficient over time
- Average consumption over time

## Mode

Simulator (no calibration needed)

## Source

Applegate, J.M. CoMSES (peer-reviewed): https://www.comses.net/codebases/76a4fad5-d7ac-423d-9025-27f921a1283c/
