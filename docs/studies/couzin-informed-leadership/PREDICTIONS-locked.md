# Couzin et al. informed leadership (2005) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Couzin, Krause, Franks & Levin 2005 (Nature 433:513), not
tuned. **Genuine-agent (disclosed): zonal self-propelled particles with informed minorities.** Verified;
gate-checked.

**Model:** N zonal self-propelled agents in 2D (same repulsion/orientation/attraction substrate as the 2002
model). A fraction p of agents are INFORMED: they balance social forces with a fixed preferred goal direction
(weight ω). The rest are naïve (social forces only). Group directional accuracy = cos of the angle between the
group's mean heading and the informed goal (1 = perfectly on-target). Sweep informed fraction p and group size
N; for the majority-vs-averaging test, split informed agents into two subgroups with preferred directions
separated by angle θ.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | A few leaders suffice. | at N=100, group directional accuracy exceeds 0.9 with an informed fraction p ≤ 0.10 (a small minority steers the group). |
| P2 | Larger groups need a smaller informed fraction. | the informed fraction needed to reach accuracy 0.9 is strictly smaller for N=200 than for N=30 (the required fraction falls with group size — a ~1/N leader economy). |
| P3 | Averaging vs majority. | with two equal informed subgroups whose preferred directions differ by θ, the group heading AVERAGES the two when θ is small (< ~60°) but COMMITS to one (symmetry-break / majority) when θ is large (> ~120°). |

**Discipline:** N grid, p grid, goal weight ω, zone radii, θ values, seeds, run length FIXED; metrics locked;
no tuning. Falsified → MISS. gate_design_check: accuracy averaged over seeds after heading equilibration; P1/P2
are the load-bearing leader-economy claims, P3 the qualitative averaging→commitment transition (graded by the
angular spread of the group heading vs the two goals).
**Distinctness (keep):** locks a leadership-fraction-vs-accuracy curve (a 1/N leader-economy law) and a
majority-vs-averaging heading transition from CONTINUOUS spatial motion — not the milling/hysteresis phase
portrait of couzin_zonal_model, and not discrete spin/vote flips like galam_majority / majority_vote.
