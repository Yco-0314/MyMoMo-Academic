# Dynamic Congestion Codegen Template Design Spec

**Status:** Approved for implementation
**Date:** 2026-06-20
**Repo:** MyMoMo-GIS-Academic
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md)
and [ADR-019 synthesis](../../reproduce/coupled-seam/ADR-019-SYNTHESIS.md)

## Goal

Promote the existing dynamic congestion routing runtime into a codegen-renderable
GIS capability. The generated model builds a synthetic `GeoNetwork`, runs
`run_dynamic_congestion_routing(...)`, and verifies behavior with
`dynamic_congestion_reroute_gate(...)`.

This closes the codegen coverage gap opened by Dynamic Congestion Routing Phase
1. It is synthetic codegen evidence only. It does not claim real traffic-flow
validity, congestion calibration, capacity modeling, or optimal assignment.

## Scope

Add one capability:

```text
dynamic_congestion_routing
```

Capability metadata:

- `spatial_type="network"`
- `mechanism="dynamic_congestion_routing"`
- `layers=("GeoNetwork", "moving agents", "per-tick edge loads")`
- `coupling="dynamic_network_congestion"`
- `dynamic=True`
- `temporal=False`
- `renderable=True`
- `gate="dynamic_congestion_reroute_gate"`

Required generated-code tokens:

- `GeoNetwork`
- `run_dynamic_congestion_routing`
- `dynamic_congestion_reroute_gate`

## Architecture

The registry remains the codegen truth-table. `dynamic_congestion_routing`
becomes a renderable capability in `abm_auto/gis/_capabilities.py`.

The template layer adds a dedicated branch in `abm_auto/gis/_templates.py`.
The generated model is a single synthetic `main.py` that:

1. builds the deterministic diamond road network used by the runtime gate;
2. chooses two leading agents at `B` and one follower at `A`;
3. calls `run_dynamic_congestion_routing(...)` with `reroute=True`;
4. calls `dynamic_congestion_reroute_gate(...)`;
5. prints `PASS: ...` or `FAIL: ...`.

No runtime behavior changes are required. The generated code calls existing GIS
runtime functions and existing deterministic gate functions.

## Generated Synthetic Scenario

The generated model should use the same shape as runtime tests:

```text
A ---- B ---- C ---- safe
      \          /
       D ------ E
```

Coordinates:

- A `(0, 0)`
- B `(100, 0)`
- C `(200, 0)`
- safe `(300, 0)`
- D `(100, -100)`
- E `(200, -100)`

Parameters:

- `n_steps`: default `8`
- `speed_m_per_tick`: default `100`
- `congestion_alpha`: default `3.0`

The generated model should accept overrides from `GISModelSpec.params` for those
three values. It does not need to support real road data in this phase.

## Codegen Fidelity

`gis_codegen_gate(...)` already reads required tokens from the registry. Once the
capability is registered, missing `run_dynamic_congestion_routing` or
`dynamic_congestion_reroute_gate` must fail structurally.

The generated template must not import or use:

- `RasterSpace`
- `RasterTimeline`
- `run_dynamic_flood_evacuation`
- `dynamic_flood_reroute_gate`
- base-engine runtime modules

## Extractor And Self-Extension

The extractor prompt is generated from `renderable_capabilities()`. Once
`dynamic_congestion_routing` is renderable, the prompt should advertise it
automatically, and explicit LLM output using that capability should validate.

Self-extension preflight should classify the capability as:

```python
ok=True
status="renderable"
action="render"
```

Scaffold should refuse it as already renderable, consistent with other closed
gaps.

## Documentation

Update coupled seam status and ADR-019 synthesis to state that dynamic congestion
now has codegen coverage. Keep the boundary explicit:

- synthetic generated model only;
- no traffic-flow validity claim;
- no real-data congestion calibration;
- no `CoupledModel` extraction.

## Tests

Add or extend tests for:

- capability registry metadata and renderable list;
- explicit `GISModelSpec` validation;
- rendered code structure;
- rendered code executable gate PASS;
- codegen gate required token checks;
- extractor prompt and explicit extraction;
- self-extension preflight renderability;
- docs/status text where useful.

Final verification must include:

```bash
.venv/bin/python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py tests/gis/test_self_extension.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Non-Goals

- No runtime model changes.
- No real road data demo.
- No congestion calibration.
- No BPR, capacity, queue spillback, assignment, or traffic-flow model.
- No `RasterSpace`, `RasterTimeline`, or flood coupling in this template.
- No `CoupledModel`, `CoupledSpace`, or shared lifecycle helper extraction.
- No base-engine changes.
