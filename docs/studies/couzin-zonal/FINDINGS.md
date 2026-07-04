# Couzin et al. (2002) zonal collective motion — FINDINGS

**Claim reproduced:** Couzin, I. D., Krause, J., James, R., Ruxton, G. D. & Franks, N. R.
(2002), "Collective Memory and Spatial Sorting in Animal Groups", *Journal of Theoretical
Biology* 218(1):1–11. doi:10.1006/jtbi.2002.3065.

**Framing:** genuine-agent (3-zone self-propelled particles, 2D, disclosed). Each individual
is an autonomous self-propelled agent with a position, a unit heading, a constant speed, and
a bounded turning rate, integrating three nested behavioural zones (repulsion, orientation,
attraction) every step. This is NOT a grid CA and NOT the single-alignment Vicsek rule.

**Verdict tier:** refutation. A passed clause means "not refuted at the locked bar"; a failed
clause is a valid, honest MISS. Nothing was tuned to make a clause pass.

## What was fixed and what was dialled

FIXED before running (discipline): N = 60 agents, speed s = 1.0, repulsion radius zor = 1.0,
attraction-zone width zoa_width = 8.0, max turn theta_max = 0.35 rad/step, heading noise
sigma = 0.02 rad, initial disc radius 5.0, seed set {0..5} (6 seeds), run length 1000 steps
with a trailing 300-step steady-state window; the hysteresis ramp grid, equilibration, and
the polarization switch threshold (0.65); and the two order-parameter metrics (polarization
p, angular momentum m) and their locked pass bars.

DIALLED (the only knob): the orientation-zone width **Delta_zoo**. Narrow (Delta_zoo = 4.0)
probes the mill regime; wide (Delta_zoo = 12.0) probes the parallel-flock regime; and a slow
quasi-static up/down ramp over Delta_zoo in [1.0, 10.0] — continuing the SAME swarm across
the whole loop — probes hysteresis.

## Order parameters (locked metrics)

- Polarization p = |(1/N) sum_i d_i| in [0,1] — heading coherence; p ~ 1 is a parallel flock.
- Angular momentum m = |(1/N) sum_i (r_i_hat × d_i)| in [0,1], with r_i the position relative
  to the group centroid — rotational coherence about the centroid; m ~ 1 is a coherent torus.
  A mill has LOW p and HIGH m; a parallel flock has HIGH p and LOW m.

## Results (actual run numbers, 6 seeds)

| Clause | Locked pass bar | Measured | Verdict |
|---|---|---|---|
| P1 mill (narrow Delta_zoo = 4.0) | p < 0.35 AND m > 0.65 | p = 0.201 (range [0.153, 0.278]); m = 0.493 (range [0.411, 0.546]) | **MISS** |
| P2 parallel (wide Delta_zoo = 12.0) | p > 0.9 AND m < 0.2 | p = 0.998 (min 0.996); m = 0.017 (max 0.033) | **REPRO** |
| P3 hysteresis (up/down Delta_zoo ramp) | mean \|up_switch − down_switch\| >= 1 length-unit | mean gap = 1.75 (min 1.00); 6/6 seeds switch on both branches; 6/6 seeds gap >= 1 | **REPRO** |

Per-seed narrow-zone m: 0.49, 0.52, 0.55, 0.41, 0.45, 0.54.
Per-seed hysteresis up-switch Delta_zoo: 6.0, 5.5, 6.0, 6.0, 5.0, 5.5; down-switch: 3.5, 4.0,
4.0, 4.0, 4.0, 4.0; gap: 2.50, 1.50, 2.00, 2.00, 1.00, 1.50.

## Per-clause honest reading

**P1 (mill) — MISS.** At the narrow orientation zone the group settles into a distinct,
LOW-polarization state (mean p = 0.201, comfortably below the locked p < 0.35 bar) that is
also the strongest-rotation regime in the whole Delta_zoo sweep — its angular momentum
(mean m = 0.493) is an order of magnitude above the parallel flock's m = 0.017. So a
rotating, milling-type state clearly exists and is qualitatively distinct from both the
disordered swarm and the polarized flock. However, its angular momentum **ceilings around
m ≈ 0.5 and never reaches the aggressive locked bar of m > 0.65** (max over 6 seeds = 0.546).
The clause is graded on BOTH sub-conditions, and the m > 0.65 sub-condition fails, so P1 is an
honest MISS. This was flagged in the lock as a MISS-risk clause. Cause: with this
implementation's zone geometry and agent count the torus does not tighten into the very
coherent single-ring rotation that an m > 0.65 bar demands; larger, more sharply repulsive
mills in the original paper reach higher angular momentum, but reproducing that specific
number is not achievable at the locked config without tuning — which the discipline forbids.
The qualitative mill (low p, elevated m, distinct from the flock) IS reproduced; only the
specific quantitative bar is not. Reported as MISS rather than adjusted.

**P2 (parallel flock) — REPRO.** At the wide orientation zone the group forms an almost
perfectly coherent moving flock: mean polarization p = 0.998 (min 0.996 over seeds), far
above the p > 0.9 bar, while angular momentum collapses to m = 0.017 (max 0.033), far below
the m < 0.2 bar. Both sub-conditions pass on every seed. This is the robust wide-zone limit
the lock anticipated, and it changed from the mill purely by widening Delta_zoo — no other
rule changed.

**P3 (hysteresis) — REPRO.** Ramping Delta_zoo slowly UP (from a warmed-up swarm) and then
DOWN — threading the SAME swarm from the top of the up-branch into the down-branch — the
collective state is history-dependent. On the way up the swarm→polarized switch occurs around
Delta_zoo ≈ 5.0–6.0; on the way down the polarized→swarm switch occurs around
Delta_zoo ≈ 3.5–4.0. The polarized flock therefore PERSISTS to substantially narrower
orientation zones than it needed to first form, giving a mean hysteresis gap of 1.75
model length-units (min 1.00), above the locked >= 1.0 bar, with all 6 seeds switching on
both branches and all 6 gaps >= 1.0. The carry-forward of swarm state across the ramp is what
makes this bistability observable; a fresh swarm at each Delta_zoo would erase it.

## Distinctness (why this is not just Vicsek or boids)

The reproduced signature is the joint (polarization, angular-momentum) phase portrait as a
SINGLE zone-width parameter varies: a milling/rotating low-polarization state at narrow
orientation, a parallel flock at wide orientation, and a bistable HYSTERESIS loop between
them. vicsek_flocking has one alignment rule and one order/disorder threshold — no distinct
mill and no hysteresis. boids has no zone-width control parameter. The mill's angular
momentum and the hysteresis gap are exactly the observables those simpler models cannot
produce, so the harness would catch a Vicsek-shaped artifact masquerading as this model.

## Bottom line

2 of 3 locked clauses REPRO (P2 parallel flock, P3 hysteresis). P1 (mill) is an honest MISS:
a distinct low-polarization rotating state exists (p = 0.20, m = 0.49) but its angular
momentum ceilings below the locked m > 0.65 bar. The MISS is reported, not tuned away.
