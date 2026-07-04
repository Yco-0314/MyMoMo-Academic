# Axtell Model of Firms (Zipf firm sizes) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Axtell 1999/2001 (Science 293:1818), not tuned.
Genuine agent-based. Verified; gate-checked.

**Model:** population of N agents; each has a work-vs-leisure preference. Firms are groups of agents;
output of a firm with total effort E is O = a·E + b·E² (increasing returns), shared equally among
members. Each activated agent chooses its effort AND whether to stay, join another firm, or start a new
singleton firm, to maximise its own utility (Cobb-Douglas over income share + leisure). Random
activation, run to a stationary firm-size distribution. N = 2000–100000 (larger N sharpens the tail),
run to stationarity, ≥ several seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Firm-size distribution is Zipf (power law). | rank-size log-log OLS slope ∈ [−1.5, −0.7] (wide band around Zipf −1; covers empirical −0.96…−1.04 + finite-N drift). |
| P2 | Firm-size inequality is EXTREME. | Gini of firm sizes ≥ 0.60 (empirical ≈0.89; ≥0.60 absorbs finite-N tail truncation); the size distribution is strongly right-skewed (most firms tiny, a few huge). |
| P3 | Firm log-GROWTH-RATE distribution is tent-shaped (Laplace, not Gaussian). | excess kurtosis of pooled firm log-growth rates > 1.5 (Laplace excess kurtosis = 3, Gaussian = 0) AND growth-rate std decreases with firm size (negative log-log slope of σ_growth vs size). |

**Discipline:** N, output function (a,b), utility, activation, seeds FIXED + metrics locked; no tuning.
Falsified → MISS. **Distinctness (keep):** no built model has endogenous FIRM formation or a Zipf
size distribution; sugarscape has individual wealth (not firms/groups), and its Gini is landscape-set,
not the Zipf firm-size power law + Laplace growth rates that are the Axtell/Stanley stylized facts.
