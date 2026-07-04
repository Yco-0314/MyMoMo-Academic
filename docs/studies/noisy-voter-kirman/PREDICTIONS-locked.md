# Noisy Voter / Kirman Model - PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is the complete-graph noisy
voter/Kirman process with spontaneous flips plus voter copying, not tuned after results.

**Model:** N binary agents. One update picks a target. With probability a the target
flips spontaneously. Otherwise it copies a random other agent. Unlike the absorbing
voter model, a > 0 removes absorbing states and yields a stationary magnetization
distribution.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Weak noise produces herding / edge-heavy stationary mass. | For a*N < 1, stationary trace has more mass at \|m\| > 0.6 than at \|m\| < 0.2. |
| P2 | Strong noise produces centred / unimodal stationary mass. | For a*N > 1, stationary trace has more mass at \|m\| < 0.2 than at \|m\| > 0.6 and \|mean m\| <= 0.15. |
| P3 | Crossover scales approximately with a*N. | Matched a*N runs at N=100 and N=400 have edge-vs-centre mass ratios within a broad tolerance of 0.35. |

**Discipline:** N, a values, burn-in, sample count, record interval, and metrics fixed
before run; no tuning. Falsified -> MISS.
