# abm_auto.gis — GIS mode

A spatial agent-based-modelling layer for `abm_auto`. It is **additive and
import-isolated**: the GIS libraries are an optional extra, imported lazily, so
the base (non-GIS) install stays light.

```bash
pip install abm-auto[gis]
```

Importing `abm_auto.gis` never pulls in the heavy dependencies; call
`abm_auto.gis.require_gis()` for a clear error if the extra is missing.

## What's in it

**Spaces** — georeferenced, CRS-aware spatial containers:

- `GeoNetwork` (`_geo_network`) — a road/graph network built from line geometries
  (`GeoNetwork.from_lines(...)`), with node snapping and nearest-node lookup.
- `RasterSpace` / `RasterField` (`_raster_space`) — a georeferenced grid wrapping
  the runtime `Grid` for cell topology, with an affine transform + CRS + nodata.
- `PolygonSpace` (`_polygon_space`) — stable region IDs over projected polygons,
  STRtree-indexed point-in-polygon and adjacency.
- `PointSpace` (`_point_space`) — a projected point cloud (`PointSpace.from_coords`).
- `RasterTimeline` (`_temporal`) — a time-indexed stack of raster frames.

**Coupling operators** (`_coupling`) — combine two space layers:

- `flood_depth_per_edge` — max flood depth sampled along each road edge.
- `point_risk_per_edge` — nearby-point counts per edge.
- `polygon_overlap_areas`, `lines_in_polygon` — vector × vector overlays.
- DE-9IM predicates (`intersects`, `contains`, `within`, …) + STRtree-indexed
  `features_intersecting` / `features_containing`.

**Platform layer** (`_platform`) — minimal Mesa-shaped floor abstractions
(`GISAgent`, `GISModel`, `AgentSet`, `DataCollector`) with no Mesa dependency. A
new spatial ABM subclasses `GISAgent` + `GISModel` instead of re-implementing
agent state, a scheduler, a collector, and a run loop by hand. Deterministic:
one seeded RNG chain on the model.

**Dynamic models** built on the platform:

- `run_dynamic_congestion_routing` (`_dynamic_congestion`) — node-starting agents
  routed through a road graph with dynamic congestion costs and rerouting.
- `run_dynamic_flood_evacuation` (`_dynamic_flood`) — agents evacuating over a
  time-varying flood raster, stranding on flooded edges and replanning when blocked.

**Spatial statistics** (`_ops`) — Moran's I and focal operators.

**Codegen** (`_capabilities`, `_templates`, `_codegen_gate`, `_extractor`) — emit a
full `GISAgent`/`GISModel` ABM from a spec, guarded by a deterministic
codegen-fidelity gate (structural checks on generated code, never the generator's
word). Each capability declares its render parameters as a schema, so the
extractor prompt lists the valid params and `GISModelSpec.validate()` rejects
unknown / mistyped / out-of-range values at parse time instead of silently
defaulting.

**Validation** (`_spatial_validation`, `_network_validation`,
`_observed_raster_bridge`) — compare simulated rasters to observed ones and gate
on overlap / centroid / loss metrics.

## Design notes

- **Determinism.** Models seed a single RNG chain; routing uses a deterministic
  Dijkstra with stable `repr`-keyed tie-breaking, so results are reproducible
  regardless of dict/heap ordering.
- **Import isolation.** Heavy/GDAL-adjacent deps (`rasterio`, `pyproj`,
  `geopandas`, `shapely`) live only behind the `[gis]` extra and are imported
  lazily inside the modules that use them.
- **No base-engine edits.** GIS code composes the runtime (`abm_auto.runtime`) and
  calibration seams; it does not modify them.
