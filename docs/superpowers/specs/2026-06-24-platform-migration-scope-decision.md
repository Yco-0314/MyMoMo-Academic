# Platform migration scope — decision: the migration set is empty

**Date:** 2026-06-24
**Branch:** `feat/gis-sweep`
**Status:** Decided — **do not migrate** the remaining hand-written model loops onto
the ADR-020 platform. All five candidates are `leave-as-is`. The platform's adapter
set is already complete and correct.
**Method:** Matt Pocock `codebase-design` (deep module + the deletion test) +
the project's own YAGNI rule (*one adapter = hypothetical seam, two = real*).
**Provenance:** grounded by a 9-agent analysis sweep (per-module deletion test ×5 +
platform-interface read + reference-pattern extraction from the 2 merged migrations +
a synthesis pass + an adversarial skeptic). All three independent passes converged.

---

## Context

ADR-020 added the GIS platform floor (`abm_auto/gis/_platform.py`):
`GISAgent` / `AgentSet` / `DataCollector` / `GISModel` — a Mesa-shaped deep module
that absorbs four hand-rolled subsystems behind a thin interface (subclass +
override `step`): a scheduler, an agent container/iteration order, a seeded-RNG
tick loop, and a per-tick collector.

The platform docstring framed its purpose as ending *"5 hand-written step loops"*.
Three **real adapters** now sit on the seam:

- `ContagionModel` (reference, in `_platform.py`)
- `CongestionModel` (`_dynamic_congestion.py`, migration `0a0bb27`, 2nd adapter)
- `FloodModel` (`_dynamic_flood.py`, migration `d0ff9dd`, 3rd adapter)

The open "扫尾" question was whether to migrate the remaining hand-written loops —
`_sir`, `_flood_model`, `_commute`, `_social`, `_road_model` — onto the platform to
make the seam "real across all models".

## The seam, in `codebase-design` terms

The deep module is the platform; each migrated model is an **adapter at the seam**.
The seam sits at the **per-tick lifecycle boundary**: where a model holds
*persistent mutable agents that are stepped across real ticks*. The three existing
adapters live exactly there — each had genuine cross-tick agent state + a
multi-phase `step` + a hand-written run loop for the platform to unify.

The migration question is therefore a **deletion test**, applied per candidate:
*if I delete this module's hand-rolled machinery, what does the platform give back?*

## Verdict per candidate (all `leave-as-is`)

| Module | Shape | Deletion test returns | Byte-faithful risk | Protecting gate / tests |
|---|---|---|---|---|
| `_sir` | array synchronous CA (two ndarrays, row-major snapshot scan) | ~1 line (`history.append` → `DataCollector`) | **High** — a faithful migration would force building the deferred `concurrent` `AgentSet` strategy for **one** consumer (a sequential schedule reads live-mutated neighbours and diverges on tick 1) | `spatial_spread_gate`; `tests/gis/test_sir.py`, `test_gate.py`, `test_end_to_end.py`, `test_codegen_gate.py` |
| `_flood_model` | memoryless snapshot fn (graph-cut + one `multi_source_dijkstra` + one aggregation) | nothing | Low — but its **stateful sibling `_dynamic_flood.FloodModel` is already migrated**; the snapshot version has no agents/state/RNG to host | `flood_gate`, `temporal_flood_gate`; `test_flood_model.py`, `test_flood_gate.py`, `test_temporal.py` |
| `_commute` | parameter sweep over pure/array fns (`spreads` loop, not a clock) | nothing | Low — one `random.Random(seed)` consumed across the whole sweep makes draw order load-bearing | none (test-gated: `test_commute.py`) |
| `_social` | ~8-line space-coupling adapter delegating to shared `_mechanisms.run_contagion` | nothing | **High** — platform `ContagionModel` is **byte-incompatible** (async in-place + one draw per infected neighbour vs `_mechanisms` synchronous double-buffer + one draw per susceptible via `1-(1-beta)**k`); migrating = replacing the shared engine, breaking the pinned-history test | `social_lift_gate`, `mechanism_contagion_gate`; `test_social.py` (+ codegen/capability) |
| `_road_model` | stateless trip loop (`for _ in range(n_trips)`, independent trips) | nothing (only reproduces one `random.Random` line) | Low — but RNG/node/edge order is pinned by 4 test files + the gate | `geo_network_gate`; `test_road_model.py`, `test_geo_gate.py`, `test_geo_end_to_end.py` |

**Why none migrates.** The platform exists to unify *persistent-stepped-agent*
models. These five are structurally different cousins the platform was deliberately
**not** built for: an array CA, a memoryless snapshot, a parameter sweep, a thin
engine adapter, and a stateless aggregation. For each, the deletion test returns
~0 lines while migration would *add* a no-op `GISAgent.step` plus a `GISModel`
wrapper around a one-shot computation — shallow ceremony with negative leverage —
and several carry concrete byte-faithfulness risk against gates and tests that pin
exact output. The project's YAGNI rule cuts the same way: the seam is **already
real** (three adapters), and no fourth migration demonstrates anything new. SIR is
the sharpest case — migrating it would itself violate the two-adapters rule by
building the `concurrent` strategy ADR-020 explicitly defers, for a single model.

Additional hard constraint: `run_road_model`, `run_flood_evacuation` /
`run_temporal_flood_evacuation`, and `_social.run_contagion` / `social_lift_gate`
are **codegen `required_tokens`** emitted verbatim by `_templates.py` and asserted
by the capability / codegen-fidelity gates. Their free-function names and
signatures must stay stable regardless of any internal change.

## Deeper finding (recorded, not yet acted on)

The deletion test, turned on the **platform itself**, surfaces a real question.
Both *production* adapters bypass the platform's machinery:

- `CongestionAgent.step` (`_dynamic_congestion.py:38`) and
  `FloodAgent.step` (`_dynamic_flood.py:41`) are literally `pass`.
- Each model **fully overrides `GISModel.step()`**; the per-tick logic lives there.
- Neither uses `DataCollector` / `reporter`; `self.agents` (`AgentSet`) is used only
  as an insertion-ordered container, never its `.step()` scheduler.

So the platform's actual leverage — the scheduler strategies and the
`DataCollector` — is currently exercised **only by the toy `ContagionModel`
reference**. Production code uses the platform as a base-class + ordered-container
naming convention. The legitimate `codebase-design` follow-up is therefore *not*
more migrations but a decision about the platform's own depth: either **simplify**
it toward what the adapters actually use, or **add an adapter that genuinely
needs** the scheduler/collector machinery. Deferred to a future session; out of
scope for this decision.

## Verification (docs-only change; HEAD `13c8709`)

Run at HEAD before writing this record (a docs-only change cannot affect engine
behaviour; gates confirm the additive invariant holds):

- forbidden base-engine diff (`abm_auto/{runtime,codegen,calibration,agents,pipeline}`): **empty**
- `git diff --check`: clean
- `engine_oracle.py --science`: **SCIENCE GATE: PASS**
- `engine_oracle.py --check`: **ENGINE ORACLE: PASS** (byte-identical)
- base suite (`pytest tests/ --ignore=tests/gis`): **488 passed, 4 skipped**
- GIS suite (`pytest tests/gis`): **539 passed, 1 skipped**

## Decision

The migration set is **empty**. `ContagionModel` + `CongestionModel` + `FloodModel`
are the complete, correct adapter set under ADR-020. Do not re-attempt migrating
`_sir` / `_flood_model` / `_commute` / `_social` / `_road_model`. Revisit only if an
**external** driver appears (a pedagogy/demo goal, a codegen-template ambition, or
a second synchronous-CA raster ABM that would make `concurrent` a real two-consumer
seam) — and if so, prefer a shared array-CA strategy over forcing SIR onto the
object-agent platform.
