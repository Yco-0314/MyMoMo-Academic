# Coord-Response ABM — LOCKED Predictions v2 (pre-registration)

**Status:** LOCKED before the v2 cross-treatment experiment run.
**Date locked:** 2026-06-28
**Branch:** `feat/coord-response-abm`
**Supersedes:** `PREDICTIONS-locked.md` (v1). v1 was invalidated by two mechanism
artifacts (disconnected baselines → penalty-dominated makespan; peak_overload
capped at 1.0 → overload never activated). v2 fixes both; these predictions are
re-locked for the corrected mechanism.

> **Lock-first + outcome-blind discipline (mymomo).** The v2 mechanism was
> calibrated using ONLY single-treatment diagnostics — verifying (a) the ORIGINAL
> baseline completes all 9 tasks (0 failed) and (b) peak_overload > 1.0 occurs.
> The optimized-vs-original-vs-null makespan comparison was **NOT** consulted
> during calibration, and these thresholds are **NOT** tuned to make any
> prediction pass. I do **not** know the v2 outcomes; any of P1–P5 may be
> **FALSIFIED** and will be reported as MISS. The null-gate, being refutation
> tier, can only render "not refuted", never "verified".

## Mechanism (v2) — why these thresholds

- **Connected, improvable baselines.** Every required (lead, collaborator) DAG
  edge exists at LOW weight, so the ORIGINAL network completes all tasks but
  leaves room for DOC A's global-efficiency edge-edit to shorten coordination
  paths (info-delay = 1/w).
- **Biting overload.** Faster info → tasks start sooner → more concurrency →
  shared hub departments' demand exceeds capacity (peak_overload > 1.0) →
  congestion throttles progress and overload raises failure probability. This is
  the counterexample engine: added edges CAN worsen makespan even as static
  efficiency rises.
- **Timing-driven makespan.** A full run now completes in ≈ 26 ticks; the failed
  task penalty is 30 (≈ one extra run's worth), so makespan reflects response
  TIMING, not a failed-task count. The thresholds below are stated on this scale.

## Experiment configuration (fixed here, before the run)

- Ensemble: **N = 30** representative networks (`representative_network(seed=ni)`,
  `ni = 0 .. 29`).
- Seeds per (network, treatment): **(0, 1, 2, 3, 4)**.
- Edge-edit budget: **B = 4**.
- Treatments: `original` / `optimized` (DOC-A-style, CEI-protected on 省应急管理厅)
  / `null` (B random edges).
- Primary outcome: **makespan** (lower is better; failed-task penalty = 30.0,
  timing-driven).
- Null-gate margin: **1.0 tick** (the minimum resolvable response-time
  improvement; ≈ 4% of a typical makespan — kept absolute and unchanged from v1
  because it is a timing margin, not a penalty-scale quantity).

## Predictions

### P1 — Process effectiveness
`optimized` beats `original` on mean makespan in **≥ 60%** of the 30 ensemble
networks (≥ 18 / 30 show `mean_opt < mean_orig`). Fraction-based, scale-independent.

- REPRO if ≥ 60%; PARTIAL if 50–60%; MISS if < 50%.

### P2 — Null-gate (central refutation test)
Mean `optimized` makespan beats mean `null` AND mean `original` by **≥ 1.0 tick**
(the `CoordNullGate` margin) — i.e. `CoordNullGate.judge(...)` **passes**
("not refuted").

- REPRO if the gate passes; MISS otherwise (the method "just adds edges, not the
  *right* edges").

### P3 — Consistency (the headline divergence)
`corr(static_efficiency_gain, makespan_gain)` across the 30 networks is
**> 0 and < 0.9** (positive but imperfect), **AND** at least **1 counterexample**
exists (a network where `static_gain > 0` but `makespan_gain < 0` — static
efficiency rose yet the simulated process got worse). With overload now biting,
the counterexample is *mechanistically possible*; whether it actually emerges is
an open empirical question reported honestly.

- REPRO if both clauses hold; PARTIAL if exactly one; MISS if neither.

### P4 — Phase ranking
Makespan-gain / completion-tick contribution is **reported** and compared to DOC
A's static phase ranking (监测预警 7.97% > 处置救援 3.45% > 事后恢复 1.77%).
v2 still uses a single combined 9-task DAG, so P4 is **"reported, not pass/fail"**;
any divergence from DOC A's static ranking is noted honestly.

- REPORTED (always).

### P5 — CEI validation
Removing (isolating) the **top-CEI** department raises mean makespan **more** than
removing a **median-CEI** department, averaged over the ensemble.

- REPRO if top-CEI removal degrades makespan more; MISS otherwise.

## Sensitivity analysis (mandatory — params uncalibrated)

A sensitivity pass over `capacity` and `failure_prob` (±50%) records whether the
**P1** and **P2** verdicts hold. Robustness check, not a tuning loop — the locked
thresholds are not changed by its outcome.

## Honest scope (binds every output)

Synthetic representative ensemble — **not** any real province. Agent parameters
(capacity / delay / failure / task-rate) are **not** empirically calibrated; they
were set to make the mechanism *functional* (baseline completes; overload occurs),
not to match real coordination dynamics. The claim is **method-mechanism
validity**, not real-world response prediction. This study *motivates* collecting
real department-coordination networks for a future exact validation. There is NO
real network data.
