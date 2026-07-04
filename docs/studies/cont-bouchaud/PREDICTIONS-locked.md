# Cont-Bouchaud Percolation Market — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Cont & Bouchaud 2000 (Macroecon Dyn 4:170), not
tuned. **Network-generation (percolation) + trading (disclosed).** Verified; gate-checked.

**Model:** N agents on an Erdős-Rényi random graph with connection probability p = c/N; connected
clusters act as single traders. Each step, each cluster is active with probability a and, if active,
all its members buy (+1) or sell (−1) together (fair coin); the aggregate return r = Σ over active
clusters of (±cluster size). Operate at the percolation threshold c = 1 with small activity a. N large
(≥1e4). Standardize returns (subtract mean, divide by std). ≥ many steps + seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Fat-tailed (non-Gaussian) returns at criticality. | at c=1, a ≤ 0.1: excess kurtosis of standardized returns > 3 AND > 5× a near-Gaussian control (large a / well-below-threshold). |
| P2 | Heavy tails relative to Gaussian. | P(\|r\| > 3σ) ≥ 0.008 (≥3× Gaussian's 0.0027) AND P(\|r\| > 5σ) ≥ 10× Gaussian; any fitted tail exponent ∈ [1.5, 4]. |
| P3 | Activity-driven crossover to Gaussian. | excess kurtosis(a≈0.05) ≥ 3× excess kurtosis(a≈0.49); monotone decrease of kurtosis across the a-sweep (herding → Gaussian as activity rises). |

**Discipline:** N, c, a grid, steps, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** the power-law cluster-size distribution at the percolation threshold, aggregated
into returns, produces the fat-tailed / excess-kurtosis stylized fact of real markets — a mechanism
absent from the built ER (structure only), ZI-traders (efficiency), and minority-game (attendance);
here the ER percolation clustering IS the market's fat tail.
