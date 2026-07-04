# Minority Game — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Challet & Zhang (1997), not tuned. Genuine
agent-based (adaptive strategy agents).

**Model:** N=301 agents (odd). Each holds S=2 strategies = random lookup tables from the
m-bit history of the winning side → action (0/1). Each round: each agent plays the action of
its currently best-scoring strategy; the MINORITY side wins; every strategy's score is
updated by whether it predicted the minority (virtual points). Control α=2^m/N (sweep m at
fixed N). Outcome = volatility σ²/N = Var(attendance on one side)/N over a long run after
transient. Mean over ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | σ²/N is U-shaped/asymmetric with a minimum near αc≈0.34. | argmin of σ²/N over the α sweep falls in α∈[0.1,0.6] |
| P2 | Small α: worse than random (crowding/herding). | σ²/N > 1 at the smallest α (≤0.1) |
| P3 | Large α: random-like. | σ²/N ∈ [0.7,1.5] at the largest α (≥2) |

**Discipline:** N, S, m-grid (→α), run length, seeds FIXED + metric (σ²/N) locked before run;
no tuning. Falsified → MISS. (random benchmark σ²/N=1 for coin-flipping agents.)
