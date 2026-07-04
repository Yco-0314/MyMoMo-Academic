# CODA (Continuous Opinions, Discrete Actions) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Martins 2008 (arXiv:0711.1199v2; IJMPC
19(4):617), not tuned. Genuine agent-based (each agent carries a continuous hidden belief,
exposes only a discrete action). Verified against the original text.

**Model:** L×L square lattice (L=50, N=2500), PERIODIC boundary, von Neumann neighbourhood
(4 neighbours). Each agent holds a continuous probability `p` that A is best and exposes only
a binary action σ = sign(p − 0.5) = ±1. In log-odds `l = ln(p/(1−p))` the Bayesian update is
EXACTLY ADDITIVE (Martins Eq. 3): on observing a neighbour's action, `l → l ± ν`, with the
fixed step `ν = ln(α/(1−α))` and likelihood α = 0.7 ⇒ ν = 0.8473; `+` when the observed
neighbour acts for A (σ_j = +1), `−` for B. Asynchronous updates: each step a random agent
observes one random neighbour. Initial `p_i ~ U(0.4, 0.6)` so NO agent starts extremist
(all |l_i| < ν). ≥3 seeds.

**Methodology (locked, derived from the claim — not tuned):** extremization is asymptotic, so
the run MUST be long — ≥ 2×10⁶ updates (≈ 800 sweeps of N), and P1 is checked for *continued
growth* by doubling to 4×10⁶. (Reporting a plateau from a too-short run would be a false MISS.)

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Opinions extremize WITHOUT bound. | starting with no extremists, `max_i |l_i|/ν ≥ 100` at t=2×10⁶ updates AND still strictly growing (≥1.3× larger when the run is doubled to 4×10⁶). A bounded-confidence-style artifact would plateau → MISS. |
| P2 | Final opinion distribution is bimodal, extremist-dominated. | the histogram of `l/ν` is U-shaped: the fraction of agents with `|l|/ν ≥ 50` exceeds the fraction with `|l|/ν < 1` by the end of the run. |
| P3 | Agreeing agents form contiguous same-action domains. | number of connected same-action clusters ≤ 0.1·N once domains are established (far fewer than the ~random-start count). |

**Discipline:** L, α (hence ν), neighbourhood, init band, update rule, run length, seeds FIXED
+ metrics locked; no tuning. Falsified → MISS. Nearest built: deffuant/HK (continuous opinions
that AVERAGE toward moderation) — CODA inverts this (discrete-action Bayesian updating DIVERGES
to certainty), which the bounded-confidence models cannot show.
