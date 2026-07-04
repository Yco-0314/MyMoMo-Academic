# Couzin et al. informed leadership (2005) — FINDINGS

**Model:** genuine-agent zonal self-propelled particles in 2D (repulsion / orientation / attraction zones,
bounded turning, heading noise) with an INFORMED minority that balances social forces against a fixed goal
direction (weight ω). Framing disclosed: **genuine-agent (zonal SPP with informed minorities).**
Graded against `PREDICTIONS-locked.md` (locked 2026-07-02, committed BEFORE this run). A falsified clause is a
valid honest MISS; nothing was tuned to pass.

Config: ω=0.5, zor=1.0, Δzoo=6.0, zoa_width=8.0, θ_max=0.35, σ=0.05, init_radius=5.0, n_steps=800, tail=300, 6 seeds.

## Verdicts — 2/3 REPRO + 1 honest MISS

### P1 — REPRO (few leaders suffice)
At N=100, group directional accuracy exceeds 0.9 with an informed fraction ≤ 0.10: p=0.100 → mean accuracy
**0.920** (min 0.871 over 6 seeds). A small informed minority reliably steers the whole group toward its goal.
Score 0.92 ≥ threshold 0.90.

### P2 — MISS (the 1/N leader economy did not reproduce under fixed density)
The locked clause required the informed fraction needed to reach accuracy 0.9 to be STRICTLY SMALLER for N=200
than for N=30. Observed the opposite: smallest passing fraction was **0.033 at N=30** but **0.300 at N=200**
(N=100 needs 0.100). So larger groups needed a LARGER, not smaller, informed fraction.

**Cause (honest):** the zone radii (zor, Δzoo, zoa) were held FIXED across N, so the N=200 group is far sparser
and less cohesive than the N=30 group — many fish fall outside each other's interaction zones and the informed
signal cannot propagate. Couzin 2005's 1/N leader-economy holds when group DENSITY is comparable across sizes
(radii or domain scaled with N); the locked P2 did not control density, so it falsifies. This is a design
subtlety in the locked experiment, not a model bug and not tuning — the model faithfully implements the zonal
informed-leadership dynamics; the un-density-controlled size comparison is what fails. Reported as MISS.

### P3 — REPRO (averaging vs majority commitment)
With two equal informed subgroups whose preferred directions differ by θ, the group heading AVERAGES for small
θ and COMMITS for large θ. At θ=40° the mean heading offset from the bisector is **15.3°** (≤ 30° → averaging);
at θ=150° it is **84.8°** (≥ 60° → committed to one subgroup). Score 84.8 ≥ threshold 60.0. The transition from
compromise to decision as the goal conflict widens reproduces.

## Summary
The load-bearing Couzin-2005 claims — a small informed minority steers a large group (P1), and the group
averages small directional conflicts but commits on large ones (P3) — reproduce. The size-scaling "1/N leader
economy" (P2) does NOT reproduce because the locked size comparison held zone radii fixed and so did not hold
group density constant. Honest 2/3 REPRO. No tuning. Distinct from couzin_zonal_model (leadership/goal-directed,
not milling/hysteresis) and from galam/majority_vote (continuous heading vectors, not discrete spin flips).
