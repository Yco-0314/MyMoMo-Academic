# Coord-Response ABM — LOCKED Predictions (pre-registration)

**Status:** LOCKED before any full-ensemble experiment run.
**Date locked:** 2026-06-28
**Branch:** `feat/coord-response-abm`
**Locked at commit:** the commit that introduces this file (see `git log`).

> **Lock-first discipline (mymomo).** These predictions are committed BEFORE
> `examples/coord_response/run.py` is ever executed on the full N=30 ensemble.
> I do **not** know the outcomes. Any of P1–P5 may be **FALSIFIED**. A falsified
> prediction is a valid, honest result and will be reported as such (MISS). I
> will **not** tune thresholds, parameters, or the model to make a prediction
> pass. The null-gate, being refutation-tier, can only render "not refuted",
> never "verified".

## Experiment configuration (fixed here, before the run)

- Ensemble: **N = 30** representative networks (`representative_network(seed=ni)`,
  `ni = 0 .. 29`).
- Seeds per (network, treatment): **(0, 1, 2, 3, 4)** — 5 stochastic replicates.
- Edge-edit budget: **B = 4**.
- Treatments: `original` / `optimized` (DOC-A-style global-efficiency edge-edit,
  CEI-protected on 省应急管理厅) / `null` (B random edges).
- Primary outcome: **makespan** (lower is better; failed critical task penalty =
  100.0 ticks, pre-registered).
- Null-gate margin: **1.0 tick**.

## Predictions

### P1 — Process effectiveness
`optimized` beats `original` on mean makespan in **≥ 60%** of the 30 ensemble
networks (i.e. ≥ 18 / 30 networks show `mean_opt < mean_orig`).

- REPRO if ≥ 60% improved; PARTIAL if 50–60%; MISS if < 50%.

### P2 — Null-gate (the central refutation test)
Mean `optimized` makespan beats mean `null` makespan by **≥ 1.0 tick** (the
`CoordNullGate` margin) AND beats mean `original` by ≥ 1.0 tick — i.e. the
`CoordNullGate.judge(...)` verdict **passes** ("not refuted").

- REPRO if the gate passes; MISS if it does not (the method "just adds edges,
  not the *right* edges").

### P3 — Consistency (the headline divergence)
`corr(static_efficiency_gain, makespan_gain)` across the 30 networks is
**> 0 and < 0.9** (positive but imperfect), **AND** at least **1 counterexample**
exists (a network where `static_gain > 0` but `makespan_gain < 0`, i.e. static
efficiency rose yet the simulated process got worse).

- REPRO if both clauses hold; PARTIAL if exactly one holds; MISS if neither.

### P4 — Phase ranking
The makespan-gain ranking is **reported and compared** to DOC A's static phase
ranking (监测预警 warning > 处置救援 response > 事后恢复 recovery, i.e.
7.97% > 3.45% > 1.77%). Because v1 uses a single combined 9-task DAG (not three
separate per-phase configs), this prediction is locked as **"reported, not
pass/fail"** — the phase-level makespan contribution is reported and any
divergence from DOC A's static ranking is noted honestly.

- REPORTED (always); divergence-from-DOC-A noted if present.

### P5 — CEI validation
Removing (isolating) the **top-CEI** department raises mean makespan **more** than
removing a **median-CEI** department, averaged over the ensemble.

- REPRO if top-CEI removal degrades makespan more than median-CEI removal;
  MISS otherwise.

## Sensitivity analysis (mandatory — params are uncalibrated)

A sensitivity pass over department `capacity` and `failure_prob` (e.g. ±50%) is
run and the report records whether the **P1** and **P2** verdicts hold under it.
This is a robustness check, not a tuning loop; the locked thresholds above are
not changed by its outcome.

## Honest scope (binds every output)

Synthetic representative ensemble — **not** any real province. Agent parameters
(capacity / delay / failure) are **not** empirically calibrated. The claim is
**method-mechanism validity**, not real-world response prediction. This study
*motivates* collecting real department-coordination networks for a future exact
validation. There is NO real network data (only DOC A's reported optimal edges,
top-CEI nodes, and per-phase static gains).
