# Social-Spatial Codegen Template Phase 1 Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only social-spatial contagion codegen

## Summary

Promote the existing `social_spatial_contagion` capability from registered gap
to codegen-renderable. The generated model builds a deterministic grid-like
spatial neighbor function plus a synthetic social network, runs
`run_contagion(...)`, and verifies social reach expansion with
`social_lift_gate(...)`.

This is codegen coverage over an existing gated runtime adapter. It does not add
new contagion dynamics, real social data loading, spatial file I/O, calibration,
or a shared `CoupledModel` abstraction.

## Goals

- Mark `social_spatial_contagion` as `renderable=True`.
- Add required codegen tokens:
  - `combined_neighbors`
  - `run_contagion`
  - `social_lift_gate`
  - `networkx`
- Render deterministic runnable code for explicit
  `GISModelSpec(spatial_type="coupled", mechanism="social_spatial_contagion",
  capability="social_spatial_contagion")`.
- Keep runtime behavior unchanged.
- Update extractor prompt and self-extension preflight behavior through the
  registry.

## Non-Goals

- No new social contagion model behavior.
- No point/polygon template work in this phase.
- No real social graph or spatial file I/O.
- No codegen scaffold generation.
- No `CoupledModel` extraction.
- No edits under `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.

## Architecture

The template uses the same synthetic pattern as the existing social-spatial
tests:

- `grid_neighbors(side)` provides local spatial neighbors over agent ids;
- a deterministic NetworkX Watts-Strogatz graph supplies long-range social ties;
- `run_contagion(...)` is called once so the fidelity gate can verify the
  generated model uses the social-spatial runtime adapter;
- `social_lift_gate(...)` compares spatial-only and spatial-plus-social runs
  and must print `PASS`.

This keeps the mechanism space-agnostic: the generated code passes a neighbor
function instead of inventing a new space object or lifecycle wrapper.

## Testing

Update GIS tests for:

- registry: `social_spatial_contagion` is renderable and has required tokens;
- renderable list includes `social_spatial_contagion`;
- explicit social-spatial spec validates;
- rendered code contains `combined_neighbors`, `run_contagion`, and
  `social_lift_gate`;
- rendered code runs and prints `PASS`;
- codegen fidelity gate passes clean social-spatial code and fails if required
  social tokens are removed;
- extractor prompt includes social-spatial once renderable;
- self-extension preflight classifies social-spatial as renderable while another
  runtime-only capability remains a registered gap.

Final verification:

```bash
.venv/bin/python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py tests/gis/test_self_extension.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Expected Status Update

`docs/reproduce/coupled-seam/STATUS.md` should record social-spatial codegen as
the first runnable social-network plus spatial-neighbor template. It remains
synthetic and does not claim real social network validity.
