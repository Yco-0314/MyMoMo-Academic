# Holme-Kim Growing Scale-Free with Tunable Clustering — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Holme & Kim 2002 (Phys Rev E 65:026107), not tuned.
**Network-generation (disclosed).** Verified; gate-checked.

**Model:** BA preferential attachment PLUS a triad-formation step: after each new node makes a
preferential-attachment edge, with probability p it also links to a random NEIGHBOUR of the just-chosen
node (closing a triangle); repeated for the m edges. m = 3, N ∈ [2000, 10000]. Sweep p ∈ {0.0, 0.15,
0.45, 1.0}. ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Clustering is TUNABLE by p, far above BA. | C(p=1.0) ≥ 0.40 AND C(p=1.0)/C(p=0) ≥ 5 AND monotone C(p=0) < C(p=0.45) < C(p=1.0). |
| P2 | Scale-free structure PRESERVED, exponent independent of clustering. | γ_fit(p=0) and γ_fit(p=1) both ∈ [2.0, 3.5] (both ≈2.6) AND \|γ_fit(p=0) − γ_fit(p=1)\| ≤ 0.4. |
| P3 | Small-world preserved (short, log-growing path length). | L(N=1000) ∈ [3,4] and L(N=5000) ∈ [3.5,5] for p ∈ {0,1}, with L(N=5000) − L(N=1000) ≤ ~1. |

**Discipline:** m, N, p grid, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep-with-gate):** built BA has vanishing clustering (C ~ (ln N)²/N → 0) and no tunable
knob; Holme-Kim adds the triad step so C is dialed by p while the BA γ≈3 tail + small-world path length
are preserved — a combination BA cannot produce.
