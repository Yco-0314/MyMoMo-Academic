# NetLogo Semantic Migration Gate Phase 1 Design

**Status:** Ready for implementation.
**Date:** 2026-07-03
**Scope:** Add a small manifest-driven NetLogo semantic migration gate.

## Summary

The existing NetLogo line already has native semantic cells:

- `NetLogoWorld`, patches, turtles, links, breeds, `ask`, explicit ticks,
  globals, monitors;
- controls-to-MIR packaging for parsed Interface-tab controls;
- BehaviorSpace audit manifests;
- fixture gap audit.

Phase 1 should not build a NetLogo parser or re-implement those cells. It should
add the missing migration proof: a NetLogo-like semantic spec can be migrated
into a running `NetLogoWorld` and a MIR summary while preserving declared
patches, turtles, links, breeds, ticks, globals, monitors, and boundary notes.

## Architecture

Add:

```text
abm_auto/netlogo_migration.py
tests/test_netlogo_migration.py
docs/reproduce/netlogo-semantic-migration/example-spec.json
docs/reproduce/netlogo-semantic-migration/STATUS.md
```

Public API:

```python
SCHEMA = "abm-auto/netlogo-semantic-migration/v1"

load_netlogo_migration_spec(path: Path) -> dict
validate_netlogo_migration_spec(spec: dict) -> dict
run_netlogo_semantic_migration(spec: dict) -> dict
netlogo_semantic_migration_to_mir(spec: dict) -> MIR
netlogo_semantic_migration_gate(spec: dict) -> tuple[bool, str]
```

The implementation uses existing `NetLogoWorld`; it does not execute NetLogo
code text.

## Spec Shape

Required fields:

```json
{
  "schema": "abm-auto/netlogo-semantic-migration/v1",
  "model_id": "wolf-sheep-mini-migration-v1",
  "title": "Wolf Sheep Mini Migration",
  "world": {
    "seed": 0,
    "schedule": "sequential",
    "patches": {
      "min_pxcor": 0,
      "max_pxcor": 1,
      "min_pycor": 0,
      "max_pycor": 0,
      "state": {"grass": 1}
    },
    "globals": {"energy_cost": 1}
  },
  "turtles": [
    {
      "breed": "sheep",
      "count": 2,
      "state": {"energy": 3},
      "positions": [[0, 0], [1, 0]]
    },
    {
      "breed": "wolf",
      "count": 1,
      "state": {"energy": 5},
      "positions": [[0, 0]]
    }
  ],
  "links": [
    {"end1": 0, "end2": 1, "breed": "social-links", "directed": false}
  ],
  "ticks": 2,
  "monitors": [
    {"name": "count_turtles", "reporter": "count turtles"},
    {"name": "count_sheep", "reporter": "count breed sheep"},
    {"name": "count_links", "reporter": "count links"}
  ],
  "expected": {
    "ticks": 2,
    "turtle_count": 3,
    "patch_count": 2,
    "link_count": 1,
    "breeds": {"sheep": 2, "wolf": 1},
    "monitor_records": 2
  },
  "boundary_note": "Manifest migration only; not NetLogo parser or procedure execution."
}
```

## Validation Rules

- schema, model id, title, world, expected, and boundary note are required;
- schedule must be `sequential` or `random_order`;
- patch bounds must be integer and ordered;
- turtle `count` must be a positive integer;
- if positions are provided, their count must equal turtle count;
- positions must be integer coordinates inside the patch grid;
- link endpoints must reference existing created turtle ids;
- ticks must be a non-negative integer;
- monitor reporters are intentionally limited to:
  - `count turtles`
  - `count patches`
  - `count links`
  - `count breed <breed>`
- expected fields must include ticks, turtle count, patch count, link count,
  breeds, and monitor record count.

## Runtime Contract

`run_netlogo_semantic_migration(spec)` returns:

```python
{
    "ok": bool,
    "issues": list[str],
    "model_id": str,
    "ticks": int,
    "turtle_count": int,
    "patch_count": int,
    "link_count": int,
    "breeds": {"sheep": 2, "wolf": 1},
    "monitor_records": [...],
    "mir": {...}
}
```

The runtime should collect monitors once before ticks advance and once after all
ticks advance, so `monitor_records=2` in the seed fixture.

`netlogo_semantic_migration_to_mir(spec)` creates a MIR with:

- `metadata.domain = "netlogo"`;
- `entities` for turtle breeds, patch grid, and link breeds;
- `state` for globals and patch state keys;
- `relations` for declared links;
- `processes` with `mechanism="netlogo_semantic_migration"`;
- `run.params` preserving tick count and schedule;
- `trace.source_format = "netlogo_semantic_migration_manifest"`.

## Gate

`netlogo_semantic_migration_gate(spec)` passes only when:

- validation passes;
- runtime counts match `expected`;
- MIR JSON round-trips through `MIR.from_json(...)`;
- the gate message states the boundary:

```text
not a NetLogo parser
not NetLogo procedure execution
```

## Boundaries

This phase does not:

- parse arbitrary `.nlogo` code;
- execute `to setup` / `to go` procedures;
- evaluate NetLogo expressions beyond the listed monitor reporters;
- generate codegen templates;
- claim full NetLogo compatibility;
- touch base-engine directories.

## Acceptance Criteria

- New migration tests pass.
- Existing NetLogo semantic and MIR adapter tests still pass.
- The committed example spec gates.
- `SCIENCE GATE: PASS` and `ENGINE ORACLE: PASS`.
- Forbidden base-engine diff is empty.
