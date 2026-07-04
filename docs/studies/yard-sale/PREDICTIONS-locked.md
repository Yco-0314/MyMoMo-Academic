# Yard-Sale Model of Wealth Exchange — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Chakraborti 2002 / Hayes 2002 / Boghosian 2014, not
tuned. Genuine agent-based. Verified; gate-checked.

**Model:** N agents, wealth w_i ≥ 0, total conserved. Each transaction: pick two agents; the amount at
stake Δ = β · min(w_i, w_j) (a fraction β of the POORER agent's wealth); a fair coin decides who wins Δ.
No redistribution. Start from equal wealth. N ∈ [500, 1000], β ∈ [0.1, 0.2], ≥2×10⁴ sweeps (2e4·N
transactions), ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | CONDENSATION to extreme inequality. | final Gini ≥ 0.95 (N∈[500,1000], β∈[0.1,0.2], ≥2e4 sweeps) AND the Gini(t) trajectory is non-decreasing (monotone climb toward 1). |
| P2 | OLIGARCHY / single winner. | the top-1 agent holds ≥ 0.90 of total wealth at run end AND the bottom 50% of agents jointly hold ≤ 0.01. |
| P3 | DISTINCT from the exponential (Dragulescu-Yakovenko) fixed point. | final Gini ≥ 0.7 — well above the exponential's 0.5 — so the exponential hypothesis is falsified by inequality level alone (same conserved-exchange family, opposite outcome: condensation, not thermalization). |

**Discipline:** N, β, sweeps, seeds FIXED + metrics locked; no tuning. Falsified → MISS. **Distinctness
(keep-with-gate):** same conserved pairwise-exchange FAMILY as Dragulescu-Yakovenko but the
stake-the-poorer rule has an UNSTABLE fixed point at equality → wealth condenses onto one agent
(Gini→1), the OPPOSITE of DY's exponential (Gini=0.5). Neither built model (sugarscape/ZI) has this
multiplicative winner-take-all dynamic. The Gini≥0.7 gate (vs DY's 0.5) is the discriminator.
