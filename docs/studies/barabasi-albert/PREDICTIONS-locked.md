# Barabási–Albert Preferential Attachment — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Barabási & Albert (1999), not tuned.
Mildly agent-based (arriving NodeAgents choose attachments ∝ degree).

**Model:** small connected seed; each tick a new node arrives with m edges, each attached
to an existing node with probability ∝ its current degree. Grow to N=10,000. Outcome =
degree distribution; tail exponent γ from a fit (MLE or log-log CCDF slope). Mean over ≥5
seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Power-law tail with γ≈3 (m=3). | fitted γ ∈ [2.7, 3.3] |
| P2 | γ is ~independent of m. | γ(m=1), γ(m=3), γ(m=5) all ∈ [2.5, 3.5] |
| P3 | Heavy-tailed vs ER (hubs). | BA max degree ≫ ER max degree at equal mean degree (ratio ≥ 3×) |

**Discipline:** N, m grid, seed count, the exponent-fit method FIXED before run; no tuning
of the fit to hit 3. Falsified → MISS.
