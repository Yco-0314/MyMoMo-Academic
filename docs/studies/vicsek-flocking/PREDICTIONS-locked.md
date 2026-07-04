# Vicsek Flocking — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Vicsek et al. (1995), not tuned. Genuine
agent-based (self-propelled particle agents).

**Model:** N=300 particles, L×L periodic box (L≈12 → density ρ≈2), speed v=0.03, radius r=1.
Each tick: heading ← mean heading of particles within r (incl. self) + uniform noise in
[−η/2, η/2]; then move. Order parameter φ = |Σ e^{iθ}|/N, measured after transient. Sweep
η∈{0.1,0.5,1,2,3,4,5}. Mean over ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Order–disorder transition with noise. | φ > 0.5 at η=0.5 AND φ < 0.2 at η=5.0 |
| P2 | φ monotonically non-increasing in η. | φ(η) non-increasing across {0.5,1,2,3,4,5} |
| P3 | Strong alignment in the ordered phase. | φ > 0.8 at η=0.1 |

**Discipline:** N, L, v, r, η-grid, seeds FIXED + metric (φ) locked before run; no tuning.
Falsified → MISS.
