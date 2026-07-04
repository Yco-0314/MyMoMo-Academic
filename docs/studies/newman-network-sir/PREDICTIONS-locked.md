# Newman 2002 — SIR on Networks (bond percolation) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Newman 2002 (Phys. Rev. E 66, 016128), not tuned.
**Network-generation + bond-percolation mapping (disclosed: configuration-model graph generation +
percolation, not autonomous agent-stepping).** Verified.

**Model:** SIR on a configuration-model network with degree distribution p_k is exactly isomorphic
to BOND PERCOLATION where each edge is occupied with probability T (the transmissibility). Generate
configuration-model graphs (N≥1e4) for: a homogeneous degree (≈ Poisson/regular, ⟨k⟩≈4) and a
power-law p_k ∝ k^(−γ) (γ≈2.5, same ⟨k⟩). Run bond percolation at occupation T (= SIR with
transmissibility T); the giant percolating cluster = the epidemic. ≥50 graph realizations.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Threshold matches the degree-moment closed form. | empirical T_c (giant-cluster onset) agrees with T_c = ⟨k⟩/(⟨k²⟩−⟨k⟩) computed from the realized degree sequence to within ±0.03 (or ±15% relative). |
| P2 | Degree heterogeneity LOWERS the threshold (discriminating). | at FIXED mean degree, T_c(power-law γ≈2.5) < 0.5 × T_c(homogeneous): concretely T_c(homog) ≈ 0.25 while T_c(scale-free) < 0.10. |
| P3 | Generating-function final-size curve matches simulation. | above threshold, measured giant-outbreak fraction S within ±0.05 of the self-consistent generating-function S at each T ∈ {0.3, 0.4, 0.6} on the homogeneous graph; below T_c, no giant outbreak (largest component o(N)). |

**Discipline:** degree distributions, N, T grid, realization count FIXED + metrics (T_c formula, GF
final size) locked; no tuning. Falsified → MISS. **Distinctness (keep-with-gate):** nearest built
are sir-threshold (well-mixed R0) and barabasi-albert (structure only). The network T_c =
⟨k⟩/(⟨k²⟩−⟨k⟩) and its heterogeneity-driven collapse are a structural property neither shows alone
— a well-mixed SIR rerun has no degree moments; the BA generator has no epidemic dynamics.
