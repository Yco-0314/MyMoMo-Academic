# Random Geometric Graph (Gilbert disk model, 2D) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Gilbert 1961 / Penrose 2003 / Dall-Christensen 2002,
not tuned. **Network-generation (disclosed).** Verified; gate-checked (robust structural bars).

**Model:** N nodes placed uniformly at random in the 2D unit square [0,1)² (hard boundary, no wrap);
connect two nodes iff Euclidean distance ≤ r. Mean degree ⟨k⟩ = N·π·r² (choose r = √(⟨k⟩/(Nπ))).
N = 1000–2000 (up to 10000). Sweep ⟨k⟩ ∈ {1,2,3,4,4.5,5,6,8,12}. ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | HIGH clustering, far above ER (geometric overlap). | at ⟨k⟩ ∈ [8,12]: clustering C ∈ [0.50, 0.62] (bulk constant 0.5865; boundary pulls it modestly down) AND C_RGG / C_ER ≥ 30 at matched N, ⟨k⟩. |
| P2 | Giant component emerges at a HIGH critical ⟨k⟩ (not ⟨k⟩=1). | largest-component fraction S(⟨k⟩=2) < 0.30 AND S(⟨k⟩=8) > 0.85 (critical ⟨k⟩≈4.51, far above ER's 1); S monotone non-decreasing across the sweep. |
| P3 | Mean-degree relation ⟨k⟩ = N·π·r². | for each swept r, measured ⟨k⟩_meas ∈ [0.85, 1.05]·(N·π·r²) (boundary loss ≤15%); correlation of ⟨k⟩_meas vs N·π·r² across the sweep > 0.99. |

**Discipline:** N, r/⟨k⟩ grid, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep-with-gate):** ER G(n,p) at the same ⟨k⟩ has C ≈ ⟨k⟩/N ≈ 0.01 (RGG is ~30–50×
higher) and its giant component appears at ⟨k⟩=1 (RGG at ≈4.51); the spatial embedding + distance-based
connection is absent from ER/WS/BA and the built config-model.
