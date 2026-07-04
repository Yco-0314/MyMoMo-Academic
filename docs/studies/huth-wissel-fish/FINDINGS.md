# Huth & Wissel fish schooling (1992) — FINDINGS

**Paper.** Huth, A. & Wissel, C. (1992), "The simulation of the movement of fish schools",
*Journal of Theoretical Biology* 156(3):365-385. doi:10.1016/S0022-5193(05)80681-2.

**Framing: genuine-agent (zonal SPP fish, disclosed).** Each individual is an autonomous
self-propelled fish in continuous, unbounded 2D with a unit heading and a bounded turning
rate, integrating the standard nested behavioural zones (repulsion / parallel-orientation /
attraction) every step. This is NOT a grid CA and NOT the single-alignment Vicsek rule.

**Locked A/B (the distinctness of this reproduction).** All zonal forces (radii, speed,
bounded turn, noise, seeds, run length) are held identical between two arms; ONLY the
INTEGRATION RULE for combining orientation+attraction influence differs:

- **AVERAGING** — the fish averages the desired directions induced by ALL relevant
  neighbours (sum the in-orientation-zone headings and the unit vectors toward
  in-attraction-zone neighbours, then normalise).
- **DECISION** — the fish picks ONE neighbour, the single NEAREST orientation/attraction
  neighbour, and follows only that one (align to it if it is in the orientation zone, else
  steer toward it).

The repulsion override (steer away from any neighbour inside `zor`) is byte-identical in
both arms; collision avoidance is reflexive in both.

## Fixed configuration (locked BEFORE running; nothing tuned)

N=60 fish, speed s=1.0, repulsion radius zor=1.0, orientation-zone width dzoo=6.0,
attraction-zone width zoa_width=8.0, max turn theta_max=0.35 rad/step, heading noise
sigma=0.05 rad, initial cluster disc radius 4.0, n_steps=600, steady-state window
measure_last=250 (trailing), 8 seeds (0..7). The dzoo=6.0 orientation width places the
AVERAGING school in its canonical polarized-school regime (below ~dzoo=5 the averaging school
does not polarize; this is the shared-force calibration, chosen before grading and NOT a
per-clause knob — the only thing switched between the two graded arms is the integration
rule). Metrics: school polarization p = |mean(heading)| in [0,1]; nearest-neighbour distance
(NND) per fish and its coefficient of variation CV(NND) = std(NND)/mean(NND). Measurement is
seed-averaged over the trailing 250 steps after the school equilibrates.

## Results (actual run numbers)

| Arm | mean p | mean CV(NND) | mean NND |
|-----|-------:|-------------:|---------:|
| AVERAGING | **0.906** (min 0.900, std 0.003) | 0.603 (std 0.047) | 1.073 |
| DECISION  | **0.176** (max 0.296, std 0.084) | 0.483 (std 0.040) | 2.151 |

- polarization gap (p_avg − p_dec) = **+0.730**
- CV(NND) gap (cv_avg − cv_dec) = **+0.120**

Per-seed AVERAGING polarization: 0.91, 0.90, 0.91, 0.91, 0.91, 0.91, 0.90, 0.90 — every seed
strongly polarizes. Per-seed DECISION polarization: 0.08, 0.23, 0.19, 0.05, 0.30, 0.15, 0.14,
0.28 — no seed reaches 0.5.

## Per-clause verdicts (honest; a falsified clause is a valid MISS)

### P1 — averaging beats decision on polarization: **REPRO**
Pass clause: p_avg − p_dec ≥ 0.15. Observed gap = **0.730** (p_avg=0.906, p_dec=0.176),
nearly 5× the bar, with zero per-seed overlap (min averaging p=0.900 > max decision p=0.296).
This is the load-bearing averaging-advantage claim and it reproduces strongly: averaging the
headings of ALL orientation neighbours builds robust global consensus, whereas following a
single neighbour cannot. **REPRO.**

### P2 — averaging gives tighter cohesion (CV of NND smaller): **MISS**
Pass clause: CV(NND)_avg < CV(NND)_dec. Observed CV(NND)_avg = **0.603** is NOT smaller than
CV(NND)_dec = **0.483** — the averaging school's CV is *higher*. **MISS.** Honest cause: the
averaging school is far more compact (mean NND 1.07) than the decision school (mean NND 2.15).
The decision-rule fish spread into a looser, more diffuse cloud in which each fish's nearest
neighbour is more uniformly (Poisson-like) distributed, giving a *lower* coefficient of
variation of NND despite being less cohesive in absolute terms. The locked P2 metric (CV of
NND as a cohesion proxy) is confounded by the mean-NND scale difference between the two arms
and is falsified here. Absolute cohesion (mean NND) IS much tighter under averaging (1.07 vs
2.15); the *coefficient-of-variation* form of the cohesion claim is not.

### P3 — both rules still school (p > 0.5): **MISS**
Pass clause: p_avg > 0.5 AND p_dec > 0.5. Averaging schools (p_avg=0.906 > 0.5) but the
decision rule does NOT (p_dec=0.176, max over seeds 0.296, ≤ 0.5). **MISS.** Honest cause:
in a compact school the single nearest orientation neighbour keeps changing from step to step,
so following only that one fish produces a noisy chain of local alignments that never
coalesces into a global heading. The decision arm is therefore essentially averaging-vs-near-
disorder, not the "same-baseline averaging advantage over an already-schooling group" that P3
asserts. The averaging advantage on polarization (P1) is real and large, but it is an
advantage over a decision rule that barely schools — not over a schooling baseline.

## Summary

**1/3 locked clauses REPRO.** The load-bearing averaging-advantage on polarization (P1)
reproduces strongly and cleanly (gap +0.73, no seed overlap). The two secondary clauses are
honest MISSes with clear mechanistic causes: P2 because the CV-of-NND cohesion proxy is
confounded by the looser decision-school's lower dispersion (absolute mean NND is in fact
tighter under averaging: 1.07 vs 2.15), and P3 because the single-nearest-neighbour decision
rule fails to build a polarized school at all under these matched forces (p_dec≈0.18), so the
contrast is averaging-vs-near-disorder rather than a quantitative advantage over a schooling
baseline. No parameters, metrics, or thresholds were tuned to change any verdict; the
falsifications are reported as-is.
