# Bak-Sneppen (SOC) — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Bak & Sneppen (1993), not tuned.
**Extremal dynamics (global-min selection) — model-orchestrated, NOT autonomous-agent-stepping**
(disclosed in FINDINGS).

**Model:** ring of N=200 species, each fitness ~U[0,1]. Each step: find the GLOBAL minimum
fitness; replace it + its two ring-neighbours with fresh U[0,1]. Run long (≥10⁶ steps); discard
transient. Outcome = stationary fitness distribution + avalanche sizes (consecutive steps with
the min below a threshold).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Self-organizes to a critical threshold f_c≈0.667. | the stationary distribution's lower cutoff (fitnesses become ~uniform above it) measured in [0.60, 0.72] |
| P2 | Power-law avalanches (SOC). | avalanche-size distribution heavy-tailed, ≥2 decades |
| P3 | Punctuated equilibrium. | activity is intermittent — the running minimum repeatedly dips below and recovers above f_c |

**Discipline:** N, run length, transient, avalanche-threshold FIXED + metric locked; no tuning
toward 0.667. Falsified → MISS.
