# Coord-Response ABM — LOCKED Predictions v2.1 (pre-registration)

**Status:** LOCKED before the v2.1 cross-treatment experiment run.
**Date locked:** 2026-06-28
**Branch:** `feat/coord-response-abm`
**Supersedes:** `PREDICTIONS-locked-v2.md`.

## Why v2.1 (transparent)

The v2 cross-treatment run (committed bundle `verdict-bundle-v2.json`) exposed a
**residual mechanism degeneracy**, not a finding: makespan was *insensitive to
the network* (mean_orig == mean_opt == 26.67, corr = NaN, 0/30 improved). Root
cause: the coordination info-delay was measured from `trigger_tick` (= 0) while
tasks actually start at predecessor-completion (much later), so the delay term
was always already in the past and never gated a task start except the first
one. A model whose makespan cannot respond to edges can register neither an
improvement nor the counterexample — the test had no discriminating power.

**Fix (commit `0547db7`, mechanism-correctness, verified OUTCOME-BLIND):** the
info-delay now gates from each task's `eligible_tick` (trigger + predecessors
done): `ready = eligible_tick + response_delay + ceil(coord_delay)`. Verified via
single-treatment diagnostics ONLY that (a) the original baseline still completes
all 9 tasks, (b) peak_overload > 1.0 still holds (1.875), and (c) makespan now
RESPONDS to coordination delay (slower info ×0.25 → makespan 47 vs base 39). The
optimized-vs-original-vs-null comparison was **NOT** consulted for the fix or for
these thresholds.

> **Lock-first + outcome-blind discipline.** I do not know the v2.1 cross-treatment
> outcomes. Any of P1–P5 may be FALSIFIED and will be reported as MISS. No
> thresholds/params are tuned to make a prediction pass.

## Mechanism (v2.1)

- Connected, improvable baselines (every required (lead,collaborator) DAG edge
  present at low weight).
- Info-delay gates task starts from eligibility; faster info (added/heavier edges
  on a task's coordination path) can advance a start by ≥ 1 tick.
- Biting overload: concurrency drives shared hubs' load above capacity
  (peak_overload ≈ 1.875), congestion throttles progress, overload raises failure
  probability. Added edges → earlier/more-concurrent starts → more overload, which
  CAN outweigh the timing gain (the counterexample mechanism).
- Timing-driven makespan (typical run ≈ 37 ticks; failed-task penalty 30).

## Experiment configuration (fixed here, before the run)

- N = 30 networks (`representative_network(seed=ni)`, ni = 0..29); seeds
  (0,1,2,3,4); budget B = 4; treatments original / optimized (CEI-protected on
  省应急管理厅) / null (B random edges); primary outcome makespan (lower better,
  penalty 30); null-gate margin 1.0 tick.

## Predictions (same spirit + thresholds as v2; scale unchanged ~timing)

- **P1 — Process effectiveness.** `optimized` beats `original` mean makespan in
  **≥ 60%** of the 30 networks. REPRO ≥60%; PARTIAL 50–60%; MISS <50%.
- **P2 — Null-gate.** Mean `optimized` beats mean `null` AND mean `original` by
  **≥ 1.0 tick** (gate passes → "not refuted"). REPRO if pass; MISS otherwise.
- **P3 — Consistency.** `corr(static_gain, makespan_gain)` is **> 0 and < 0.9**
  AND **≥ 1 counterexample** (static_gain > 0 but makespan_gain < 0). REPRO if
  both; PARTIAL if one; MISS if neither. (Note: if the optimizer's edges never lie
  on task coordination paths, makespan_gain may be ~0 ensemble-wide → corr near 0
  or NaN → P3 MISS; that is a valid honest divergence finding, reported as such.)
- **P4 — Phase ranking.** Reported-only (single combined DAG); compared to DOC A's
  监测预警 > 处置救援 > 事后恢复 ranking. REPORTED.
- **P5 — CEI validation.** Isolating the top-CEI department raises mean makespan
  **more** than isolating a median-CEI department. REPRO if so; MISS otherwise.

## Sensitivity analysis (mandatory)

±50% capacity & failure_prob (scaled from v2 hub/non-hub defaults); record whether
P1 and P2 hold. Robustness, not tuning.

## Honest scope

Synthetic representative ensemble, not real provinces; uncalibrated parameters set
for mechanism-functionality only; method-mechanism validity, not real-world
prediction; motivates real-network collection. No real network data.
