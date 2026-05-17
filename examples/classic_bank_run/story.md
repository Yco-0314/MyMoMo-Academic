# Story: Bank Run Model

## Research Motivation

Diamond and Dybvig (1983) showed that bank runs can be self-fulfilling prophecies: if enough depositors believe others will withdraw, it becomes rational for everyone to withdraw, causing the bank to fail even if it is fundamentally solvent. This agent-based version models the contagion of panic through local social networks.

## Research Goal

Simulate a population of bank depositors who observe their neighbors' withdrawal decisions and may panic-withdraw based on local information cascades. Study the conditions under which bank runs emerge versus deposit stability, and how the bank's reserve ratio and depositor patience affect systemic risk.

## Agent Description

Each agent represents a bank depositor with:
- `state`: integer (0 = patient/holding, 1 = withdrawn, 2 = panic-withdrawn)
- `patience`: personal panic threshold — fraction of neighbors withdrawing before panic (uniform random in [0.2, 0.8])
- `wealth`: deposit amount (uniform random in [50, 200])

## Spatial Structure

Grid of 15x15 (225 depositors). Toroidal. Each agent observes 8 neighbors (Moore neighborhood).

## Dynamics

**Initialization**: A small number of agents (`initial_withdrawers`) are set to state=1 (genuine liquidity need).

Each time step (100 periods):
1. For each patient agent (state=0):
   a. Count fraction of neighbors who have withdrawn (state=1 or 2)
   b. If fraction_withdrawn > `patience`: panic and withdraw (state=2)
2. Bank tracks total withdrawals vs. reserves
3. If total withdrawals > `reserve_ratio * total_deposits`: bank becomes insolvent
4. Environment records: fraction withdrawn, bank solvency status, total panic events

## Parameters of Interest

- `reserve_ratio`: Bank's liquid reserve as fraction of deposits (range 0.05-0.5, default 0.1)
- `initial_withdrawers`: Seed withdrawals triggering potential cascade (range 1-20, default 5)
- `mean_patience`: Average patience threshold (range 0.2-0.7, default 0.4)

## Output of Interest

- Fraction of depositors withdrawn over time
- Bank solvency indicator (solvent/insolvent)
- Time to insolvency (if occurs)
- Total panic withdrawals vs. genuine withdrawals
- Spatial spread pattern of panic

## Mode

Simulator (no calibration needed)

## Source

Diamond, D.W. & Dybvig, P.H. (1983). "Bank Runs, Deposit Insurance, and Liquidity." Journal of Political Economy, 91(3), 401-419.
