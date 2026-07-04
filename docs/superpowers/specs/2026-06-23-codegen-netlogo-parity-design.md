# Codegen Registry — NetLogo Parity Integration — Design Spec

**Status:** Draft. **Date:** 2026-06-23. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md).
**Builds on (merged into `main`):**
- `2026-06-22-netlogo-parity-topology-design.md` — DE-9IM topology + line×polygon / polygon×polygon coupling cells
- `2026-06-22-netlogo-parity-focal-design.md` — raster convolve / resample / raster_sample
- `2026-06-22-netlogo-parity-coverage-design.md` — areal coverage (polygon → raster)

## Why

The three NetLogo-parity phases shipped **runtime** primitives. The autonomous
codegen path (intent → spec → render → run → fidelity-gate → science-gate) does
not know about them yet: `_capabilities.py` has 13 capabilities, none of them
expose topology / focal / coverage. The self-extension story in ADR-019 only
holds when new runtime capability is **routed** through codegen — otherwise an
LLM emitting "convolve a flood raster" generates code the fidelity gate cannot
verify.

This phase **closes that loop**: register 3 new capabilities, give each a
template that produces a runnable model, and have the codegen-fidelity gate
catch broken renders via the existing `required_tokens` mechanism.

## Hard constraints

1. Zero changes to `abm_auto/runtime/`, `codegen/`, `calibration/`, `agents/`,
   `pipeline/`. Additive only.
2. The 13 existing capabilities and their templates / tests must remain
   byte-stable. Adding 3 new entries to `CAPABILITIES`, 3 new templates, and a
   new branch in `render(spec)` is purely additive.
3. Every new capability must run end-to-end: render → execute → its associated
   gate (`line_polygon_gate` / `focal_gate` / `apply_coverage_gate`) returns PASS.
4. Predictions locked before runs: every new template's `required_tokens` is
   chosen BEFORE the test exercises the fidelity gate, and the gate's failure
   mode is exercised by a broken-template test.

## What the 3 new capabilities look like

### NL1 `topology_clip` — line × polygon coupling cell

- `spatial_type="topology"`, `mechanism="line_polygon_clip"`, `layers=("LineLayer", "Polygon")`
- Template emits: build a small line layer + a polygon → call `lines_in_polygon` for
  inside/outside groups → call `line_polygon_gate` → print PASS/FAIL.
- `required_tokens = ("lines_in_polygon", "line_polygon_gate")`
- `wrong_space_tokens = ("RasterSpace", "GeoNetwork")` (these would be a wrong-space leak)
- `gate = "line_polygon_gate"`

### NL2 `raster_focal` — focal raster operator

- `spatial_type="raster"`, `mechanism="focal_smoothing"`, `layers=("RasterField",)`
- Template emits: build a small noisy raster → call `convolve` with a 3×3 mean
  kernel → call `focal_gate` → print PASS/FAIL.
- `required_tokens = ("RasterField", "convolve", "focal_gate")`
- `wrong_space_tokens = ("GeoNetwork",)` (focal on a network would be a wrong-space leak)
- `gate = "focal_gate"`

### NL3 `raster_coverage` — areal coverage (polygon → raster)

- `spatial_type="raster"`, `mechanism="areal_coverage"`, `layers=("Polygon", "RasterField")`
- Template emits: build a small raster template + 2 disjoint half-envelope polygons
  → call `apply_coverage` → call `apply_coverage_gate` → print PASS/FAIL.
- `required_tokens = ("RasterField", "apply_coverage", "apply_coverage_gate")`
- `wrong_space_tokens = ("GeoNetwork",)`
- `gate = "apply_coverage_gate"`

## Decomposition (TDD, bite-sized)

1. **Register 3 capabilities** in `_capabilities.py`. Tests:
   `CAPABILITIES["topology_clip"]` etc. resolvable; `MECHANISMS` table updated.
2. **Add 3 templates** to `_templates.py` + extend `render(spec)` to dispatch
   the 3 new keys. Tests:
   - `render(spec)["main.py"]` contains every `required_tokens` string;
   - the generated code **executes** end-to-end and its associated gate
     prints `PASS`.
3. **Codegen-fidelity gate already covers** the new caps via `required_tokens` /
   `wrong_space_tokens` — confirm by:
   - happy-path: `gis_codegen_gate(render(spec), spec)` is `(True, [])`;
   - injected-fault path: remove a required token → gate returns `(False, [...])`.

## Validation

```
.venv/bin/python -m pytest tests/gis/test_codegen_netlogo_parity.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline   # must be EMPTY
```

## Non-goals

- LLM extractor changes (B4 `_extractor.py`): deferred; the registry is
  data-driven, so the extractor will pick up the new keys without code changes
  the moment the model is prompted with an updated taxonomy. That belongs to a
  separate B4-update spec.
- A unified "registry of registries" abstraction. There are now 16 entries;
  YAGNI still applies until a real second registry appears.
- Real GIS data; synthetic in-test inputs only.
- No edits to `codex/real-data-validation-pack-v2*`.
