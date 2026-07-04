# SIR Epidemic Threshold — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claims are the standard SIR threshold + final-size
results, not tuned. Source: Kermack & McKendrick (1927); Brauer, final-size relations.

**Model (faithful, well-mixed / mass-action):** N=10,000 agents, states S/I/R. γ fixed
(recovery prob per tick, e.g. 0.1); β set so R0=β/γ takes target values. Each tick: each
S becomes I with prob 1−(1−β/N)^{I} (mass-action contact) — equivalently force of
infection βI/N; each I recovers with prob γ. Seed a few I (e.g. 10). Run to extinction of
I. Outcome = final attack rate (1−S∞/N). Average over ≥20 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Epidemic threshold at R0=1. | attack rate < 0.05 at R0=0.8 AND > 0.30 at R0=2.0 |
| P2 | Final size matches the analytic relation. | at R0=2.0, measured attack rate within ±10% of the solution of ln(S0/S∞)=R0(1−S∞/N) |
| P3 | Monotone in R0, near-zero below 1. | attack rate non-decreasing across R0 ∈ {0.8,1.0,1.5,2.0,3.0}; <0.05 at R0=0.8 |

**Discipline:** N, γ, seed count, R0 grid FIXED + the metric (attack rate) and the analytic
final-size formula locked before the run (formula from locked R0, not fit). Falsified → MISS.
