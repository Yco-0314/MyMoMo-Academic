# Buhl et al. marching locusts (2006), Czirok 1D SPP variant — FINDINGS

**Paper:** Buhl, J., Sumpter, D. J. T., Couzin, I. D., Hale, J. J., Despland, E.,
Miller, E. R. & Simpson, S. J. (2006), "From disorder to order in marching locusts",
*Science* 312(5778):1402–1406. doi:10.1126/science.1125142.
**Dynamics:** the Czirók 1D self-propelled-particle model (Czirók, Barabási & Vicsek,
*Phys. Rev. Lett.* 82:209, 1999).

**Framing (disclosed): genuine-agent (self-propelled particles, 1D ring, disclosed).**
Each locust is an autonomous agent carrying its own continuous position on a periodic ring
and a discrete heading `s ∈ {−1, +1}`. Every synchronous tick each agent averages the
heading of the neighbours within interaction range `R` over the **real ring geometry**
(no mean-field field, no grid), applies the Czirók alignment response `G(u) = tanh(β·u)`
plus uniform heading noise, takes the sign, then moves at fixed speed and wraps. The
control parameter is the **density** `ρ = N / Lr`, dialled by varying the ring length `Lr`
at fixed `N`. The order parameter is `|⟨v⟩| = |(1/N) Σ sᵢ| ∈ [0, 1]`.

**Discipline (binding):** `N = 60`, `R = 1.0`, `η = 2.0`, `β = 2.0`, `speed = 0.1`, the
ring-length grid, the 6-seed set (`seed_base = 0`), `n_steps = 6000`, and
`measure_last = 4000` were all FIXED before the run. ONLY the ring length (= the density
knob) is dialled. Nothing was tuned to make a clause pass; a falsified clause is reported
as an honest MISS. Predictions were locked in `PREDICTIONS-locked.md` and committed before
any run.

## Density sweep (low → high density), mean over 6 seeds

| ρ = N/Lr | Lr | mean \|⟨v⟩\| | [min, max] | total flips (6 seeds) | seeds with a flip |
|---|---|---|---|---|---|
| 0.100 | 600 | 0.238 | [0.161, 0.353] | 592 | 6/6 |
| 0.200 | 300 | 0.581 | [0.440, 0.701] | 42 | 4/6 |
| 0.300 | 200 | 0.696 | [0.575, 0.775] | 39 | 2/6 |
| 0.500 | 120 | 0.801 | [0.764, 0.835] | 1 | 1/6 |
| 1.000 | 60 | 0.881 | [0.867, 0.899] | 2 | 2/6 |

The order parameter rises monotonically with density, from a disordered band at low
density to a coherent marching band at high density — the Buhl-et-al. density-driven
onset of collective marching. Direction reversals are frequent at low/near-critical
density and vanish deep in the ordered phase.

## Verdicts (honest; a falsified clause is a valid MISS)

### P1 — density-driven order/disorder crossover — **REPRO**
Score (crossover span `high − low`) = **0.642**; carrier gap = 0.4.
At the lowest swept density (ρ = 0.100) the mean order parameter is
**0.238 < 0.3** (disordered), and at the highest swept density (ρ = 1.000) it is
**0.881 > 0.7** (collective marching). The clear order/disorder crossover as density
rises is reproduced.

### P2 — intermittent direction reversals near threshold — **REPRO**
Score (near-critical seeds that switched) = **4 / 6**; threshold = ≥ 1.
This is the pre-registered honest MISS-risk clause. At the near-critical density
(ρ = 0.200) the net marching direction reverses in **4 of 6 seeds**
(per-seed flips `[2, 0, 7, 0, 4, 29]`, total 42, switching rate ≈ **1.75×10⁻³ / tick**),
so the switching rate is `> 0`. Deep in the ordered phase (high density ρ = 1.500) the
**median seed shows 0 flips** (per-seed flips `[0, 0, 0, 0, 0, 0]`, total 0, rate = 0 /
tick): the typical marching band never reverses. The near-critical switching rate is
orders of magnitude above the high-density rate — the empirical signature of near-critical
locust bands is reproduced. (The reversals are stochastic per seed, as expected of a
finite-N near-critical fluctuation; the clause is graded on whether switching is *present*
near-critical and *absent* in the typical high-density run, not on a tuned flip count.)

### P3 — monotone ordering in density — **REPRO**
Score (worst per-step change in mean `|⟨v⟩|`) = **+0.080**; tolerance = −0.05.
Across the density grid the mean order parameter is non-decreasing on every step
(steps: +0.343, +0.115, +0.105, +0.080), well within the 0.05 tolerance. Ordering
increases monotonically with density.

## Summary

**3 / 3 locked clauses REPRO.** The genuine-agent Czirók 1D self-propelled-particle
reproduction on a periodic ring exhibits the Buhl-et-al. density-driven order/disorder
transition (P1), the near-critical intermittent direction reversals that vanish deep in
the ordered phase (P2, the pre-registered MISS-risk clause), and monotone ordering in
density (P3). Metrics, thresholds, and parameters were fixed before the run; only the
density (ring length at fixed N) was dialled.

**Distinctness.** This locks the 1D ring-arena **density**-driven transition with
spontaneous global-direction reversals, distinct from `vicsek_flocking` (a **noise**-driven
transition at fixed density on a 2D torus) and `boids` (vector-velocity three-rule
steering). The reproduction is a faithful single-implementation study of a published
self-propelled-particle model; there is no real-world data and no cross-tool baseline. The
contribution is whether the harness + discipline reproduce the transition and would catch
an artifact.
