# Coord-Response ABM v3 — Genuine Agent-Based Redesign (design)

**Date:** 2026-06-28
**Amends:** `2026-06-28-coord-response-abm-design.md` (v1/v2 design).
**Why this exists:** two independent observations converged on the same root cause.

1. **"It doesn't look like an ABM."** v2's `CoordModel.run()` is a central two-pass
   *god-loop*: departments are passive load-buckets, tasks are processed in a global
   loop. No autonomous agents, no `step()`, no scheduler, no collector — and it does
   not ride mymomo's platform layer (`GISAgent`/`AgentSet`/`DataCollector`). It is a
   task-DAG scheduler dressed as agents.
2. **The 23-agent adversarial audit (2026-06-28)** found `peak_overload` is a
   treatment- AND network-INVARIANT constant (exactly 1.875 everywhere). The
   "more edges → overload → worse" counterexample channel is **structurally absent**:
   the three phase-2 tasks co-activate every tick regardless of topology, so edges
   shift only *when* the peak occurs, never its magnitude.

Both are the **same root cause**: load is not emergent from autonomous agents, so it
cannot respond to the network. Making the model genuinely agent-based and making the
counterexample mechanistically testable are therefore **one move** — this redesign.

---

## Goal

Rebuild the coordination model as a genuine agent-based model (autonomous
`DepartmentAgent.step()` on the platform scheduler + collector) in which a
department's per-tick **load is emergent and edge-responsive** — adding edges can
*raise* a department's peak concurrency — so the static↑/process↓ divergence
thesis (P3/P5) becomes empirically testable rather than structurally impossible.

This is **calibration to mechanism-functionality, not to outcome.** Success of the
*build* is "load now varies with topology" (an outcome-blind property). Whether the
counterexample actually occurs is then an empirical question we **lock and find out** —
never tune toward.

---

## Architecture

### 1. Promote the platform to a neutral, dep-light module

`abm_auto/gis/_platform.py` is already 100% domain-agnostic ("Mesa's shape, not its
code" — only `random`+`typing`). The single obstacle to reuse is that importing
`abm_auto.gis._platform` runs `gis/__init__.py`, which eagerly pulls `rasterio`/
`pyproj`. A non-spatial package must not inherit heavy GIS deps.

**Move** the generic core to a new neutral module `abm_auto/_platform.py`:
`Agent`, `AgentSet`, `DataCollector`, `RunReporter`, `AgentModel`, `StagedAgentModel`
(verbatim logic; neutral names).

**Re-export shim** in `gis/_platform.py` (behavior-identical — gis tests stay green):

```python
from abm_auto._platform import (
    Agent as GISAgent, AgentSet, DataCollector, RunReporter,
    AgentModel as GISModel, StagedAgentModel as StagedGISModel,
)
```

The GIS reference adapter (`ContagionAgent`/`ContagionModel`/`contagion_gate`/
`_IsolatedContagionModel`) stays in `gis/_platform.py` (it is the GIS adapter #1).
`coord/` imports the neutral names from `abm_auto._platform` → no rasterio, clean
names, one shared implementation. This also *proves the cross-domain platform thesis*
(the same agent floor rides gis contagion AND coord; later closed extensions), the same
"promote-to-shared-base" pattern already flagged for the repro bundle.

Cut marker: `# ponytail: kept GIS-name aliases in gis/_platform.py so existing gis
code/tests are untouched; upgrade path = rename gis subclasses to the neutral names.`

### 2. The agents

`DepartmentAgent(Agent)` — one per network node. Local state only:
- `name`, `capacity` (hub vs non-hub, from `_HUBS`), `failure_prob`
- `inbox`: activation signals that have arrived (task_name → first-arrival tick)
- `load`: work committed THIS tick (reset each tick) — **emergent**, MAY exceed capacity

`step()` (local rules, no global view):
1. **Receive** — drain newly-arrived activation signals into `inbox`.
2. **Decide** — actionable tasks = tasks it leads or collaborates on whose `needs`
   are done AND whose activation signal has reached it. Demand = Σ rate over
   actionable tasks → `load`. If `load > capacity` → overload → throttle all its
   tasks' effective progress by `load/capacity`, and elevate failure prob.
3. **Act** — apply throttled progress to each actionable task it touches.
4. **Signal** — when it (as lead) starts/advances a task, emit activation signals to
   that task's collaborators and to dependent tasks' leads, propagating over edges.

### 3. Network-gated activation propagation (the edge-responsive channel)

Activation arrival depends on the *actual paths through the current edge set*: a
signal from `u` toward `v` is delayed by the least-latency path, each edge of weight
`w` costing `ceil(1/w)` ticks (heavier edge → arrives sooner).

> **Implementation note (as-shipped reconciliation, audit 2026-06-28):** the design
> above sketched per-agent hop-by-hop relay (and listed a 4th "Signal" agent stage in
> §2). The shipped model instead computes arrivals **centrally** — the environment runs
> a Dijkstra over the current topology each tick into a model-owned message bus that
> agents only READ (stages are `receive`/`decide`/`act`; there is no separate "Signal"
> stage). This is **distributed-equivalent and leak-free** (arrivals are numerically
> identical to faithful per-agent relay; an agent still acts only on its local inbox),
> and it is simpler/deterministic. Treat the "agent-to-agent / not a single global
> shortest-path" phrasing as superseded by this note; the agents remain autonomous, but
> message *delivery timing* is an environment computation, not a literal relay.

**Why load is now edge-responsive (the mechanism):** a shared collaborator (e.g.
`省交通运输厅`) co-works task X only once X's activation has *arrived*. The arrival
ticks of several tasks' signals at that hub depend on path lengths from each task's
lead. Adding edges (optimization) shortens some paths more than others → can pull
multiple arrivals into the **same tick window** at the hub → peak concurrency RISES →
overload → that hub's tasks slow → makespan can WORSEN even as static efficiency
rises. On other networks the added edges *stagger* arrivals → load falls. Peak load
is now an emergent function of topology — it **varies by treatment**. This is exactly
the channel v2 lacked (v2 synchronized the three tasks by construction).

This requires the task set to have **heterogeneous leads at different network
distances from the shared hub** so topology differentially shifts their arrivals;
the v2 default DAG (three phase-2 tasks sharing one lead-structure) must be relaxed
so arrivals are not structurally simultaneous. (If the existing `default_tasks`
already has distinct leads, only the activation mechanism changes; the implementer
verifies and adjusts the DAG minimally if needed — documented as a mechanism change,
not an outcome tune.)

### 4. Interface-preservation contract (keep downstream + tests working)

The model's *public surface* is unchanged so `_metrics.py`, `_experiment.py`,
`_gate.py`, and interface-level tests keep working:

- `CoordModel(net, tasks, scenario, *, seed, ...)` constructor signature preserved
  (now builds `DepartmentAgent`s on an `AgentSet` + `DataCollector` internally;
  `CoordModel` becomes a `StagedAgentModel` or composes one).
- `.run() -> dict` returns the **same shape**:
  `{task_name: {"status", "start_tick", "done_tick"}, "_peak_overload": float}`.
  `_peak_overload` is now derived from the collector's per-tick per-dept load series
  (max over ticks over depts of `load/capacity`) — emergent, not a tracked scalar.
- `Task`, `Scenario` dataclasses unchanged. `Department` stays importable (config or
  the agent) — `tests/coord/test_model.py` imports `Department, Task, Scenario,
  CoordModel`.
- `peak_overload(res)` in `_metrics.py` stays a passthrough of `res["_peak_overload"]`
  (no change); the model populates it from emergent load.

### 5. Error handling / determinism

- Deterministic given a seed (one seeded RNG on the model, threaded to agents) —
  `test_deterministic_same_seed_same_result` must still pass.
- Unreachable collaborator (no path) → the task's activation never arrives → task
  ends non-`done` (`failed`/`pending`) → penalized by the fixed makespan metric.
  `test_unreachable_collaborator_fails_task` must still pass.
- `MAX_TICKS` cap retained as a safety bound.

---

## Testing

Keep all **interface-level** coord tests green (deterministic, completes-and-records,
unreachable-fails, higher-weight-starts-sooner, baseline-completes). Change the
mechanism tests to the v3 truth:

- **Flip** `test_overload_occurs_but_is_treatment_invariant_KNOWN_LIMITATION` →
  `test_load_is_edge_responsive`: assert `peak_overload` is **NOT** constant across
  `{original, optimized, random}` on at least one network (`o != p` or `o != r`),
  and add an **infinite-capacity ablation** that changes the opt-vs-orig makespan gain
  (proving load actually feeds back into the outcome). This is the test that flips the
  v2 limitation.
- Keep `test_makespan_penalizes_pending_not_just_failed` (the fixed metric).

Run: `.venv/bin/python -m pytest tests/coord -q` (+ `tests/gis` for the platform shim:
`.venv/bin/python -m pytest tests -q -k "platform or contagion"`).

---

## The discipline gates (anti-fabrication "命门")

1. **Outcome-blind mechanism-functionality gate (BEFORE locking):** across the
   ensemble, `peak_overload` must VARY across `{original, optimized, random}` on a
   non-trivial fraction of networks (target: differs on ≥30% of networks, and ≥1
   network where `optimized > original`), AND baselines complete. This proves load is
   edge-responsive. **If it does not vary, STOP and report honestly** — v3 failed to
   activate the channel; do NOT lock a "testable" P3/P5 or fake a counterexample.
2. **Lock predictions BEFORE running the experiment.** Only after gate (1) passes,
   write `PREDICTIONS-locked-v3.md` (P1/P2 timing; P3 divergence + ≥1 counterexample,
   now mechanistically possible; P5 CEI on the fixed makespan metric). No threshold or
   parameter is changed after seeing P-outcomes.
3. **Honest verdicts.** A falsified prediction is a valid result. Mandatory
   sensitivity analysis (params are uncalibrated). The study's claim remains
   method-mechanism validity on a SYNTHETIC ensemble, not real-world prediction.

---

## Scope / non-goals

- No real coordination-network data (still synthetic representative ensemble).
- No hazard physics, no GIS/spatial layer (non-spatial — `space=None`).
- `_network.py`, `_gate.py`, `_experiment.py` (analyze/P1–P5, `run_ensemble`,
  `default_scenario`, `PROTECT`) unchanged except where the activation mechanism or
  the `default_tasks` lead-heterogeneity requires a minimal, documented adjustment.
- Private fork only; not wired into any pipeline; no public push in this work.
