# Seceder Model — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Dittrich, Liljeros, Soulier & Banzhaf (2000),
not tuned. Genuine agent-based.

**Model:** N=200 entity agents, each a real 1D trait (init ~N(0,1)). Reproduction event: pick 3
random entities; the one with the LARGEST distance to their 3-mean reproduces a mutated offspring
(value + N(0,σ), σ small); the offspring replaces a random entity. Many events. Outcome = #clusters
on the trait line + population variance. ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Spontaneous multi-cluster formation. | ≥ 2 clusters (typically ≈3) at steady state |
| P2 | Diversity persists (no collapse). | population variance stays ≫ the mutation floor (does not collapse to one point) |
| P3 | Cluster structure is stable. | cluster count ≈ constant over the late run (not transient) |

**Discipline:** N, σ_mut, run length, seeds FIXED + metric (cluster count + variance) locked; no
tuning. Report the measured #clusters honestly (the standard 1D seceder gives ≈3). Falsified → MISS.
