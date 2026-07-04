# GIS Self-Extension Gap/Halt Phase 1 Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only deterministic gap reporting and halt decisions

## Summary

Add the first self-extension control surface for GIS codegen: a deterministic
preflight that classifies a requested `GISModelSpec` as renderable, registered
but not renderable, mismatched, or unknown. This phase does not generate new
capabilities. It reports the gap and halts with enough structured information
for a future scaffold-and-gate phase.

This implements the honest fallback part of ADR-019: the registry is the source
of truth; a missing or nonrenderable capability becomes a deterministic gap, not
a fabricated template.

## Goals

- Add `abm_auto/gis/_self_extension.py`.
- Provide `gis_codegen_preflight(spec) -> dict`.
- Provide `gis_self_extension_gap_gate() -> tuple[bool, str]`.
- Return stable, JSON-like dictionaries that can be logged by future pipeline or
  codegen orchestration code.
- Distinguish these cases:
  - `renderable`: registered and codegen-renderable; caller may render.
  - `registered_gap`: registered runtime capability exists, but template support
    is absent; caller must halt.
  - `invalid_spec`: explicit capability mismatch or invalid legacy spec; caller
    must halt.
  - `unknown_gap`: explicit capability key is unknown; caller must halt.
- Preserve current `render(spec)` behavior. `render()` still renders or raises;
  the new preflight is an additive diagnostic layer.

## Non-Goals

- No automatic scaffold generation.
- No LLM code writing or retry loop.
- No edits to base codegen or base runtime packages.
- No new `CoupledModel`.
- No extractor behavior change in this phase.
- No template work for temporal, dynamic, social-spatial, point/polygon,
  validation, or calibration capabilities.

## API

```python
def gis_codegen_preflight(spec: GISModelSpec) -> dict:
    ...


def gis_self_extension_gap_gate() -> tuple[bool, str]:
    ...
```

For a renderable spec, `gis_codegen_preflight(...)` returns:

```python
{
    "ok": True,
    "status": "renderable",
    "action": "render",
    "capability": "flood_evacuation",
    "spatial_type": "network",
    "mechanism": "flood_evacuation",
    "renderable": True,
    "layers": ("GeoNetwork", "RasterSpace"),
    "coupling": "raster_network_flood",
    "temporal": False,
    "dynamic": False,
    "gate": "flood_gate",
    "required_tokens": (...),
    "reason": "",
}
```

For a registered but nonrenderable capability, it returns:

```python
{
    "ok": False,
    "status": "registered_gap",
    "action": "halt",
    "capability": "dynamic_flood_evacuation",
    "renderable": False,
    "reason": "capability 'dynamic_flood_evacuation' is registered but not codegen-renderable",
    ...
}
```

For an unknown explicit capability, it returns:

```python
{
    "ok": False,
    "status": "unknown_gap",
    "action": "halt",
    "capability": "missing_cell",
    "reason": "unknown capability 'missing_cell'",
}
```

For mismatch or invalid implicit specs, it returns:

```python
{
    "ok": False,
    "status": "invalid_spec",
    "action": "halt",
    "capability": "...",
    "reason": "...",
}
```

## Gate

`gis_self_extension_gap_gate()` is deterministic and synthetic. It passes only
when all of these hold:

- a renderable flood spec returns `ok=True`, `status="renderable"`,
  `action="render"`;
- a registered dynamic flood spec returns `ok=False`,
  `status="registered_gap"`, `action="halt"`;
- an unknown explicit capability returns `ok=False`, `status="unknown_gap"`,
  `action="halt"`;
- a mismatched explicit capability returns `ok=False`, `status="invalid_spec"`,
  `action="halt"`.

The gate wording must be explicit: this proves deterministic gap/halt reporting,
not self-generating GIS capabilities.

## Testing

Add `tests/gis/test_self_extension.py` covering:

- renderable flood spec is classified as renderable;
- registered dynamic flood capability is classified as registered gap;
- unknown explicit capability is classified as unknown gap;
- capability/spec mismatch is classified as invalid spec;
- invalid implicit mechanism is classified as invalid spec;
- returned capability metadata includes layers, coupling, temporal/dynamic flags,
  gate, and required tokens;
- gate passes and states the limitation.

Final verification:

```bash
.venv/bin/python -m pytest tests/gis/test_self_extension.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Expected Status Update

`docs/reproduce/coupled-seam/STATUS.md` should record that self-extension Phase 1
now has deterministic gap/halt reporting. Scaffold-and-gate remains a future
phase once a specific known-pattern gap is selected for auto-fill.
