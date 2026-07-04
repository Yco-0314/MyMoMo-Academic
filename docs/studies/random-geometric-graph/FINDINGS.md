# Random Geometric Graph (Gilbert disk model, 2D) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Faithful network-GENERATION reproduction
(**network-generation, disclosed** — no agents, no scheduler, no ticks) on the shared
platform. Predictions were locked BEFORE running (`PREDICTIONS-locked.md`); the config
below was fixed before the run and was NOT tuned to make any clause pass.

## What was built

N = 1500 points placed uniformly at random in the 2D unit square `[0,1)²` with a **HARD
boundary** (no wrap / no torus — a point near an edge simply has fewer neighbours on that
side). Two points are connected iff their Euclidean distance is `≤ r` (the Gilbert "disk"
rule). The single control is the radius `r`; to target a mean degree we set
`r = √(⟨k⟩ / (N·π))`, inverting the ideal mean-degree relation `⟨k⟩ = N·π·r²`.

The graph is handed to `networkx` for the structural measurements (average clustering,
connected components), matching the `erdos_renyi` control module; only the edge
construction is spatial. Three structural quantities are measured:

- **Clustering C** — the average local clustering coefficient (`nx.average_clustering`).
- **Giant-component fraction S** — largest connected component size / N.
- **Measured mean degree ⟨k⟩_meas** — `2·(#edges)/N`.

Neighbour finding uses a **non-wrapped uniform cell grid** of side `≥ r` over the unit
square, so each point's r-neighbours all lie in its own cell or the (up-to-8) in-bounds
adjacent cells — **O(N)** rather than O(N²). Because the boundary is hard, edge cells are
NOT wrapped: they simply scan fewer neighbour cells. The cell-grid edge set is verified
equal to the brute-force all-pairs edge set in the tests. The graph is deterministic given
a seed (the only randomness is the seeded uniform draw of the N points).

**Erdos-Renyi control (for P1):** at each swept `⟨k⟩` an ER `G(n, p)` graph is built at
the *same* N and matched mean degree (`abm_auto.classics.erdos_renyi`). ER has no spatial
embedding, so its clustering is `C ≈ ⟨k⟩/N ≈ 0.005` — the fair non-spatial baseline
against which the RGG's geometric clustering is compared.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N | 1500 |
| ⟨k⟩ grid | 1, 2, 3, 4, 4.5, 5, 6, 8, 12 |
| seeds | 0–9 (10 seeds) |
| boundary | hard, unit square `[0,1)²` (no wrap) |
| connection rule | Euclidean distance ≤ `r = √(⟨k⟩/(N·π))` |
| control | ER `G(n,p)` at matched N, ⟨k⟩ |

## Results (mean over 10 seeds; raw)

| ⟨k⟩ | C_RGG | C_ER | C_RGG/C_ER | S (giant) | ⟨k⟩_meas | ideal N·π·r² | meas/ideal |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.1569 | 0.00020 | 784.6 | 0.008 | 1.012 | 1.000 | 1.012 |
| 2 | 0.3494 | 0.00091 | 384.0 | 0.019 | 1.999 | 2.000 | 0.999 |
| 3 | 0.4672 | 0.00182 | 256.4 | 0.058 | 2.978 | 3.000 | 0.993 |
| 4 | 0.5323 | 0.00268 | 198.9 | 0.222 | 3.964 | 4.000 | 0.991 |
| 4.5 | 0.5537 | 0.00312 | 177.5 | 0.491 | 4.445 | 4.500 | 0.988 |
| 5 | 0.5683 | 0.00341 | 166.8 | 0.797 | 4.923 | 5.000 | 0.985 |
| 6 | 0.5862 | 0.00424 | 138.3 | 0.947 | 5.877 | 6.000 | 0.980 |
| **8** | **0.5986** | 0.00550 | **108.9** | **0.998** | 7.791 | 8.000 | 0.974 |
| **12** | **0.6069** | 0.00796 | **76.2** | 1.000 | 11.501 | 12.000 | 0.958 |

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | High clustering, far above ER | C ∈ [0.50, 0.62] at ⟨k⟩∈[8,12] AND C_RGG/C_ER ≥ 30 | C = 0.599 (⟨k⟩=8), 0.607 (⟨k⟩=12); ratios 108.9, 76.2 | **REPRO** |
| **P2** | Giant component at HIGH ⟨k⟩ | S(⟨k⟩=2) < 0.30 AND S(⟨k⟩=8) > 0.85 AND S monotone | S(2)=0.019, S(8)=0.998; monotone ✓ | **REPRO** |
| **P3** | Mean-degree relation ⟨k⟩=N·π·r² | ⟨k⟩_meas/ideal ∈ [0.85,1.05] ∀r AND corr > 0.99 | ratios ∈ [0.958, 1.012]; corr = 0.99991 | **REPRO** |

## Honest interpretation

- **P1 — geometric clustering is real and ~100× above ER.** At ⟨k⟩ = 8 the RGG's average
  clustering is **0.599** and at ⟨k⟩ = 12 it is **0.607**, both sitting squarely inside the
  locked band `[0.50, 0.62]` and close to the infinite-plane bulk constant **0.5865**. The
  matched-⟨k⟩ ER control has clustering ≈ 0.005–0.008, so the ratio C_RGG/C_ER is **77–109×**
  in the graded window (and up to ~785× at ⟨k⟩=1) — vastly above the locked `≥ 30`. This is
  the defining RGG signature: a neighbour of a neighbour is very likely also within `r`,
  because the connection is geometric overlap of disks, which independent-edge ER cannot
  produce.

- **P2 — the giant component emerges at a HIGH critical mean degree, not ⟨k⟩=1.** S climbs
  from **0.008** (⟨k⟩=1, essentially fragmented) and **0.019** (⟨k⟩=2) through a sharp
  transition — 0.222 → 0.491 → 0.797 across ⟨k⟩ = 4, 4.5, 5 — to **0.998** at ⟨k⟩=8 and a
  fully spanning **1.000** at ⟨k⟩=12. The half-giant crossing sits right at the locked
  critical value **⟨k⟩_c ≈ 4.51** (S(4.5)=0.491), roughly **4.5× higher** than ER's ⟨k⟩=1
  threshold. S is monotone non-decreasing across the entire sweep. The spatial embedding
  *delays* percolation: local disks must overlap densely enough to bridge the plane.

- **P3 — the mean-degree relation ⟨k⟩ = N·π·r² holds with only the expected boundary loss.**
  Across all nine radii the realised ⟨k⟩_meas is within **0.958–1.012×** the ideal N·π·r²
  (inside the locked `[0.85, 1.05]` band; the mild downward drift with ⟨k⟩ — from ~1.01 at
  ⟨k⟩=1 to 0.958 at ⟨k⟩=12 — is exactly the hard-boundary loss, since a larger r means edge
  points lose a larger fraction of their disk). The Pearson correlation of ⟨k⟩_meas against
  N·π·r² across the sweep is **0.99991**, far above the locked `> 0.99`. The density–area
  identity is reproduced quantitatively.

- **Distinctness holds (keep-with-gate).** The RGG is not an ER/WS/BA relabelling: at
  matched ⟨k⟩ it has ~100× the clustering of ER and its giant component appears at ⟨k⟩≈4.51
  rather than ER's ⟨k⟩=1. The high clustering comes from the spatial embedding + distance
  connection, which is absent from ER, Watts–Strogatz, Barabási–Albert, and the
  configuration model.

**Bottom line:** all three locked structural claims of the 2D Gilbert disk model reproduce
cleanly and quantitatively — high geometric clustering ~100× above the ER baseline, a giant
component emerging at the high critical mean degree ⟨k⟩_c ≈ 4.51, and the ⟨k⟩ = N·π·r²
density relation with only the expected hard-boundary loss.

## Source

Dall, J. & Christensen, M. (2002). *Random geometric graphs.* Physical Review E 66:016121.
doi:10.1103/PhysRevE.66.016121. (The disk model traces to Gilbert 1961 *Random plane
networks*; its rigorous large-N theory to Penrose 2003 *Random Geometric Graphs*.)

Scope: a faithful reproduction of a published **network-generation** model (disclosed — no
agents, no ticks); no real-world data. The contribution is whether the harness +
lock-first-prediction discipline reproduce the RGG's high geometric clustering, its
high-⟨k⟩ giant-component threshold, and its mean-degree relation, and would catch an
artifact.
