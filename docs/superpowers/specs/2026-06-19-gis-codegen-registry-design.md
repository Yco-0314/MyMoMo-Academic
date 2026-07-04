# GIS Codegen Registry Phase 1 Design Spec

**Status:** Implemented. **Date:** 2026-06-19. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md)
(autonomous codegen coverage and self-extension truth-table).

## Goal

Add a minimal deterministic capability registry for GIS codegen. The registry
separates capabilities that are already template-renderable from capabilities
that exist in the GIS runtime but are not yet safe to generate from a story.

This closes the main gap after the coupled seam work: runtime capability is now
larger than the codegen schema. The registry makes that difference explicit
instead of letting codegen silently pretend every runtime model has a template.

## Architecture

The registry lives in `abm_auto/gis/_capabilities.py`.

Each `GISCapability` records:

- `key`
- `spatial_type`
- `mechanism`
- involved `layers`
- optional `coupling`
- `temporal` and `dynamic` flags
- `renderable`
- `required_tokens`
- `gate`
- `wrong_space_tokens`

Phase 1 renderable capabilities:

- `raster_sir`
- `network_routing_load`

Phase 1 runtime-only capabilities:

- `flood_evacuation`
- `social_spatial_contagion`
- `point_network_risk`
- `polygon_point_zoning`
- `temporal_flood_evacuation`
- `dynamic_flood_evacuation`

Runtime-only capabilities are registered for deterministic gap reporting and
validation, but `render()` and the extractor reject them with an explicit
`not codegen-renderable` error.

## Codegen Contract

`GISModelSpec` keeps the legacy `spatial_type + mechanism` shape and adds an
optional `capability` key. Old specs continue to resolve through the registry.
Explicit capabilities must match the given `spatial_type` and `mechanism`.

`render(spec)` resolves the capability first. It renders only capabilities where
`renderable=True`; registered runtime-only capabilities fail before code is
emitted.

`gis_codegen_gate(files, spec)` reads required tokens and wrong-space tokens from
the registry. The gate still rejects forbidden patterns and still requires
generated code to import from `abm_auto.gis`.

The extractor prompt only advertises renderable capabilities. Legacy LLM output
without `capability` remains valid. If the LLM emits a registered but
non-renderable capability, extraction fails loudly before template rendering.

## Validation

Targeted validation:

```bash
python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_codegen_gate.py tests/gis/test_extractor.py -q
```

Coverage includes:

- legacy raster/network specs resolving to registry capabilities;
- runtime-only cells being registered but not renderable;
- unknown capability and capability/spec mismatch failures;
- raster generated model still running and passing its spatial gate;
- non-renderable capability rendering failure;
- fidelity gate required-token checks sourced from the registry;
- extractor compatibility with legacy output and rejection of non-renderable
  capabilities.

## Out of Scope

- Coupled, temporal, or dynamic runnable templates.
- Self-extension scaffold/generate/halt flow.
- A general `CoupledModel` abstraction.
- Changes to the base engine, calibration, agents, pipeline, or core codegen
  packages.
