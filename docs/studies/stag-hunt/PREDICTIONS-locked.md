# Stag Hunt Coordination Game — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is the stag-hunt coordination game (Skyrms 2004;
Maynard Smith), not tuned. Genuine agent-based. Verified.

**Model:** symmetric 2-player stag hunt: Stag=S, Hare=H. Payoffs R (S,S), S_ (S vs H), T (H vs S),
P (H,H) with **R>T>P>S_** — both (S,S) [payoff-dominant] and (H,H) [risk-dominant] are strict pure
ESS, with an unstable interior fixed point x* = (P−S_)/((R−T)+(P−S_)) (fraction of Stag). Replicator
/ imitation dynamics in a large well-mixed population (N≥1000). Canonical payoffs (R,T,P,S_)=(4,3,2,0)
⇒ x*=0.667; also (R,T,P,S_) giving x*∈{0.500, 0.200}. ≥500 replicates with x0~U(0,1) for the basin.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Bistable basin threshold at the predicted interior fixed point. | empirical x*_emp ∈ [0.62, 0.72] (canonical 0.667); P(all-Stag) ≤ 0.05 for x0=0.5 and ≥ 0.95 for x0 well above x*. |
| P2 | Risk-dominant (Hare) equilibrium has the strictly larger basin. | over ≥500 replicates x0~U(0,1): P(fixate Hare) = 0.667 ± 0.05 AND strictly > P(fixate Stag). |
| P3 | The threshold TRACKS the payoff formula (not a fixed 50/50). | x*_emp matches the predicted x* within ±0.05 for three parameter sets giving {0.667, 0.500, 0.200}. |

**Discipline:** payoff sets, N, replicate count, update rule FIXED + metrics locked; no tuning.
Falsified → MISS. **Distinctness (keep):** hawk_dove has a single stable interior MIXED ESS
(p*=V/C, C and D coexist); the stag hunt is BISTABLE with two pure ESS and basin-of-attraction
selection — a hawk_dove rerun converges to its interior mix, never to all-Stag/all-Hare fixation.
