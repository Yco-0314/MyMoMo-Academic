# Pastor-Satorras-Vespignani SIS on scale-free — adversarial review

**tier: deep** (trigger: 1 honest MISS). Reviewed against the verified canonical claim + the
committed lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (BA λ_c 0.074→0.061 ratio 0.825, ρ_BA/ρ_ER 243×, C=0.316 R²=0.988) matches the bundle/results.
- fair-control: **pass** — BA vs ER differ ONLY in the degree distribution at the SAME ⟨k⟩ (single variable); the 243× prevalence contrast is a fair A/B.
- no-post-lock-drift: **pass** — graded verbatim against the committed lock; L3 integrity gate ok, FINDINGS fingerprinted.
- mechanism-aliveness: **pass** — the load-bearing mechanism is vividly alive: BA ⟨k²⟩ grows 88.9→144.7 (ER stays 42.0), so λ_c=⟨k⟩/⟨k²⟩ shrinks on BA but stays finite on ER. P1 fails on its numeric BAR, not on a dead mechanism (P2/P3 confirm the physics).
- framing-disclosure: **pass** — hybrid (network generation + SIS dynamics), disclosed; a faithful platform one-agent-per-node path is asserted to agree with the vectorised CSR path.

## Verdict: model FAITHFUL; P1 is an HONEST MISS (optimistic bar, NOT a bug or dead mechanism).
- **P1 MISS.** λ_c(1e5)/λ_c(1e3) = 0.825 (needed ≤ 1/3) AND ρ_BA(0.05, N=1e5) = 0.00328 (needed > 0.005).
  A ⅓ threshold-collapse over two N-decades needs ⟨k²⟩ to triple (N ≳ 1e7–1e8, out of reach); ρ=0.00328
  at λ=0.05 is physically correct (dead-centre on the PSV stretched-exp asymptote, confirmed dt-invariant
  and stable under longer runs — NOT a low-biased sampler). Builder did not tune bars/λ; a mid-task helper
  consultation only CORROBORATED the physics and was correctly treated as evidence, not permission.
- **P2 REPRO** (ER finite λ_c=0.153 ∈ [0.125,0.21]; ρ_BA/ρ_ER = 243× ≥ 5) and **P3 REPRO**
  (stretched-exp C=0.316 ≈ 1/m, R²=0.988) — these carry the distinct PSV signature.

## Discipline check: PASS. Distinctness confirmed.
2/3 REPRO reported honestly; no tuning. The vanishing-threshold-on-scale-free physics is REPRO via the
finite-vs-shrinking λ_c contrast (P2) + the stretched-exponential prevalence (P3) — properties neither the
built well-mixed SIS (finite threshold) nor the BA generator shows alone. Same gate-design lesson as
q-voter / social-impact: P1's exact numeric bar was optimistic for the accessible finite-N regime.

REVIEW COMPLETE
