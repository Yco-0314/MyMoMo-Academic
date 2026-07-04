# Coord-Response ABM — FINDINGS v2 (post-run)

**Status:** v2 run complete. Verdicts reported HONESTLY against the pre-registered `PREDICTIONS-locked-v2.md` (a falsified prediction is a valid result; no thresholds/params were tuned to pass). The mechanism was calibrated OUTCOME-BLIND (baseline completion + overload verified via single-treatment diagnostics before re-locking).

**Config:** N=30 networks, seeds (0,1,2,3,4), budget B=4, null-gate margin 1.0 tick, fail penalty 30.0 (timing-driven).

## v1 artifact caveat (why v2 exists)

v1 (`FINDINGS.md`, `PREDICTIONS-locked.md`) was invalidated by two mechanism artifacts: (A) generated baselines were missing required (lead,collaborator) DAG edges → tasks failed/stalled → the 100× failed-task penalty dominated makespan; (B) peak_overload was capped at 1.0 everywhere → the overload mechanism (the counterexample engine) never activated. v1's P3/P5 falsifications were therefore artifacts, not findings. v2 repairs both and re-locks predictions. The v1 docs are kept for provenance.

## Mechanism functionality (proof the v2 fixes work)

- ORIGINAL baseline non-done tasks across all 150 original runs: **0** (target 0 → baselines complete all 9 tasks).

- peak_overload min/mean/max = 1.875 / 1.875 / 1.875; fraction of runs with overload>1.0 = **100%** (overload now occurs — but see the audit caveat below: it is a non-discriminating constant).

## ⚠ Post-run adversarial audit (2026-06-28) — what v2 does and does NOT show

A 23-agent adversarial audit (verdicts independently reproduced) found that the "overload now genuinely bites" framing above OVER-CLAIMS, and a metric bug inverted P5. Honest correction:

1. **Overload is a treatment- AND network-INVARIANT constant (exactly 1.875 in 100% of runs — original = optimized = random, every network, every seed).** `1.875 = (3 concurrent tasks × rate 1.0) / non-hub capacity 1.6` — a structural ceiling of the fixed 9-task DAG, **not** a dynamic outcome. Root cause: three phase-2 tasks share collaborator 省交通运输厅 and the same `needs=['预警发布']`, so they co-activate every tick regardless of topology; **edges shift only WHEN the peak occurs, never its magnitude.** Infinite-capacity ablation barely changes the optimization gain (3.69→3.95). So **the "more edges → overload → worse" counterexample channel is structurally ABSENT** — P3's 0 counterexamples reflects that, NOT a clean empirical null.
2. **makespan had a pending-blindness BUG (now fixed in code: `n_failed → n_nondone`, `_metrics.py`).** It counted only `failed` tasks, so a total DAG collapse (one early failure stalling everything downstream as `pending`) scored as a *fast* finish. **This inverted P5**: isolating the most-central dept caused a cascade scored as makespan 30 (< a healthy 9/9 finish at 43). The verdict table below was computed on the BUGGY metric; with the fix, removing the most-central dept correctly registers the cascade as costly and **P5's direction flips** (a corrected re-run is the next step). Note: corrected-P5 "importance" is then a *reachability/cascade* effect, not an overload effect.
3. **P1/P2 are a NARROW, SOUND result — a timing effect, not the full thesis.** Optimized beats original/random because DOC A's edge selection shortens coordination info-delay (`1/w`) → earlier task starts → lower makespan (baselines complete 9/9, so the penalty never contaminates it). BUT the positive predictions **cannot fail by construction** (there is no working counterforce), so they validate only "static-efficiency edge-selection yields a faster deterministic schedule than original or random edges in a fixed synthetic DAG."
4. **P3 corr≈0 is real but mis-attributed:** its cause is that the optimizer normalizes every network to nearly the same finish-line floor (corr(orig_makespan, makespan_gain)=0.79), **not** a static-vs-process divergence via overload.
5. **The re-lock discipline held** (v2/v2.1/v2.2 thresholds identical; re-locks followed real mechanism fixes, not outcome-convenient shifts) — independently confirmed.

**Bottom line:** v2's number tables are honest, but its narrative oversells. The defensible contribution is the **timing result (P1/P2)**; the **divergence thesis (P3/P5) is NOT-YET-TESTABLE** in this model (overload channel structurally absent + the now-fixed metric bug). Testing it needs a v3 where department LOAD is edge-responsive (adding edges can raise a dept's peak concurrency).

## Verdict table

| Prediction | Verdict | score | threshold |
|---|---|---|---|
| P1 — P1 optimized beats original makespan in >=60% of ensemble | **REPRO** | 1.0 | 0.6 |
| P2 — P2 null-gate: optimized beats original AND random-edge null (makespan) | **REPRO** | 1.84 | 1.0 |
| P3 — P3 consistency: 0<corr<0.9 AND >=1 counterexample (static up, makespan up) | **MISS** | -0.0001 | 0.9 |
| P4 — P4 phase ranking REPORTED (v2 single combined DAG; not pass/fail) | **REPORTED** | 0.0 | 0.0 |
| P5 — P5 CEI: top-CEI removal degrades makespan more than median-CEI removal | **MISS** | -21.673 | 0.0 |

## The three analyses

**1. Process effectiveness.** 30/30 networks improved (100%); mean makespan: original=41.23, optimized=37.99, random-null=39.83.

**2. Consistency (headline).** corr(static_gain, makespan_gain) = -8.638637815278217e-05. Counterexamples (static efficiency ↑ but makespan ↑/worse): 0 -> networks [].

   - No counterexample surfaced in this ensemble; P3's counterexample clause is FALSIFIED (reported honestly — the overload penalty did not, in aggregate, overturn the timing gain on any single network at B=4).

**3. CEI validation.** mean makespan increase on removal: top-CEI dept=-10.000, median-CEI dept=11.673. **P5 FALSIFIED** (top-CEI delta <= median-CEI delta).

**Null-gate (refutation tier).** [coord optimization beats original AND random-edge null (makespan)] PASS (not refuted) — score=1.84 threshold=1  
PASS renders as 'not refuted', never 'verified'.

## P4 — phase ranking (reported-only)

v2 uses a single combined 9-task DAG (not three per-phase configs), so P4 is reported, not pass/fail. Mean completion tick by phase (optimized): {'监测预警': 12.35, '处置救援': 30.78, '事后恢复': 37.99}. DOC A's static phase ranking is 监测预警 > 处置救援 > 事后恢复 (7.97% > 3.45% > 1.77%); the simulated completion order follows the DAG phases (monitoring earliest, recovery latest) — noted here rather than scored.

## Sensitivity analysis (mandatory — params uncalibrated)

Re-ran the ensemble's P1 fraction and null-gate under ±50% capacity and failure_prob (scaled from the v2 hub/non-hub defaults). This is robustness, not tuning — locked thresholds unchanged.

| Perturbation | P1 fraction | P1 holds (>=60%) | null-gate passed |
|---|---|---|---|
| cap-50% | 0.967 | True | True |
| cap+50% | 0.967 | True | True |
| fail-50% | 1.0 | True | True |
| fail+50% | 1.0 | True | True |

## Honest scope (binds this study)

- **Synthetic representative ensemble, not real provinces.** There is NO real department-coordination network data — only DOC A's reported optimal edges, top-CEI nodes, and per-phase static gains.

- **Uncalibrated agent parameters.** capacity / response_delay / failure_prob / task-rate are not empirically fit — they were set to make the mechanism *functional* (baseline completes; overload occurs), not to match real dynamics — hence the mandatory sensitivity analysis.

- **Claim is method-mechanism validity, not real-world response prediction.** This tests whether DOC A's static-global-efficiency edge-edit reliably helps a *simulated* coordination process, and where it can fail (the counterexample).

- **Motivates real-network collection** for a future exact validation; no flood-inundation/hazard physics, no casualty/loss prediction, no GIS layer (non-spatial).
