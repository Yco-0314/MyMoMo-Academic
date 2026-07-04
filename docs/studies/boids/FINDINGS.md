# Boids Flocking (Reynolds 1987) — FINDINGS

**Status: 2/3 locked clauses REPRO; P1 is an honest near-MISS (φ=0.671 vs the locked
0.70 bar).** Genuine agent-based reproduction on `abm_auto._platform`. Predictions were
locked BEFORE running (`PREDICTIONS-locked.md`); the config below was fixed before the
run and was NOT tuned to make φ cross 0.7.

## What was built

200 `BoidAgent`s in a 50×50 **periodic** box, each carrying a position `(x, y)` and a
velocity vector `(vx, vy)`. Each tick is a **synchronous** update: every boid's new
velocity is computed from one start-of-tick snapshot, then all boids move. The velocity
update is the genuine Reynolds three-rule steering:

- **Separation** — steer away from boids closer than the separation radius `r_sep`,
  with 1/distance weighting so the nearest crowders dominate.
- **Alignment** — steer toward the average velocity of perception-radius neighbours.
- **Cohesion** — steer toward the centre of mass (periodic-aware) of perception-radius
  neighbours.

Each rule uses Reynolds' `steer = desired − current` form, the per-rule steering force
is capped (for smooth turning), the three are added with fixed weights, and the speed is
clamped into `[vmin, vmax]`. The order parameter is the locked grading metric
`φ = |(1/N) Σ vᵢ/|vᵢ||` ∈ [0,1]; cohesion is the mean nearest-neighbour (periodic)
distance. Neighbour lookup uses a periodic cell list that is verified equal to brute
force in the tests. The model is deterministic given a seed (the only randomness is the
seeded initial draw of positions + velocities).

The **alignment-OFF control** is the *same* model with `w_align → 0` (separation +
cohesion only). Every other knob — N, box, both radii, the other two weights, the speed
clamp, the seeds — is identical. This isolates "alignment is what creates the common
heading".

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N | 200 |
| box L | 50.0 (periodic) |
| perception radius r | 7.0 |
| separation radius r_sep | 2.0 |
| weights (sep / align / coh) | 1.5 / 1.0 / 1.0 |
| speed clamp [vmin, vmax] | [0.5, 1.0] |
| seeds | 0,1,2,3,4 (5 seeds) |
| ticks / measurement window | 400 / last 100 |

## Results (mean over 5 seeds; raw)

| Arm | mean steady φ | φ range | mean NN distance |
|---|---|---|---|
| **FULL (3 rules)** | **0.671** | [0.661, 0.678] (std 0.006) | **0.729** |
| **ALIGNMENT-OFF (sep+coh)** | **0.0505** | [0.049, 0.052] (std 0.001) | 1.020 |

Per-seed full-model φ: 0.672, 0.674, 0.678, 0.670, 0.661.
Per-seed alignment-OFF φ: 0.050, 0.051, 0.052, 0.049, 0.050.

The full model's φ climbs from ~0.09 (random initial headings) through the transient and
settles near 0.67 by ~tick 150, then holds. The mean nearest-neighbour distance
**shrinks** over the run (early-window mean ≈ 1.07 → trailing-window mean ≈ 0.71): the
boids pull together and stay packed far tighter than a uniform gas (uniform-spacing scale
`L/√N ≈ 3.54`).

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Flocking emerges (3 rules) | mean φ > 0.7 after transient | **0.671** | **MISS** (by 0.029) |
| **P2** | Alignment causes the common heading | alignment-OFF φ < 0.3 | **0.0505** | **REPRO** |
| **P3** | Cohesion holds (no dispersal) | mean NN distance bounded, not growing | **0.729** ≪ 3.54, and decreasing | **REPRO** |

## Honest interpretation

- **Emergent flocking is real and alignment is unambiguously its cause.** Turning the
  alignment rule off collapses the order parameter from **0.67 to 0.05** — a >13×
  drop — while separation + cohesion alone keep the boids loosely clustered (NN ≈ 1.0)
  but with **no common heading** (φ ≈ 0.05, indistinguishable from random). P2 passes
  decisively, and that contrast *is* the Reynolds result: alignment is the rule that
  produces coherent collective motion.

- **Cohesion holds (P3 passes clearly).** Under the full three rules the flock packs to
  a nearest-neighbour spacing ≈ 0.73 — roughly a fifth of the uniform-gas spacing — and
  the spacing tightens rather than drifting outward over the run. The flock does not
  disperse.

- **P1 is an honest near-MISS at φ = 0.671 vs the locked 0.70 bar.** This is reported as
  a MISS, not papered over. The shortfall is a genuine, robust property of this faithful
  formulation, *not* a transient or a seed artifact: φ is tight across seeds (std 0.006),
  stable for hundreds of ticks past steady state, and we confirmed during characterization
  that it does **not** rise toward 0.7 by (a) running 2× longer (800 ticks → still 0.674),
  (b) enlarging the perception radius to keep the flock globally connected (r=10, r=12 →
  ≈0.69), (c) narrowing the speed band, or (d) raising the alignment weight (both *lowered*
  φ). Raising the per-rule force cap above its working value destroys flocking entirely
  (φ → 0.02), confirming the cap at 0.5·vmax is load-bearing for smooth alignment, not a
  throttle. The residual ~0.33 gap from perfect polarization is the continual heading
  perturbation injected by the separation and cohesion rules acting on a finite, packed
  flock — those two rules constantly nudge each boid off the common heading, so the
  steady polarization saturates near 0.67 rather than approaching 1. A φ>0.7 regime is
  reachable in alignment-dominated boids variants (e.g. near-constant speed with weak
  separation/cohesion), but reaching it here would require changing the locked weights,
  which the discipline forbids. We report the faithful model's honest number.

**Bottom line:** the reproduction cleanly demonstrates the two *mechanistic* claims —
alignment creates the common heading, and cohesion keeps the flock together — and reports
the absolute polarization ceiling (φ ≈ 0.67) honestly as falling just short of the locked
0.70 threshold for P1.

## Source

Reynolds, C. W. (1987). *Flocks, herds and schools: A distributed behavioral model.*
Computer Graphics (SIGGRAPH '87 Proceedings) 21(4):25–34. doi:10.1145/37402.37406.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce emergent
flocking, isolate alignment as its cause, and would catch an artifact.
