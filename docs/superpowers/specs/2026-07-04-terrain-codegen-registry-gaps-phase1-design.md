# Terrain Codegen Registry Gaps Phase 1 - Design Spec

## Summary

Register the new terrain runtime/gate cells in the GIS codegen capability
registry as explicit, non-renderable gaps:

- `terrain_network_cost`
- `terrain_aware_routing`

This closes the truth-table gap created by the terrain coupling and
terrain-aware routing phases. The runtime and gates exist, but codegen must not
pretend it can render terrain models yet.

## Why This Is Next

The registry is the deterministic boundary between implemented GIS abilities
and runnable codegen templates. Terrain now has runtime/gate evidence, but no
template. If the registry omits it, self-extension and extractor diagnostics
cannot see the gap. If the registry marks it renderable too early, codegen can
fabricate support. The correct Phase 1 is explicit non-renderable registration.

## Scope

Modify:

- `abm_auto/gis/_capabilities.py`
- `tests/gis/test_capabilities.py`
- `tests/gis/test_codegen.py`
- `tests/gis/test_extractor.py`
- `docs/reproduce/coupled-seam/STATUS.md`

Do not modify codegen templates beyond relying on their existing
registered-but-nonrenderable refusal path. Do not add a terrain runnable
template.

## Registry Contract

Add:

```python
"terrain_network_cost": GISCapability(
    key="terrain_network_cost",
    spatial_type="terrain",
    mechanism="terrain_network_cost",
    layers=("terrain bridge heightfield", "GeoNetwork"),
    coupling="terrain_network",
    renderable=False,
    required_tokens=("terrain_cost_per_edge", "terrain_network_coupling_gate"),
    gate="terrain_network_coupling_gate",
)

"terrain_aware_routing": GISCapability(
    key="terrain_aware_routing",
    spatial_type="terrain",
    mechanism="terrain_aware_routing",
    layers=("terrain bridge heightfield", "GeoNetwork"),
    coupling="terrain_network_routing",
    renderable=False,
    required_tokens=("terrain_aware_shortest_path", "terrain_aware_routing_gate"),
    gate="terrain_aware_routing_gate",
)
```

These keys must validate only when explicit `capability` is present. They must
not appear in `renderable_capabilities()` and must not appear in the extractor
prompt.

## Tests

- `test_capabilities.py`:
  - both terrain capabilities are registered;
  - both have `renderable=False`;
  - required tokens and gate names are correct;
  - `renderable_capabilities()` still excludes them.

- `test_codegen.py`:
  - explicit `GISModelSpec(... capability="terrain_network_cost")` validates;
  - explicit `GISModelSpec(... capability="terrain_aware_routing")` validates;
  - `render(...)` for each fails with `registered but not codegen-renderable`.

- `test_extractor.py`:
  - prompt still omits the two terrain non-renderable capabilities;
  - if an LLM emits either registered terrain capability, extraction rejects it
    with `registered but not codegen-renderable`.

Final verification:

- `.venv/bin/python -m pytest tests/gis/test_capabilities.py tests/gis/test_codegen.py tests/gis/test_extractor.py -q`
- `.venv/bin/python -m pytest tests/gis -q`
- `.venv/bin/python engine_oracle.py --science`
- `.venv/bin/python engine_oracle.py --check`
- forbidden base-engine diff check must be empty.

## Boundaries

Do not:

- add terrain codegen templates;
- make terrain capabilities renderable;
- let extractor prompt advertise non-renderable terrain capabilities;
- introduce `CoupledModel`;
- change base-engine forbidden paths.
