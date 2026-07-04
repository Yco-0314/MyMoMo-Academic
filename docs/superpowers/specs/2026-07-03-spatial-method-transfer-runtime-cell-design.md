# Spatial Method Transfer Runtime Cell Phase 1 Design

**Date:** 2026-07-03
**Roadmap lane:** GISABM Generalization

## Summary

Add the first runtime cell for `spatial_method_transfer`. The cell applies a
single graph-neighborhood method to two different spatial representations:
`RasterSpace` cells and `GeoNetwork` nodes. This closes the runtime side of the
registered ADR-019 layer-E gap while intentionally keeping the capability
nonrenderable in codegen until a later template phase.

The first method is a deterministic Forman-style edge curvature proxy:

```text
curvature(u, v) = 4 - degree(u) - degree(v)
```

This is not a full Ollivier-Ricci implementation and not a TDA library binding.
It is a small transfer proof: the same graph-neighborhood calculation can be
applied to different GIS spaces through existing neighbor adapters and can
produce the same structural signature on equivalent topologies.

## Architecture

Create:

`abm_auto/gis/_spatial_method_transfer.py`

The module owns:

- neighbor-callable edge extraction;
- deterministic Forman-style curvature scoring;
- summary signatures for any `neighbors_of(i)` method;
- `RasterSpace` adapter entry point;
- `GeoNetwork` adapter entry point;
- `spatial_method_transfer_report`;
- `spatial_method_transfer_gate`.

It reuses:

- `raster_cell_neighbors(...)` from `_mechanism_adapters.py`;
- `geonetwork_node_neighbors(...)` from `_mechanism_adapters.py`;
- `RasterSpace`, `RasterField`;
- `GeoNetwork`.

Modify:

- `abm_auto/gis/_capabilities.py` comments only: the capability remains
  `renderable=False`, but the comment must say the runtime cell exists while
  codegen template support is still absent.
- `abm_auto/gis/_self_extension.py` message/comment only: the registered gap is
  now a codegen-template gap, not a runtime-cell gap.
- `tests/gis/test_self_extension.py` docstrings/comments if needed.
- ADR-019 coupled-seam docs.

Do not add a codegen template in this phase.

## Public API

Expose:

```python
forman_ricci_edge_scores(n_nodes, neighbors_of) -> dict[tuple[int, int], float]
spatial_curvature_summary(n_nodes, neighbors_of) -> dict
raster_spatial_curvature_summary(space, moore=False) -> dict
geonetwork_spatial_curvature_summary(geonet) -> dict
spatial_method_transfer_report() -> dict
spatial_method_transfer_gate() -> tuple[bool, str]
```

`spatial_curvature_summary(...)` returns:

- `n_nodes`
- `n_edges`
- `scores`
- `score_signature`
- `min_score`
- `max_score`
- `mean_score`
- `min_edges`

`score_signature` is the sorted list of curvature scores. It is the transfer
comparison surface across space types.

## Gate Semantics

The gate constructs two equivalent chain topologies:

- a `1 x 4` `RasterSpace` using rook neighbors;
- a four-node `GeoNetwork` chain.

The same curvature method should produce:

```text
score_signature = [0.0, 1.0, 1.0]
```

The gate passes only when:

- raster summary has 4 nodes and 3 edges;
- geonetwork summary has 4 nodes and 3 edges;
- both score signatures match exactly;
- the middle chain edge is the lowest-curvature edge;
- gate text states this is a Forman-style transfer proof, not full ORC/TDA and
  not spatial validation.

## Registry Boundary

`spatial_method_transfer` remains:

```python
renderable=False
```

Reason: the runtime method exists after this phase, but there is still no
codegen template or extractor contract for rendering this capability from a
story/spec. Self-extension should continue to classify it as
`registered_gap`, but the gap reason should now be "registered runtime cell is
not codegen-renderable" rather than "runtime cell does not exist".

## Tests

Add `tests/gis/test_spatial_method_transfer.py` covering:

- edge scoring on a four-node chain returns expected scores;
- invalid `n_nodes`, bool `n_nodes`, bad neighbor ids, and self loops fail;
- raster curvature summary produces `[0.0, 1.0, 1.0]`;
- geonetwork curvature summary produces `[0.0, 1.0, 1.0]`;
- report compares raster/geonetwork signatures and passes;
- gate passes with boundary text.

Update self-extension tests if message expectations become stale, while
preserving:

- `gis_codegen_preflight(spatial_method_transfer)` returns `registered_gap`;
- `gis_codegen_scaffold(spatial_method_transfer)` returns `scaffold_ready`;
- `renderable` remains `False`.

Run:

```bash
.venv/bin/python -m pytest tests/gis/test_spatial_method_transfer.py tests/gis/test_self_extension.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only <base>..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Documentation

Update ADR-019 docs to say:

- layer-E method transfer now has a runtime/gate proof cell;
- the proof transfers a Forman-style graph metric across RasterSpace and
  GeoNetwork neighbor adapters;
- codegen rendering is still intentionally absent;
- this is not full ORC/TDA, not spatial validation, and not scientific method
  discovery.

## Handoff

Owner: Codex.

Next phase after this should be either:

- `spatial_method_transfer` codegen template support, if the runtime cell proves
  stable; or
- Evidence Foundry Challenge Harness Phase 2, following the roadmap queue.
