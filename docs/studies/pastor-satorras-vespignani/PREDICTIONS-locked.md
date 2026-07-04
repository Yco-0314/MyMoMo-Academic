# Pastor-Satorras-Vespignani — SIS on Scale-Free Networks — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Pastor-Satorras & Vespignani 2001 (PRL 86, 3200),
not tuned. **Hybrid (network generation + SIS agent dynamics on it) — disclosed.** Verified.

**Model:** SIS dynamics (per S→I-link infection rate λ, recovery rate 1; control λ = infection/
recovery) on a network. Heterogeneous mean-field epidemic threshold λ_c = ⟨k⟩/⟨k²⟩. On scale-free
networks (BA, γ≈3) ⟨k²⟩ diverges with N, so λ_c → 0 (NO epidemic threshold); on homogeneous
networks λ_c is finite (≈ 1/⟨k⟩). Generate BA (m=3) and a homogeneous control (ER/WS, same ⟨k⟩) at
N ∈ {1e3, 1e5}. Measure the metastable prevalence ρ(λ). ≥ several realizations + seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Vanishing threshold on BA. | estimated SIS threshold λ_c(N=1e5) ≤ (1/3)·λ_c(N=1e3) on BA AND ρ_BA(λ=0.05, N≥1e5) > 0.005 (well below 1/⟨k⟩=0.167) — i.e. a finite endemic prevalence at a λ far under the homogeneous threshold. |
| P2 | Homogeneous control keeps a FINITE threshold (discriminating). | on the ER/WS control (same ⟨k⟩), fitted λ_c ∈ [0.125, 0.21] (≈1/⟨k⟩ ±25%); ρ_homog(0.05) < 0.002 AND ρ_BA(0.05)/ρ_homog(0.05) ≥ 5. |
| P3 | Stretched-exponential prevalence on BA. | for BA (m=3) at small λ, ln ρ vs 1/λ is linear; fit ρ = A·exp(−C/λ) over λ ∈ [0.04, 0.12] gives C ∈ [0.20, 0.47] (≈ 1/m = 0.333 ±40%), R² > 0.95. |

**Discipline:** network families, N grid, λ grid, realization count FIXED + metrics (λ_c scaling,
prevalence ratio, stretched-exp fit) locked; no tuning. Falsified → MISS. **Distinctness
(keep-with-gate):** nearest built are sis-endemic (well-mixed/homogeneous, finite threshold) and
barabasi-albert (structure only). The VANISHING threshold on scale-free networks (λ_c → 0) is the
emergent property neither shows alone — the well-mixed SIS has a finite threshold; the BA generator
has no epidemic dynamics. The contrast (finite λ_c on ER vs → 0 on BA) is the gate.
