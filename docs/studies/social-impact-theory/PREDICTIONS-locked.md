# Dynamic Social Impact Theory — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Nowak, Szamrej & Latané 1990 (Psych. Review
97:362; impact functional as in Castellano-Fortunato-Loreto 2009 RMP Eq. 16), not tuned.
Genuine agent-based (fixed agents, distance-weighted influence). Verified against the sources.

**Model:** L×L square lattice (L=41, N=1681), one agent per site, FIXED in space. Binary
opinion σ_i = ±1. Each agent carries two i.i.d. traits ~U[0,1], held fixed: persuasiveness
`p_i` (power to convert opponents) and supportiveness `s_i` (power to reinforce allies). The
total social impact on i is persuasive MINUS supportive:

  I_i = Σ_j p_j/g(d_ij)·(1−σ_iσ_j) − Σ_j s_j/g(d_ij)·(1+σ_iσ_j),

with Euclidean distance d_ij, decay `g(d) = 1 + d^α`, α = 2 (inverse-square, faithful to the
original; self term excluded). DETERMINISTIC dynamics (zero social temperature, h=0): update
σ_i ← sign(I_i flip rule) — an agent flips iff the opposing impact exceeds the supporting
impact. Synchronous or sequential sweeps run to a FIXED POINT (freeze). Start near f₀ ≈ 0.5
(random ±1). ≥50 seeds (the minority-survival band is a seed-ensemble statistic).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | No full consensus from a balanced start. | mean surviving minority fraction `f_min` at freeze is in the band **[0.08, 0.45]** averaged over ≥50 seeds — i.e. a stable NONZERO minority (not 0 = consensus, not ~0.5 = frozen noise). |
| P2 | Spatial clustering / self-organization. | the same-opinion nearest-neighbour bond fraction rises to **≥ 0.75** at freeze (vs ≈0.5 for the random start). |
| P3 | Minority persists in coherent CLUSTERS, not scattered singletons. | largest majority cluster ≥ 0.55·N at freeze AND ≥1 minority cluster of size ≥ 5 survives in ≥80% of seeds. |

**Discipline:** L, α, trait distributions, the impact functional, deterministic (h=0) update,
seed count FIXED + metrics locked; no tuning. Falsified → MISS. Honest-MISS risk (disclosed):
minority survival is a ZERO-NOISE, finite-size phenomenon — adding social temperature or
per-agent fields erodes the stable domains; the locked run is h=0 on a finite lattice.
Nearest built: schelling (spatial clustering by RELOCATION) — social impact keeps agents fixed
and flips opinions by distance-weighted impact, giving minority survival WITHOUT movement.
