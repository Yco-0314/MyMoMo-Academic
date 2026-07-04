# Dragulescu-Yakovenko Statistical Mechanics of Money — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Dragulescu & Yakovenko 2000 (Eur Phys J B 17:723),
not tuned. Genuine agent-based. Verified; gate-checked.

**Model:** N agents each hold money m_i ≥ 0, total M conserved. Repeatedly pick a random pair (i,j),
pool s = m_i+m_j, draw ε~U[0,1], set m_i = ε·s, m_j = (1−ε)·s — the full-repartition (no-saving)
rule — with a hard NO-DEBT boundary (reject any transaction driving a balance < 0). Start from a
delta (all agents = M/N). N ∈ [1000, 5000], ⟨m⟩ = T = M/N (e.g. 100). Run ≥ 2000–5000 sweeps, discard
~50% burn-in, time+seed-average P(m) over ≥20 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Stationary distribution is EXPONENTIAL (Boltzmann-Gibbs), not peaked, not power-law. | log-linear OLS of ln P(m) vs m over m ∈ [0.2⟨m⟩, 3⟨m⟩] has R² ≥ 0.95 and fitted decay slope 1/T within ±25% of 1/⟨m⟩; the mode is in the lowest ~10% money bin; exponential AIC < power-law AIC over the bulk. **FAIL if interior-peaked (mode > 0.3⟨m⟩ = the saving-propensity Gamma signature).** |
| P2 | Inequality matches the exponential fixed point. | seed-averaged stationary Gini = 0.50 ± 0.03 AND coefficient of variation CV = std(m)/⟨m⟩ = 1.0 ± 0.1. FAIL if Gini ≤ 0.45 (over-equalized / saving-propensity) or ≥ 0.58. |
| P3 | Money conserved; temperature = mean (consistency check). | \|M(t)−M(0)\|/M(0) < 1e-9 for all t; min(m_i) ≥ 0 always; fitted T within 10% of ⟨m⟩=M/N. |

**Discipline:** N, ⟨m⟩, rule, no-debt, burn-in, seeds FIXED + metrics locked; no tuning. Do NOT add a
saving propensity λ>0 (turns it into a peaked Gamma → must FAIL). Falsified → MISS. **Distinctness
(keep):** sugarscape has spatial harvesting + non-conserved sugar + a landscape-set Gini (not pinned to
0.5, no thermal/entropy signature); ZI measures allocative efficiency (no wealth dynamics). The
conserved kinetic exchange → universal exponential (Gini exactly 0.5) is unique here.
