# 协同响应验证 ABM — 设计 (coord-response ABM)

**Date:** 2026-06-28
**Status:** Approved (brainstorming) — ready for implementation plan
**Area:** new additive package `abm_auto/coord/` in the private fork (non-spatial; base-engine untouched) + a runner + locked-prediction/findings docs. **Intent:** originate (the user's own research; DOC A/B by 唐毅/黄艳秋, 应急管理大学).

## Problem & positioning

DOC A optimizes provincial flood-plan department **coordination networks** for **static global efficiency** via budgeted edge-editing (CEI-constrained), reporting per-phase gains (monitoring-warning 7.97% / response 3.45% / recovery 1.77%). DOC B sketches an ABM to test whether that optimization actually helps the **response process**.

**Hard constraint: there is NO real network data** (only DOC A's *reported* optimal edges + top-CEI nodes + phase gains). Therefore this ABM is **NOT** an empirical prediction of any real province. It is a **methodological / mechanism-validation study**:

> Does the "edge-edit for static global efficiency" method (DOC A's approach) reliably improve a **simulated** coordination response on **representative** department-coordination networks — and in what regimes (department overload, off-critical-path edges) does higher static efficiency **fail** to translate into process gains?

This directly serves DOC B's **"文本合规 → 预案有效"** thesis: demonstrate that static network metrics can **diverge** from process effectiveness, hence process simulation is needed. The study delivers BOTH (a) a mechanism-validation ensemble result AND (b) a **counterexample** (a network where static efficiency ↑ but process ↓) — both from one engine; the counterexample is a finding the ensemble surfaces / a deliberately-constructed instance the same engine runs.

**Honest scope (written into every output):** synthetic representative ensemble, not real provinces; agent parameters (capacity/delay/failure) are not empirically calibrated (→ mandatory sensitivity analysis); the claim is method-mechanism validity, not real-world response prediction; the study *motivates* collecting real networks for a future exact validation.

## Architecture — engine (tick-based agent simulation)

Chosen over discrete-event / analytical queueing because finite-capacity **overload and failure dynamics** (the source of the counterexample) emerge most naturally and transparently in a per-tick agent loop, and it is the most ABM-native + gate-friendly fit for mymomo.

`abm_auto/coord/` (new package):
- `_network.py` — the coordination network value object + the **representative-network generator** (the ensemble source) + the **treatment operators** (DOC-A-style global-efficiency edge-edit; random-edge-addition null; identity/original) + static metrics (global efficiency, CEI) for the consistency comparison.
- `_model.py` — the tick-based simulation: `Department` agent, `Task` (DAG node), `Scenario` (event timeline), and the `CoordModel` tick loop. Deterministic given a seed.
- `_metrics.py` — outcome extraction: makespan (primary), critical-task completion rate, peak department overload.
- `_gate.py` — the null-gate (refutation tier, mirrors the existing gate protocol): the optimized treatment must beat BOTH the original AND the random-edge null on makespan; a synthetic self_test.
- `_experiment.py` — the ensemble × treatment × scenario × seed runner producing a tidy results table + the three analyses.

### Objects & mechanism

**Department agent** (~15 depts from DOC B: 应急管理厅, 水利厅, 气象局, 公安厅, 交通运输厅, 住建厅, 农业农村厅, 民政厅, 商务厅, 通信管理局, 粮食物资储备局, 国网电力, 铁路部门, 红十字会, 消防救援): `capacity` (work units/tick), `current_load`, `response_delay`, `resources`, `coordination_neighbors` (from the network), `failure_prob` (rises with overload / comms-cut), `priority`.

**Task DAG** (9 tasks across the 3 phases; lead + collaborators per DOC B's table; each has a work amount + phase + a trigger condition):
1. 降雨监测 — lead 气象局; collab 水利厅, 应急管理厅 (监测预警)
2. 水情研判 — lead 水利厅; collab 气象局, 应急管理厅 (监测预警) — needs (1)
3. 会商决策 — lead 应急管理厅; collab 水利厅, 气象局, 交通运输厅, 公安厅 (监测预警) — needs (2)
4. 预警发布 — lead 气象局/应急管理厅; collab 通信管理局, 公安厅 (监测预警) — needs (3)
5. 交通管控准备 — lead 公安厅; collab 交通运输厅, 铁路部门 (处置救援) — needs (4)
6. 群众转移 — lead 民政厅; collab 公安厅, 交通运输厅 (处置救援) — needs (4)
7. 抢险救援 — lead 消防救援; collab 水利厅, 应急管理厅 (处置救援) — needs (4)
8. 物资保障 — lead 粮食物资储备局; collab 商务厅, 交通运输厅 (处置救援) — needs (4)
9. 事后恢复 — lead 民政厅; collab 商务厅, 国网电力, 公安厅 (事后恢复) — needs (6,7)

**Scenario:** a flood timeline emitting events at set ticks (rainfall↑ triggers task 1; water-level threshold triggers the response cluster; optional road/comms cut temporarily disables specific edges, raising failure_prob). A small set of scenarios (e.g. moderate / severe / severe-with-comms-cut).

**Tick loop:** scenario emits events → triggered tasks become eligible → a task **starts** only when its lead has received info (info propagates along edges with **delay ∝ 1/w**, matching DOC A's `l_ij = 1/w_ij`) AND its collaborators are reachable via coordination edges → the task progresses at a rate limited by the available capacity of lead+collaborators → overloaded depts have higher `failure_prob` (failed task-steps retry, costing time) → task completes when work is done → record per-task completion tick. Stop when all reachable tasks are done/failed or a max-tick cap.

## The experiment

For each **ensemble network** (N representative instances) × **scenario** × **seed**, run three **treatments**:
- `original` — the base network.
- `optimized` — DOC-A-style: add the B edges that maximize static global efficiency under the CEI constraint (核心统筹节点 应急管理厅 CEI not weakened).
- `null` — add B **random** edges (and a degree-preserving-rewire variant) — the anti-fabrication control.

**Outcomes:** makespan (primary), critical-task completion rate, peak department overload.

### Three analyses (one engine)
1. **Process effectiveness:** optimized vs original makespan across the ensemble.
2. **Consistency (headline):** does each network's **static** global-efficiency gain correlate with its **process** makespan gain? Is the correlation positive but imperfect (<1)? Across the 3 phase-configs, does the process-gain phase-ranking match DOC A's static ranking (warning > response > recovery)?
3. **CEI validation:** removing a high-CEI department from the simulation degrades makespan most? (process-level node importance vs static CEI rank.)
4. **Counterexample:** identify (or construct) an instance where static efficiency ↑ but makespan ↑ (process worse) — the "static metric misleads" existence proof.

### ⭐ Null-gate (refutation tier, the命门)
`optimized` must beat **both** `original` AND `null` (random edges) on makespan, by a pre-registered margin, in a pre-registered fraction of the ensemble. If `optimized ≈ null` → the finding is "the method just adds edges, not the *right* edges" — recorded honestly (PASS = "not refuted", never "verified"). `self_test`: a synthetic network where a deliberately-good edge beats a random edge (gate must fire correctly), deterministic, no data.

## Locked predictions (mymomo discipline — commit BEFORE running)

Written to `docs/studies/coord-response/PREDICTIONS-locked.md` and committed before any experiment run. Draft targets (final numbers locked in the plan/just-before-run):
- **P1:** `optimized` reduces makespan vs `original` in ≥ a locked fraction of ensemble instances.
- **P2 (null-gate):** `optimized` beats `null` (random edges) on mean makespan by a locked margin; if not, the method is not edge-*selection*-specific.
- **P3 (consistency):** static-efficiency gain ↔ makespan gain correlation is **positive but < 1** (imperfect), AND **at least one counterexample exists** (static ↑, makespan ↑).
- **P4 (phase ranking):** the process-gain ranking across the 3 phase-configs matches DOC A's static ranking (warning > response > recovery) — or is honestly reported as diverging.
- **P5 (CEI):** removing the top-CEI department degrades makespan more than removing a median-CEI department.

Each becomes a refutation-tier Verdict (REPRO/PARTIAL/MISS-style), reported honestly even if falsified.

## mymomo integration & outputs

- Engine is deterministic + seeded; the runner emits a tidy results table + the analyses + an L3 verdict bundle (`abm_auto/gis/_repro_bundle.py` is reusable — it is network-agnostic; carry ODD + citations).
- Gates: the **null-gate** (central), plus a sensitivity analysis (capacity/delay/failure are uncalibrated → SA is mandatory, surfaced in the report).
- `docs/studies/coord-response/`: `PREDICTIONS-locked.md` (pre-run), `FINDINGS.md` (post-run, with the honest-scope section), `verdict-bundle.json`.

## Error handling
- A network where a task's collaborators are unreachable → that task is recorded as **failed** (not a crash); makespan uses completed-task times + a penalty for failed critical tasks (penalty pre-registered).
- Empty/degenerate ensemble instance → skipped with a logged count.
- The optimized edge-edit having no feasible improvement under the CEI constraint → that instance contributes a 0% static gain (valid data point), not an error.

## Testing (deterministic, no real data, no live LLM)
- `_model.py`: tick loop determinism (same seed → same makespan); info-delay ∝ 1/w; a task waits when a collaborator is unreachable; overload raises failure_prob → longer makespan; a tiny hand-built network golden.
- `_network.py`: generator produces valid weighted networks with the hub structure; the optimized edge-edit raises static global efficiency; the random null adds B edges.
- `_metrics.py`: makespan / completion-rate / peak-overload on a known tiny run.
- `_gate.py`: null-gate self_test (good edge beats random → gate fires correctly); on a synthetic case where optimized ties random → gate refutes.
- `_experiment.py`: a small ensemble (e.g. N=5) runs end-to-end producing the results table + the four analyses without error.

## Non-goals
- No flood-inundation / hazard physics, no casualty/loss prediction (DOC B is explicit).
- No claim about any real province (no real network/response data).
- No GIS/spatial layer (this is a non-spatial coordination-process model).
- No editing of base-engine paths (`abm_auto/pipeline`, `abm_auto/agents`) — `abm_auto/coord/` is purely additive.

## Where it lives
- `abm_auto/coord/` (engine: `_network`, `_model`, `_metrics`, `_gate`, `_experiment`), `tests/coord/`, `examples/coord_response/run.py`, `docs/studies/coord-response/` (locked predictions + findings + bundle). Private fork, branch `feat/coord-response-abm` off `main`.
