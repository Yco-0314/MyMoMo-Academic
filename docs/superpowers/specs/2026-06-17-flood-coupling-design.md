# Coupled Seam — Flood Adapter (raster × network) — Design Spec

**Status:** Draft. **Date:** 2026-06-17. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../decisions/ADR-019-gis-abm-platform-vision.md) (this is the
**first adapter** of the coupled multi-layer space seam).

## Goal

Couple a road **network** (`GeoNetwork`) with a flood-depth **raster**
(`RasterSpace`) in one model: an urban-flood evacuation ABM. The one new primitive
is a **raster↔network spatial join** — `flood_depth_per_edge`. Everything else
(GeoNetwork, RasterSpace, routing) already exists.

## The seam (kept minimal — YAGNI)

One adapter does not justify a grand `CoupledSpace` abstraction (one adapter =
hypothetical seam; **two** = real seam — ADR-019). So build the **coupling operator**
+ the flood model now; the shared seam is extracted when the second adapter
(social-GIS) arrives.

## Components

### F1 coupling operator — `abm_auto/gis/_coupling.py`
`flood_depth_per_edge(geonet, flood_raster, n_samples=8) -> {edge: depth}`: for each
edge, sample the flood raster at points along the segment (node coords → raster cell
via `world_to_cell`) and take the **max** depth. **CRS contract:** the network and
the raster must be in the **same CRS** (the model reprojects the raster to the
network's CRS first); sampling out-of-bounds cells = depth 0.

### F2 flood-evacuation model — `abm_auto/gis/_flood_model.py`
`run_flood_evacuation(geonet, flood_raster, threshold, safe_nodes, agent_nodes, seed)`:
edges with depth > `threshold` are removed (impassable); each agent routes to the
nearest reachable safe node on the remaining network; returns
`{stranded, n_agents, mean_detour_m, n_flooded_edges, reached}`. Deterministic.

### F3 flood gate — `abm_auto/gis/_flood_gate.py`
Deterministic behavioural signature: **more flooding → worse evacuation.** Concretely
(1) the flooded run strands ≥ the dry run; (2) stranded count is **monotone
non-decreasing** as the flood threshold drops (more edges flood); (3) mean detour ≥
the dry-network detour. Fails if flooding has no effect.

### F4 map — reuse `_geo_viz.render_network`, flooded edges highlighted (thin extension).

## Validation

- Unit tests on a synthetic grid network + a synthetic flood field (a "river" band
  of high depth) — no external data, like the raster-SIR tests.
- Real-data path: the model accepts the user's Beijing road network + a real flood
  DEM (when provided); the synthetic tests prove the mechanism.
- **Zero-change proof:** base `engine_oracle --science`/`--check` green; the coupling
  reuses RasterSpace/GeoNetwork unchanged (the operator reads them, doesn't modify them).

## Decomposition (TDD)

1. F1 `flood_depth_per_edge` (sample raster along edges; CRS contract; bounds)
2. F2 flood-evacuation model (remove flooded edges, route to safety, stranded/detour)
3. F3 flood gate (more flood → worse; monotone; fails on no-effect)
4. F4 map + synthetic end-to-end + zero-change proof

## Out of scope (later)

Time-varying flood (depth series per tick), the extracted `CoupledSpace` seam (at
the 2nd adapter), codegen coverage of coupled models, calibration to observed flood
extent.
