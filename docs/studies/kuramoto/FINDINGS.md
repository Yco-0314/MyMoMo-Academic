# Kuramoto Synchronization — FINDINGS

**Authored 2026-06-30, after running, before the bundle.** Honest report against the
LOCKED claims (`PREDICTIONS-locked.md`). Falsified clauses would be reported MISS.

## What was run

A genuine agent-based reproduction of the mean-field Kuramoto model (Kuramoto 1975) on
the neutral ABM platform (`abm_auto._platform`): N=500 `OscillatorAgent`s, each carrying
a phase θ and a FIXED natural frequency ω drawn once from N(0,1) (seeded). All-to-all
coupling, synchronous Euler update

    θ_i(t+dt) = θ_i(t) + ( ω_i + (K/N)·Σ_j sin(θ_j − θ_i) )·dt,   dt = 0.05,

with every phase advanced from one start-of-tick snapshot. The coupling sum is computed
in O(N) via the mean-field identity Σ_j sin(θ_j−θ_i) = Im(e^{−iθ_i}·Σ_j e^{iθ_j}); a test
pins it equal to the brute-force O(N²) all-pairs sum.

Order parameter (the locked metric): r = |(1/N)·Σ_j e^{iθ_j}| ∈ [0,1]. Each run integrates
2000 steps and r is averaged over the last 1000 (a 1000-step transient is discarded).
Sweep K ∈ {0, 0.5, 1.0, 1.6, 2.0, 3.0, 4.0}, 5 seeds per K (seeds 0–4), seed-averaged with
reported range. N, ω-distribution, dt, K-grid, seed count, transient, and the metric were
all FIXED before the run; nothing was tuned.

## Results — r vs K (mean over 5 seeds; range = [min, max])

| K   | mean r | [min, max]      | std   |
|-----|--------|-----------------|-------|
| 0.0 | 0.0415 | [0.038, 0.046]  | 0.003 |
| 0.5 | 0.0526 | [0.047, 0.058]  | 0.004 |
| 1.0 | 0.0763 | [0.059, 0.110]  | 0.018 |
| 1.6 | 0.2796 | [0.175, 0.502]  | 0.115 |
| 2.0 | 0.7121 | [0.628, 0.761]  | 0.047 |
| 3.0 | 0.9283 | [0.923, 0.934]  | 0.004 |
| 4.0 | 0.9653 | [0.963, 0.967]  | 0.002 |

Mean-field critical coupling for ω~N(0,1): K_c = 2/(π·g(0)) = 2·√(2/π) ≈ **1.596**.

Measured synchronization onset (first K with mean r > 0.3): **K = 2.0**.

## Verdicts against the LOCKED claims

- **P1 — incoherent below K_c, synchronized above. REPRO.**
  r(K=0.5) = 0.053 < 0.3 (incoherent) AND r(K=3.0) = 0.928 > 0.6 (synchronized).

- **P2 — onset near K_c ≈ 1.6. REPRO.**
  First K with mean r > 0.3 is K = 2.0, which lies in the locked window [1.0, 2.2].
  The transition is sharp: r climbs 0.08 → 0.28 → 0.71 across K = 1.0, 1.6, 2.0 — i.e. it
  takes off right around the analytic K_c ≈ 1.60, with the grid's first super-0.3 point at
  the next node (K=2.0).

- **P3 — r monotone non-decreasing in K. REPRO.**
  r is non-decreasing across the whole grid: 0.042 → 0.053 → 0.076 → 0.280 → 0.712 →
  0.928 → 0.965. No reversal (largest adjacent decrease 0.0; finite-N slack 0.02 unused).

**3/3 locked clauses REPRO.**

## Honest caveats (finite-N)

- **Finite-N residual.** Below K_c the order parameter does not vanish; for N independent
  random phases r ~ 1/√N ≈ 1/√500 ≈ 0.045. The measured incoherent-regime values
  (0.042–0.076 for K ≤ 1.0) are exactly this 1/√N floor, NOT genuine coherence. This is a
  known finite-size effect; in the N→∞ mean-field limit r→0 strictly below K_c.

- **Critical-point variance.** Right at the analytic K_c (the K=1.6 node) the seed-to-seed
  spread is large (r ranges 0.175–0.502, std 0.115). This is the expected critical slowing
  / finite-size fluctuation near a continuous transition: individual realizations sit on
  either side of partial locking. The seed mean (0.28) lands just below the 0.3 onset
  threshold, so the measured onset falls at the next grid node (K=2.0). With more
  oscillators or a finer grid the onset would press down toward K_c ≈ 1.60; the locked
  window [1.0, 2.2] is deliberately wide enough to absorb this finite-N offset, and P2 is
  graded on the onset falling in that window, not on hitting 1.6 exactly.

- **Euler integration.** A first-order Euler step at dt=0.05 introduces O(dt) integration
  error; it is fixed across the whole sweep (not tuned per K) and is small relative to the
  finite-N effects above. The qualitative transition and the order parameter are robust to it.

- **Scope.** This is a faithful reproduction of a published synthetic model — no real-world
  data. The contribution is that the lock-first harness + discipline reproduce the
  synchronization transition (incoherent → coherent across K_c) and would have flagged a
  MISS had the onset, the incoherent floor, or the monotonicity come out wrong.

## Citation

Kuramoto, Y. (1975). *Self-entrainment of a population of coupled non-linear oscillators.*
In: International Symposium on Mathematical Problems in Theoretical Physics. Lecture Notes
in Physics 39, Springer, pp. 420–422. doi:10.1007/BFb0013365. Review: Strogatz, S.H.
(2000). *From Kuramoto to Crawford.* Physica D 143:1–20.
