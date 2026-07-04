# GIS Platform Self-Depth Strengthening — Design Spec

**Status:** Draft. **Date:** 2026-06-27. **Branch:** `codex/open-source-status-reconciliation`.
**Parent:** ADR-020 and `2026-06-24-platform-migration-scope-decision.md`.

## Purpose

The platform direction is **strengthen**, not simplify. The project is intended
to become a broad GIS-ABM platform, so the ADR-020 floor should earn its depth in
production adapters instead of remaining mostly a naming convention.

The current issue is narrow and factual: `CongestionModel` and `FloodModel` are
production adapters, but their agent `step()` methods are empty, they override
the whole model `step()`, and they append summaries by hand instead of using
`DataCollector`.

## Scope

Implement Phase 1 of platform strengthening:

- Add `AgentSet.do(method_name, *args, **kwargs)` as a small scheduled-stage
  interface. It applies a named per-agent method in the model's schedule order.
- Refactor `CongestionModel` so planning, edge entry, and movement are per-agent
  stages invoked via `self.agents.do(...)`.
- Refactor `FloodModel` so flood stranding, route planning/edge entry, and
  movement are per-agent stages invoked via `self.agents.do(...)`.
- Move dynamic step summaries to `DataCollector` in both production adapters.
- Preserve public return shapes and deterministic behavior.

## Non-Goals

- Do not migrate `_sir`, `_flood_model`, `_commute`, `_social`, or `_road_model`.
- Do not add a grand `CoupledModel`.
- Do not add congestion capacity, traffic-flow theory, or emergency-evacuation
  optimality claims.
- Do not change codegen templates or registry keys.

## Interface

`AgentSet.do("stage_name")` is deliberately smaller than a new scheduler type.
It reuses the existing `sequential` / `random_order` order semantics and lets
models express multi-phase ticks without bypassing the platform's agent
collection.

Production adapters may still override `GISModel.step()` when their tick order
is model-specific. The strengthening target is that the overridden step delegates
agent-stage work to `AgentSet` and delegates summary records to `DataCollector`.

## Expected Verification

- New platform test proves `AgentSet.do()` calls named methods in scheduled order
  and rejects missing stages loudly.
- Dynamic congestion and dynamic flood tests still pass.
- Congestion and flood gates still pass.
- A regression test proves the production adapters now have a `DataCollector`
  reporter and collect summaries through it.
- Base-engine forbidden diff remains empty.
