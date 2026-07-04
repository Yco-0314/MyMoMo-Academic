# Bouchaud-Mézard Wealth Condensation — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Bouchaud & Mézard 2000 (Physica A 282:536), not
tuned. Genuine agent-based (mean-field). Verified; gate-checked.

**Model:** N agents, wealth W_i evolves by dW_i = W_i·dη_i (multiplicative Gaussian noise, variance
σ²) + (J/N)·Σ_j(W_j − W_i) dt (all-to-all exchange/redistribution at rate J). Fully connected
mean-field. Stationary normalized-wealth distribution is a Pareto power law P(W) ~ W^(−1−μ) with
μ = 1 + J/σ². Integrate (Euler-Maruyama, small dt) to stationarity; N ≈ 3000; sweep J/σ² so μ ∈
{1.4, 2, 3, 5}. ≥ several seeds, time-average.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Inequality DECREASES monotonically with redistribution J (larger μ → less inequality). | Gini(μ=2) ∈ [0.45, 0.55]; Gini(μ=3) ∈ [0.33, 0.42]; Gini(μ=5) ∈ [0.22, 0.32]; strict monotone decrease across μ = 1.4 > 2 > 3 > 5. |
| P2 | Stationary tail is a genuine POWER LAW (not exponential). | CCDF top-decile log-log slope ∈ [−2.5, −1.5] at μ=2 (exponent NOT point-locked); 99.9th-percentile/mean ≥ 12 AND max/mean ≥ 25 (heavy tail); power-law beats exponential on the top decile (AIC). |
| P3 | Tail exponent tracks μ = 1 + J/σ² in ORDERING (soft). | estimated μ̂ at the operating point (true μ=2) ∈ [1.5, 2.6] AND μ̂ increases monotonically across the J-sweep. No tight point-estimate is required. |

**Discipline:** N, σ², J grid, dt, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** unlike Dragulescu-Yakovenko (conserved exchange → EXPONENTIAL, Gini 0.5),
Bouchaud-Mézard adds MULTIPLICATIVE growth so the tail is a POWER LAW with a redistribution-tunable
exponent μ=1+J/σ²; no built model has multiplicative wealth dynamics or a Pareto tail.
