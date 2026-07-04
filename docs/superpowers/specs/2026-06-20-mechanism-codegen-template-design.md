# Mechanism Codegen Template Phase 1 Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only mechanism-library codegen

## Summary

Promote `mechanism_threshold_adoption` from registered gap to
codegen-renderable. The generated model builds a deterministic chain neighbor
function, runs `run_threshold_adoption(...)`, and verifies the neighbor seam with
`mechanism_space_gate(...)`.

`mechanism_contagion` remains registered but not renderable in this phase. That
preserves the self-extension registered-gap path and avoids claiming a
contagion-specific codegen gate before one exists.

## Goals

- Mark `mechanism_threshold_adoption` as `renderable=True`.
- Add required codegen tokens:
  - `run_threshold_adoption`
  - `mechanism_space_gate`
- Render deterministic runnable code for explicit
  `GISModelSpec(spatial_type="mechanism", mechanism="threshold_adoption",
  capability="mechanism_threshold_adoption")`.
- Keep `mechanism_contagion` as registered-but-nonrenderable.
- Keep base engine directories untouched.

## Non-Goals

- No contagion mechanism codegen in this phase.
- No new mechanism runtime behavior.
- No GIS space adapter template work; this is pure neighbor-callable mechanism
  codegen.
- No self-extension scaffold generation.
- No `CoupledModel` extraction.
- No edits under `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.

## Architecture

The template uses the existing deterministic mechanism seam:

- `_chain_neighbors(n)` provides connected neighbors over integer ids;
- `run_threshold_adoption(...)` shows the mechanism runtime call;
- `mechanism_space_gate(...)` compares connected vs isolated neighbors and must
  print `PASS`.

Because `mechanism_space_gate` is threshold-adoption specific, contagion remains
a registered gap until a dedicated contagion gate is introduced.

## Testing

Update GIS tests for:

- registry: `mechanism_threshold_adoption` is renderable and
  `mechanism_contagion` remains nonrenderable;
- explicit threshold-adoption spec validates;
- rendered code contains `run_threshold_adoption` and `mechanism_space_gate`;
- rendered code runs and prints `PASS`;
- codegen fidelity gate passes clean threshold code and fails when required
  tokens are removed;
- extractor prompt includes threshold adoption but still rejects
  `mechanism_contagion`;
- self-extension preflight classifies threshold adoption as renderable and
  contagion as registered gap.

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

`docs/reproduce/coupled-seam/STATUS.md` should record threshold-adoption
mechanism codegen as the first runnable mechanism-library template, while
`mechanism_contagion` remains a registered gap.
