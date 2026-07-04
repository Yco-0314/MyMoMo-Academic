# Coevolving-Network Prisoner's Dilemma (Santos-Pacheco-Lenaerts 2006) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Santos, Pacheco & Lenaerts 2006 (PLoS Comput Biol
2:e140), not tuned. **Network-generation + adaptive rewiring (disclosed).** Verified; gate-checked.

**Model:** N=10³ agents on a HOMOGENEOUS random graph, every node degree z (baseline z=30), average
degree + edge count CONSERVED. One-shot PD vs all neighbours, payoffs R=1, P=0, T∈(1,2], S∈[−1,0]
(hard point T=2, S=−1 ⇒ b/c=2), selection β=0.005. Two entangled dynamics at timescale ratio W: each
elementary step is a STRATEGY update w.p. 1/(1+W) (A copies a better neighbour B via the Fermi rule)
else a STRUCTURAL update (a dissatisfied agent rewires the tie away from a defector toward a new node).
W=0 = static graph. Steady-state cooperator fraction, ≥20 realizations.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Static network collapses (baseline). | W=0, z=30, T=2, S=−1: final cooperator fraction < 0.05 (near 0; the static homogeneous graph cannot sustain cooperation at b/c=2). |
| P2 | Coevolution prevails + dramatic enhancement. | W ≥ 16 (well above W_crit~4): final cooperator fraction > 0.80 AND (fraction at W≥16) − (fraction at W=0) > 0.6. |
| P3 | Monotone W-dependence with a threshold. | cooperator fraction is (weakly) non-decreasing in W and jumps from low to high: fraction(W=16) − fraction(W=0.5) > 0.5, with fraction(W=0.5) < 0.2 and fraction(W=16) > 0.7. (No bar demands a specific W_crit value.) |

**Discipline:** N, z, T/S, β, W grid, realizations FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** nowak_may_pd is a STATIC lattice with deterministic best-takes-over and fixed
topology — the whole novelty here is the COEVOLVING topology (rewiring away from defectors), which the
static-lattice model has no representation of; the W=0 arm is exactly the "no enhancement" control.
