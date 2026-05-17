# Story: Eco-Innovation Diffusion Through Firm Networks

## Research Motivation

Ramkumar et al. (2022, Journal of Cleaner Production) studied how targeting strategies in inter-firm networks affect eco-innovation adoption. Firms decide whether to adopt green technologies based on economic incentives, peer influence, and policy interventions.

## Research Goal

Simulate firms deciding whether to adopt eco-innovation. Study how adoption subsidies, peer influence strength, and initial seed placement affect diffusion speed and final adoption rate.

## Agent Description

Each agent represents a firm with:
- `adopted`: boolean (0 = conventional, 1 = eco-innovator)
- `adoption_threshold`: willingness to adopt (uniform random 0.3-0.8)
- `profit`: current profit level (float, starts at 50)

## Spatial Structure

Grid of 20x20 (400 firms). Toroidal. Each firm interacts with 4 neighbors (von Neumann).

## Dynamics

Each time step (200 periods):
1. For each non-adopter:
   a. Calculate `peer_pressure` = fraction of adopted neighbors
   b. Adoption utility = `peer_influence * peer_pressure + subsidy - adoption_cost`
   c. If utility > `adoption_threshold`: adopt
2. Adopted firms gain `green_premium` bonus to profit each period
3. Non-adopters slowly decrease threshold by 0.01 per period (resistance decay)
4. Track: adoption fraction, average profit by type

## Parameters of Interest

- `peer_influence`: Strength of neighbor influence (range 0.1-1.0, default 0.5)
- `adoption_cost`: One-time switching cost (range 5-30, default 15)
- `subsidy`: Government subsidy for adoption (range 0-20, default 5)
- `initial_adopters`: Seed adopters (range 1-20, default 5)

## Output of Interest

- Cumulative adoption fraction over time
- Average profit of adopters vs. non-adopters
- Time to 50% adoption
- Spatial clustering of adopters

## Mode

Simulator (no calibration needed)

## Source

Ramkumar et al. (2022). J. Cleaner Production 335. CoMSES: https://www.comses.net/codebases/735e8443-f678-4dd3-a19a-adf41844bbcf/
