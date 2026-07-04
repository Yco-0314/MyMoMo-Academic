# Terrain-Aware Routing Gate Phase 1 - Design Spec

## Summary

Add a small terrain-aware routing proof on top of the existing terrain-network
coupling operators. Given a `GeoNetwork`, terrain bridge manifest, source node,
and target node, compare:

- the normal shortest path by edge `length`;
- the shortest path by `terrain_cost_per_edge(...)`.

Add a deterministic gate proving that terrain-derived edge costs can change
route choice on a synthetic network. This is routing-cost evidence only. It does
not model traffic flow, congestion, vehicle dynamics, 3D rendering, hydrology,
or real-world slope validity.

## Why This Is Next

Terrain-to-network coupling already produces edge-level elevation delta, grade
proxy, and cost. The next useful test is whether that cost can affect a network
decision. The smallest meaningful decision is shortest-path routing on an
existing `GeoNetwork`; it exercises the terrain seam without introducing a new
model lifecycle or `CoupledModel`.

## Scope

Modify:

- `abm_auto/gis/_coupling.py`
- `tests/gis/test_terrain_aware_routing.py`
- `docs/reproduce/coupled-seam/STATUS.md`

Do not modify base-engine forbidden paths.

## API

Add to `abm_auto/gis/_coupling.py`:

```python
def terrain_aware_shortest_path(
    geonet,
    terrain_manifest,
    source,
    target,
    *,
    repo=None,
    n_samples=8,
    grade_weight=1.0,
) -> dict:
    ...

def terrain_aware_routing_gate(
    geonet,
    terrain_manifest,
    source,
    target,
    *,
    repo=None,
    n_samples=8,
    grade_weight=1.0,
) -> tuple[bool, str]:
    ...
```

`terrain_aware_shortest_path(...)` returns:

- `length_path`: shortest path using edge `length`;
- `terrain_path`: shortest path using `terrain_cost`;
- `length_path_length_m`;
- `length_path_terrain_cost`;
- `terrain_path_length_m`;
- `terrain_path_cost`;
- `changed_path`;
- `edge_costs`.

Validation:

- source and target must exist in the graph;
- source and target must be different;
- `terrain_cost_per_edge(...)` performs manifest, CRS, extent, sampling, and
  `grade_weight` validation;
- no hidden reprojection or resampling.

## Gate

`terrain_aware_routing_gate(...)` passes only when:

- the terrain-aware path differs from the length-only path;
- the terrain-aware path has lower terrain cost than the length-only path;
- the message includes `terrain changes shortest-path routing`;
- the message includes `not traffic flow, vehicle dynamics, or 3D terrain physics`.

Failure messages report enough route/cost evidence to diagnose whether the
terrain signal was too weak or no alternative route existed.

## Tests

Create `tests/gis/test_terrain_aware_routing.py`:

- synthetic two-route network where length-only chooses the shorter uphill route
  and terrain-aware routing chooses the longer flat detour;
- result includes stable path/cost fields and `changed_path=True`;
- gate passes on the synthetic case with the required boundary text;
- gate fails when `grade_weight=0.0`;
- missing node fails clearly;
- identical source/target fails clearly.

Final verification:

- `.venv/bin/python -m pytest tests/gis/test_terrain_aware_routing.py -q`
- `.venv/bin/python -m pytest tests/gis/test_terrain_aware_routing.py tests/gis/test_terrain_network_coupling.py tests/test_terrain_bridge.py -q`
- `.venv/bin/python -m pytest tests/gis -q`
- `.venv/bin/python engine_oracle.py --science`
- `.venv/bin/python engine_oracle.py --check`
- forbidden base-engine diff check must be empty.

## Boundaries

Do not:

- add a dynamic agent model;
- add congestion, traffic flow, capacity, BPR, or vehicle dynamics;
- claim real-world routing validity;
- create terrain mesh or 3D rendering;
- alter Anshuka or other reproduction bundles;
- add `CoupledModel`;
- touch base-engine forbidden paths.
