# Relative-Agreement with Extremists (Deffuant-Amblard 2002) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Deffuant, Amblard, Weisbuch & Faure 2002
(JASSS 5(4)), not tuned. Genuine agent-based. Verified; gate-checked.

**Model:** each agent i has opinion x_i ∈ [−1,1] AND uncertainty u_i (segment [x_i−u_i, x_i+u_i]).
Random ordered pairs (i influences j). Overlap h_ij = min(x_i+u_i, x_j+u_j) − max(x_i−u_i, x_j−u_j).
ONLY IF h_ij > u_i: j updates x_j += μ·(h_ij/u_i − 1)·(x_i − x_j) and u_j similarly (relative agreement).
Fully connected, N=200, μ=0.5. Extremists: fraction p_e=0.2, very low uncertainty u_e=0.1, opinions at
the extremes; moderates start with global uncertainty U. Outcome metric y = p'₊² + p'₋² (p'± = final
fraction near each extreme). ≥20 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | CENTRAL convergence at low moderate uncertainty. | U=0.4, symmetric (δ=0): y < 0.1 AND fraction of initially-moderate agents ending with \|x\|>0.8 is < 0.15 AND central-cluster mean \|x\| < 0.3 (moderates stay central; extremists isolated). |
| P2 | DOUBLE-EXTREME (bipolarization) at higher uncertainty. | U=1.2, symmetric: y ∈ [0.35, 0.65] (≈0.5) AND moderate-capture fraction (\|x\|>0.8) > 0.6 AND \|mean(x)\| < 0.2 (both poles populated). *Strictly exceeds P1's capture (<0.15 → >0.6): the P1/P2 gate holds.* |
| P3 | SINGLE-EXTREME under a deterministic asymmetry. | δ=0.1 (more +extremists), U=1.4: in ≥60% of seeds one pole captures >0.9 of initially-moderate agents (y≥0.85) while the opposite captures <0.1, and the captured pole matches the + majority in ≥80% of those runs. *(δ>0 avoids the symmetry-broken sign ambiguity that would false-MISS at δ=0.)* |

**Discipline:** N, μ, p_e, u_e, U grid, δ, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** deffuant (2000) is CONSTANT-threshold pairwise bounded confidence on [0,1],
opinion-only; this adds an evolving UNCERTAINTY + the relative-agreement rule + LOW-uncertainty
extremists, producing single/double-extreme attractors the plain model cannot reach.
