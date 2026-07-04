# GIS Platform Staged Lifecycle — Design Spec

**Status:** Draft. **Date:** 2026-06-27. **Branch:** `codex/platform-staged-lifecycle`.
**Parent:** `2026-06-27-platform-self-depth-strengthening-design.md`.

## Purpose

Phase 1 made production adapters use `AgentSet.do(...)` and `DataCollector`.
Phase 2 makes the repeated staged tick lifecycle a platform interface.

The broad GIS-ABM direction needs a real production lifecycle seam, not just
base classes. Dynamic congestion and dynamic flood now share the same shape:

1. prepare tick-level context,
2. run named per-agent stages in scheduled order,
3. update derived context between stages when needed,
4. collect a per-tick summary,
5. advance `t`.

## Scope

- Add `StagedGISModel(GISModel)`.
- Interface:
  - `stages: tuple[str, ...]`
  - hooks: `begin_step()`, `before_stage(stage)`, `after_stage(stage)`,
    `end_step()`
  - default `step()` executes the staged lifecycle and collects via reporter.
- Refactor `CongestionModel` and `FloodModel` to subclass `StagedGISModel`.
- Keep public function signatures and return shapes unchanged.
- Keep dynamic gates unchanged.

## Non-Goals

- No `CoupledModel`.
- No new traffic-flow, capacity, congestion, evacuation, or rerouting science.
- No migration of snapshot/array/stateless modules.
- No codegen registry changes.

## Verification

- Platform tests prove hook/stage/collector order.
- Production adapter tests prove congestion/flood subclass `StagedGISModel` and
  still run their named stages.
- Dynamic congestion/flood tests and gates remain green.
- GIS suite, engine oracle, and base suite remain green.
