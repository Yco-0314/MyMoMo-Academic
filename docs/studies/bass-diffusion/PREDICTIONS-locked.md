# Bass 1969 Diffusion — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claims are Bass (1969) + the standard analytic
peak-time result, not tuned. Source: Mgmt Sci 15(5):215–227.

**Model (faithful, agent-based):** N agents (10,000), all initially non-adopters. Each
tick, every non-adopter adopts with probability p + q·F(t), where F(t) = current adopter
fraction, p = coefficient of innovation, q = coefficient of imitation. Adoption is
irreversible. Defaults p=0.03, q=0.38 (meta-analytic). Outcome = cumulative adoption curve
+ per-tick adoption rate; average over seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Cumulative adoption is S-shaped and reaches near-full adoption. | final cumulative ≥ 0.98 AND curve sigmoid (monotone, inflection interior) |
| P2 | Peak adoption RATE occurs near the analytic t* = ln(q/p)/(p+q). | measured peak tick within ±15% of t* |
| P3 | q>p ⇒ interior (bell) peak; pure innovation (q=0) ⇒ rate monotonically decreasing (no interior peak). | argmax(rate)>0 for (p=.03,q=.38); argmax(rate)=0 for q=0 |

**Discipline:** p, q, N, seed-count fixed before run. t* computed from the locked p,q
(not fit to the run). A falsified clause → MISS.
