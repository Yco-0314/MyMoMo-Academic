# Coord-Response ABM — PREDICTIONS (locked v3, agent-based redesign)

**Locked: 2026-06-28, BEFORE running the v3 ensemble experiment.** No P1–P5 outcome
(makespan_gain / correlation / counterexamples / CEI deltas) has been observed at lock
time. Thresholds are **reused verbatim from `PREDICTIONS-locked-v2.md`** — none were
invented or shifted for v3 (anti-tuning: same pre-registered bar, new mechanism).

## What changed in v3 (and why a re-lock is honest, not outcome-shopping)

v3 replaces v2's central two-pass god-loop with a genuine agent-based model:
autonomous `DepartmentAgent.step()` (receive→decide→act) on the neutral ABM platform
(`abm_auto._platform`: `AgentSet` scheduler + `DataCollector`). Activation propagates
agent-to-agent over the topology, per task from its own lead, so a shared
collaborator's concurrent coordination load is **emergent and edge-responsive** — the
channel v2 structurally lacked (v2's `peak_overload` was the treatment-invariant
constant 1.875). The re-lock follows a *mechanism* change verified outcome-blind, not
an outcome-convenient threshold shift.

## Mechanism functionality — VERIFIED outcome-blind before lock (independent probe)

Over 12 representative networks (seed 0), `peak_overload` per treatment
(original / `optimize_edges` / `add_random_edges`):

- **Load varies by treatment on 7/12 networks** at the default `coord_window=2`
  (≥30% target met); on every network where it varies, **optimized ≥ original**.
- **Direction is robust across the `coord_window` knob:** variation exists at W=1
  (2/12), W=2 (7/12), W=3 (3/12) — it is NOT a single-W knife-edge — and on every
  differing network at every W, optimized ≥ original. The window sets the operating
  point (W=1 under-saturates, W=3 over-saturates a 3-collaborator hub); it does not
  manufacture the channel or flip its direction.
- Original baselines complete all 9 tasks (0 non-done over nets 0–11 × seeds 0–4).
- Deterministic (same seed → identical run dict).

**Honest channel caveat (binds the verdicts):** at this 9-task DAG scale
`peak_overload` is **binary** — it takes only 1.25 (2 coordination windows collide at
a non-hub, 2/1.6) or 1.875 (3 collide, 3/1.6). The load channel is real and
edge-responsive but **coarse (2-state)**; its *magnitude* is `coord_window`-dependent
(direction is not). Interpret P3's correlation accordingly (a near-binary regressor).

## Locked predictions

| # | Prediction | Pass threshold (= v2) |
|---|---|---|
| **P1** | Optimized beats original makespan in **≥60%** of the ensemble. | fraction ≥ 0.60 |
| **P2** | Null-gate (refutation tier): optimized beats BOTH original AND the random-edge null on mean makespan by the locked margin. | margin ≥ 1.0 tick |
| **P3** | Consistency **AND** divergence: `0 < corr(static_gain, makespan_gain) < 0.9` **AND ≥1 counterexample** (a network where static efficiency ↑ but makespan ↑ = worse). | corr in (0, 0.9) AND #counterexamples ≥ 1 |
| **P4** | Phase completion ranking REPORTED (single combined DAG; not pass/fail). | reported-only |
| **P5** | CEI validity: removing the **top-CEI** department degrades makespan **more** than removing a **median-CEI** department (on the fixed `n_nondone` makespan metric). | top-CEI Δ > median-CEI Δ |

## Theory being tested (direction stated before the run)

- **P1/P2 (method works):** DOC A's static-global-efficiency edge selection shortens
  coordination info-delay → earlier task starts → lower makespan, beating both the
  original and a random-edge null. *Now genuinely falsifiable in v3:* the verified load
  channel shows optimization also RAISES hub overload, which can throttle/worsen
  makespan — so P1/P2 are no longer pass-by-construction. If the load channel dominates
  on enough networks, P1/P2 can FAIL (a valid, interesting result).
- **P3 (divergence — the v3 raison d'être):** static efficiency gains should NOT map
  perfectly to process gains (`corr < 0.9`) and there should exist **≥1 counterexample**
  where statically-good edges concentrate coordination load at a shared hub enough to
  make makespan WORSE. This is mechanistically possible in v3 (optimization raises peak
  overload on 7/12 nets); whether the raised overload overturns the timing gain in NET
  makespan on any network is the empirical question we now find out.
- **P5 (CEI validity):** removing a high-CEI (coordination-efficiency-index) department
  should hurt makespan more than removing a median one — CEI identifies critical
  coordinators. Tested on the corrected pending-aware makespan metric (the v2 bug that
  inverted P5 is fixed).

## Binding discipline

- A falsified prediction is a VALID result; report REPRO/MISS honestly.
- No threshold or model parameter (capacity, task_rate, failure slope, `coord_window`)
  will be changed after seeing the P-outcomes. Calibration was to mechanism
  functionality only (verified above), never to a cross-treatment outcome.
- Mandatory sensitivity analysis (params uncalibrated), INCLUDING a `coord_window`
  sweep (W=1/2/3) on the headline verdicts — since W is the load channel's operating
  point, the verdicts' robustness to it must be reported.
- Claim is method-mechanism validity on a SYNTHETIC ensemble (no real coordination
  network data), not real-world response prediction.
