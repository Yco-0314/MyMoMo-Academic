# Bianconi-Barabási Fitness Model (fit-get-richer + condensation) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Bianconi & Barabási 2001 (PRL 86:5632), not tuned.
**Network-generation (disclosed).** Verified; gate-checked (structural/rank bars, soft exponent).

**Model:** growing network, each node i has a fixed fitness η_i drawn once from ρ(η); a new node's m
edges attach to node i with probability Π_i = η_i·k_i / Σ_j η_j·k_j (fitness-weighted preferential
attachment). m = 2. Two fitness distributions: (A) UNIFORM ρ=U[0,1] (fit-get-richer, scale-free, NO
condensation); (B) a CONDENSING distribution (a fitness law that concentrates the winner — the builder
uses the paper's condensation example, e.g. ρ(η) ∝ (1−η)^θ / a distribution whose Bose-gas mapping is
below T_c; disclose it). N = 5×10⁴ (and 10⁴ for the N-scaling check). ≥ a few seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | FIT-GET-RICHER / multiscaling (uniform ρ). | holding birth-time fixed: median(k_final \| η>0.67) / median(k_final \| η<0.33) ≥ 2.0 in ≥3 of 4 birth-time deciles; Spearman(η, final degree) ≥ 0.5. A BA rerun (no fitness) gives ratio ∈ [0.7,1.4] and \|Spearman\| < 0.15 → FAILS. |
| P2 | CONDENSATION vs no-condensation contrast (the signature). | condensing run (B): max-degree fraction f_max ≥ 0.15 at N=5e4 AND f_max(5e4) ≥ 0.7·f_max(1e4) (non-vanishing); uniform run (A): f_max ≤ 0.05 at N=5e4 AND f_max(5e4) < f_max(1e4) (shrinking); gap f_max(B) − f_max(A) ≥ 0.10. A BA rerun behaves like (A). |
| P3 | Degree exponent γ < 3 (soft, CORROBORATING). | fitted γ (uniform ρ) ∈ [1.9, 2.7] (target ≈2.255, wide band; NOT a hard gate) AND < 2.9 (distinguishable from BA's 3). |

**Discipline:** m, ρ distributions, N, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep-with-gate):** BA has no fitness — the largest-hub fraction → 0 (no condensation) and
degree is uncorrelated with any node attribute; the fitness → fit-get-richer + the Bose-Einstein
condensation phase are exactly what BA cannot show (P1 + P2 gates).
