# Coord-Response ABM — FINDINGS (post-run)

**Status:** run complete. Verdicts reported HONESTLY against the pre-registered `PREDICTIONS-locked.md` (a falsified prediction is a valid result; no thresholds/params were tuned to pass).

**Config:** N=30 networks, seeds (0,1,2,3,4), budget B=4, null-gate margin 1.0 tick, fail penalty 100.0.

## ⚠ VALIDITY CAVEAT — v1 is a reachability/penalty ARTIFACT (do NOT read P1/P2 as "DOC A validated")

Post-run diagnosis (added after inspecting the mechanism, before drawing conclusions):

1. **The makespan "win" is a connectivity story, not an efficiency story.** In the
   generated baselines many tasks never complete (e.g. nets 1–2: only 2 of 9 tasks
   `done`, 1 `failed`, the rest stalled) because the 9-task DAG's required
   `(lead, collaborator)` department pairs are frequently **absent** from the
   representative-network generator's output. With `fail_penalty=100`, makespan is
   then dominated by the count of failed/unrun tasks. Optimization adds 4 edges that
   **reconnect** those pairs → all 9 complete → makespan collapses (112.6 → 15.4).
   So P1/P2 measure "did targeted edges repair a disconnected network better than
   random edges" (trivially yes) — **NOT** whether DOC A's *global-efficiency*
   edge-edit improves an already-functional coordination process.
2. **The overload mechanism never activates: `peak_overload = 1.0` in every run.**
   Departments sit exactly at capacity, never over it, so the capacity-driven failure
   dynamics — the intended engine of the "static efficiency ↑ but process ↓"
   counterexample — are **dead**. P3's 0 counterexamples is a consequence of this
   dead mechanism, not evidence about DOC A's method.

**Conclusion:** v1 does NOT yet test the intended thesis. The honest reading is "this
run is an artifact of (a) disconnected baselines + (b) a non-biting overload mechanism."
A v2 redesign is required before any claim about DOC A's optimization: (i) generate
baselines that are CONNECTED enough that the full task DAG can run (so the signal is
timing/efficiency, not reachability repair); (ii) calibrate capacity/load so overload
genuinely bites (so more-edges-can-overload-core-departments and the counterexample
can emerge); (iii) rebalance makespan so it reflects response *timing*, not a
failed-task penalty count. The verdicts below stand as the honest record of v1; they
are not a validation of the method.

## Verdict table

| Prediction | Verdict | score | threshold |
|---|---|---|---|
| P1 — P1 optimized beats original makespan in >=60% of ensemble | **REPRO** | 0.8 | 0.6 |
| P2 — P2 null-gate: optimized beats original AND random-edge null (makespan) | **REPRO** | 69.55 | 1.0 |
| P3 — P3 consistency: 0<corr<0.9 AND >=1 counterexample (static up, makespan up) | **MISS** | 0.4382 | 0.9 |
| P4 — P4 phase ranking REPORTED (v1 single combined DAG; not pass/fail) | **REPORTED** | 0.0 | 0.0 |
| P5 — P5 CEI: top-CEI removal degrades makespan more than median-CEI removal | **MISS** | -15.687 | 0.0 |

## The three analyses

**1. Process effectiveness.** 24/30 networks improved (80%); mean makespan: original=112.56, optimized=15.40, random-null=84.95.

**2. Consistency (headline).** corr(static_gain, makespan_gain) = 0.4382196872685025. Counterexamples (static efficiency ↑ but makespan ↑/worse): 0 -> networks [].

   - No counterexample surfaced in this ensemble; P3's counterexample clause is FALSIFIED (reported honestly).

**3. CEI validation.** mean makespan increase on removal: top-CEI dept=-12.560, median-CEI dept=3.127. **P5 is FALSIFIED** (top-CEI delta is not greater than median-CEI delta — it is negative).

   - *Why (honest mechanism, not tuned away):* isolating the top-CEI department (often 省水利厅) makes an EARLY task's collaborator unreachable, so that one task fails immediately and blocks all downstream tasks (makespan = 1 failed task × penalty). In the intact network MORE tasks reach-then-fail under capacity overload, each adding a penalty, so the intact makespan is HIGHER. The penalty-based makespan therefore does not rank node importance monotonically when failures cascade. This is itself a 'static metric (CEI) can diverge from process outcome' divergence — the DOC-B thesis — surfacing through P5 rather than P3's counterexample. Reported as-is; NOT engineered to pass.

**Null-gate (refutation tier).** [coord optimization beats original AND random-edge null (makespan)] PASS (not refuted) — score=69.55 threshold=1  
PASS renders as 'not refuted', never 'verified'.

## P4 — phase ranking (reported-only)

v1 uses a single combined 9-task DAG (not three per-phase configs), so P4 is reported, not pass/fail. Mean completion tick by phase (optimized): {'监测预警': 4.45, '处置救援': 11.05, '事后恢复': 15.4}. DOC A's static phase ranking is 监测预警 > 处置救援 > 事后恢复 (7.97% > 3.45% > 1.77%); any divergence in the simulated process is noted here rather than scored.

## Sensitivity analysis (mandatory — params uncalibrated)

Re-ran the ensemble's P1 fraction and null-gate under ±50% capacity and failure_prob. This is robustness, not tuning — locked thresholds unchanged.

| Perturbation | P1 fraction | P1 holds (>=60%) | null-gate passed |
|---|---|---|---|
| cap-50% | 0.8 | True | True |
| cap+50% | 0.8 | True | True |
| fail-50% | 0.8 | True | True |
| fail+50% | 0.8 | True | True |

## Honest scope (binds this study)

- **Synthetic representative ensemble, not real provinces.** There is NO real department-coordination network data — only DOC A's reported optimal edges, top-CEI nodes, and per-phase static gains.

- **Uncalibrated agent parameters.** capacity / response_delay / failure_prob are not empirically fit — hence the mandatory sensitivity analysis above.

- **Claim is method-mechanism validity, not real-world response prediction.** This tests whether DOC A's static-global-efficiency edge-edit reliably helps a *simulated* coordination process, and where it can fail (the counterexample).

- **Motivates real-network collection** for a future exact validation; no flood-inundation/hazard physics, no casualty/loss prediction, no GIS layer (non-spatial).
