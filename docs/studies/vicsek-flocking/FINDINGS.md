# Vicsek Flocking — FINDINGS

**Model:** Vicsek et al. (1995), "Novel type of phase transition in a system of
self-driven particles", Phys. Rev. Lett. 75:1226-1229. A genuine agent-based
reproduction (self-propelled `ParticleAgent`s on `abm_auto._platform`), graded on the
LOCKED metric: the order parameter φ. Predictions P1-P3 were locked BEFORE the run
(`PREDICTIONS-locked.md`); nothing below was tuned.

## What was run

N=300 particles in a 12×12 PERIODIC box (density ρ = N/L² ≈ 2.08), constant speed
v=0.03, interaction radius r=1. Each synchronous tick every particle sets its heading to
the argument of the average unit heading-vector of all particles within r of it (periodic
distance, self included) plus a fresh uniform noise in [−η/2, +η/2], then moves a step v
along the new heading and wraps into the box. Order parameter

  φ = |Σ_i e^{iθ_i}| / N   ∈ [0, 1].

Noise grid η ∈ {0.1, 0.5, 1, 2, 3, 4, 5}; 10 seeds per η; 500 ticks per run; φ measured
as the mean of the last 100 ticks (after the transient), then averaged over seeds.

## Results — φ vs noise η (mean over 10 seeds; min–max across seeds)

| η   | φ (mean) | std    | min    | max    |
|-----|----------|--------|--------|--------|
| 0.1 | 0.9971   | 0.0056 | 0.9802 | 0.9995 |
| 0.5 | 0.9751   | 0.0109 | 0.9458 | 0.9863 |
| 1.0 | 0.9165   | 0.0205 | 0.8641 | 0.9354 |
| 2.0 | 0.6400   | 0.0803 | 0.4931 | 0.7431 |
| 3.0 | 0.2962   | 0.0906 | 0.1634 | 0.4271 |
| 4.0 | 0.1052   | 0.0167 | 0.0789 | 0.1328 |
| 5.0 | 0.0586   | 0.0052 | 0.0523 | 0.0719 |

φ falls smoothly from a near-perfectly-aligned flock (φ ≈ 1.0) at low noise to nearly
disordered motion (φ ≈ 0.06) at high noise — the noise-driven order–disorder transition
Vicsek reported.

## Verdicts on the LOCKED metric (φ)

| # | Prediction | Pass clause | Measured | Verdict |
|---|------------|-------------|----------|---------|
| P1 | Order–disorder transition with noise | φ>0.5 at η=0.5 AND φ<0.2 at η=5.0 | φ(0.5)=0.975, φ(5.0)=0.059 | **REPRO** |
| P2 | φ non-increasing in η | φ(η) non-increasing across {0.5,1,2,3,4,5} | largest increase = 0.0000 | **REPRO** |
| P3 | Strong alignment in the ordered phase | φ>0.8 at η=0.1 | φ(0.1)=0.997 | **REPRO** |

All three locked clauses **REPRO** (3/3).

- **P1** clears both sides with margin: φ(η=0.5)=0.975 ≫ 0.5 and φ(η=5.0)=0.059 ≪ 0.2.
- **P2** φ is *strictly* monotonically non-increasing along the grid — the worst
  consecutive change is 0.0000 (no up-tick at all, comfortably inside the locked
  tolerance of 0.02).
- **P3** the ordered phase is essentially a perfect flock (φ=0.997 at η=0.1).

## Where the transition sits, and honest caveats

- **The transition is in the interior, not at the endpoints.** The steepest drop is
  between η=2 (φ≈0.64) and η=3 (φ≈0.30), and the across-seed spread is *largest* there
  (std≈0.08–0.09 at η=2 and η=3) — the expected critical broadening of a finite system
  near its transition, not a measurement artifact. Deep in either phase the spread is
  tiny (std≈0.005–0.02).
- **Finite-size / non-asymptotic claim.** This is one density (ρ≈2.08), one system size
  (N=300), one speed (v=0.03), measured over a 100-tick tail of a 500-tick run. The
  REPRO is of the *qualitative* transition and the locked φ thresholds, NOT of a
  critical exponent or the precise η_c (whose value is size- and density-dependent, and
  is the subject of the later debate on the order of the Vicsek transition — Grégoire &
  Chaté 2004). We do not claim to settle that; we claim the locked clauses hold.
- **Transient adequacy.** At the locked η values the φ series is visibly stationary well
  before tick 400 (see `example_phi_series` per η in `results.json`); the 100-tick
  measurement window is comfortably inside the steady regime for every η on the grid.
- **Scalar-noise convention.** We use the original "angular/scalar" noise of the 1995
  paper (noise added to the *resulting* heading), not the later "vectorial" noise
  variant; the locked predictions are stated for this convention.
- **Determinism.** Every run is reproducible from its seed (pinned by a test); the
  cell-list neighbour search is bit-for-bit equal to the brute-force all-pairs sum
  (pinned by a test), so the O(N) optimization does not change any result.

## Scope

Faithful reproduction of a published *synthetic* model; no real-world data. The
contribution is whether the harness + locking discipline reproduce the noise-driven
order–disorder transition and would have caught an artifact (e.g. a broken periodic
distance or a non-synchronous update would break P2/P3). Falsified clauses would have
been reported MISS; here all three hold.
