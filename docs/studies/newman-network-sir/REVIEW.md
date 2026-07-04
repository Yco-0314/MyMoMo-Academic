# Newman 2002 SIR-on-networks (bond percolation) — review

**tier: minimal** (all-REPRO 3/3, comfortable margins; no MISS, no load-bearing dead-mechanism
risk). Reviewed against the verified canonical claim + committed lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (T_c(hom)=0.251, susc-peak 0.260, SF 0.0375, GF dev 0.0014) matches the bundle/results.
- fair-control: **pass** — homogeneous vs power-law graphs differ only in the degree distribution at matched ⟨k⟩ (P2's single-variable contrast).
- no-post-lock-drift: **pass** — graded verbatim against the committed lock; validate_repro_bundle ok (3 doc fingerprints incl. FINDINGS, 0 failed).
- mechanism-aliveness: **pass** — the ⟨k²⟩-driven threshold shift is real (SF ⟨k²⟩ ~123 vs hom ~20 → T_c collapses 6.7×); the GF final-size solver matches simulation to 0.0014.
- framing-disclosure: **pass** — network-generation + bond-percolation isomorphism disclosed in docstring/run/FINDINGS/bundle.extra.

## Verdict: SOUND. 3/3 REPRO, closed-form + GF exact.
Faithful configuration-model stub-matching + union-find percolation + generating-function final size.
P1 empirical T_c matches ⟨k⟩/(⟨k²⟩−⟨k⟩) from the REALIZED degree sequence (Δ≤0.03); P2 heterogeneity
collapses the threshold 6.7×; P3 GF S=1−g₀(1−T+Tu) matches sim to 0.0014. Disclosed structural choice
(power-law kmin=2, kmax=500 so ⟨k⟩ matches the homogeneous ⟨k⟩≈4) is fixed pre-run and does not touch
the graded T_c (computed from realized moments) — sound, not tuning. 23 tests; ~14s run (efficient).
Distinctness: the network T_c and its heterogeneity collapse are structural properties neither the built
well-mixed SIR nor the BA generator shows alone.

REVIEW COMPLETE
