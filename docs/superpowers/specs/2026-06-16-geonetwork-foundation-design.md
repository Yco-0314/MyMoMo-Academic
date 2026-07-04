# GeoNetwork Foundation — Design Spec

**Status:** Draft (brainstorming output, pre-plan)
**Date:** 2026-06-16
**Author:** Cong Yu + Claude
**Repo:** MyMoMo-GIS-Academic (GIS developed here; the published abm-auto stays stable)
**Parent spec:** [GIS Mode](2026-06-16-gis-mode.md) — this is the first *vector/real-GIS* sub-project.

---

## 1. Goal & scope

Build the **shared real-GIS substrate** (CRS/datum correctness + vector data loading)
and the **first vector space — GeoNetwork** (a geo-referenced road network),
validated by a handcrafted road-network reference model + a gate. Deterministic,
no LLM. **Zero changes** to the existing path (additive; reuses the runtime
`Network` by composition, exactly as Sub-project A reused `Grid`).

**Why this, why now** (grounded in COMSES): road-network GIS-ABMs are real,
published, and reproducible there — e.g. *Transport simulation in a real road
network* (Ge & Polhill 2016, JASSS 19(3), Aberdeen; NetLogo + GIS road shapefile).
That spatial type is exactly the user's `路网 + 风险点` data. This foundation
unblocks both: reproducing such papers, and the user's real China road-network
research (which is the GCJ-02 datum case).

**In scope:** CRS/datum layer · vector (shapefile) loader · GeoNetwork space +
ops · a handcrafted road-network reference model · a behavioural gate · map output ·
running the GCJ-02 verifier on the user's real road data.

**Out of scope (later sub-projects):** the *faithful* Ge & Polhill reproduction;
polygon `VectorSpace`; autonomous codegen (Sub-project B). Raster GIS-ABMs
(LogoClim, MedLanD) are already reachable via Sub-project A's `RasterSpace`.

---

## 2. Hard constraints

1. **Zero changes to `abm_auto/runtime/`.** GeoNetwork composes the runtime
   `Network`; base `engine_oracle.py --science`/`--check` stay green (Task verifies).
2. **CRS-agnostic / reprojection-first.** Carry each dataset's real CRS; reproject
   via `pyproj`. **GCJ-02 / BD-09** get a dedicated, pluggable correction — `pyproj`
   cannot do them (state-secret nonlinear transform).
3. **GIS deps under the `[gis]` extra**, lazy-imported. This sub-project adds
   `geopandas` + `shapely` (and `fiona`) to the extra, alongside `rasterio`/`pyproj`.

---

## 3. Components

### 3.1 CRS / datum layer — `abm_auto/gis/_crs.py`
- `reproject(xs, ys, src_crs, dst_crs)` via `pyproj.Transformer` (standard EPSG/ESRI).
- `gcj02_to_wgs84(lon, lat)`, `wgs84_to_gcj02(lon, lat)`, `bd09_to_gcj02(...)` — the
  China datum transforms (self-contained implementation; not in PROJ).
- `looks_like_gcj02_mislabeled(points, reference_points) -> (bool, float)` — a
  heuristic: if a layer declares WGS-84 but its points sit a consistent ~50–500 m
  off a known-true reference, flag it (median offset returned). For the user's road
  data, the reference is an OSM/known-true sample for the same city.

### 3.2 Vector data loader — `abm_auto/gis/_vector_io.py`
- `load_vector(path) -> VectorLayer` (geometries [shapely] + CRS + attributes).
  Lazy `import geopandas`. Handles **lines** (roads) and **points** (risk points).
- Honour the shapefile's `.cpg`/`.dbf` **encoding** (Chinese attributes → GBK/UTF-8).

### 3.3 GeoNetwork space — `abm_auto/gis/_geo_network.py`
- `GeoNetwork.from_roads(line_layer, crs_target, snap_tol)` → builds a
  geo-referenced graph: **nodes = segment endpoints** deduplicated/snapped within
  `snap_tol` (road endpoints rarely coincide exactly); **edges = road segments**
  carrying real coordinates + **metric length** (in `crs_target`'s metres).
- Composes the runtime `Network` for topology; GeoNetwork owns coords/CRS/lengths.
- Ops: `nearest_node(x, y)`, `snap_point(geom)`, `network_distance(a, b)` (shortest
  path on metric edge weights via `networkx`), `edge_length(a, b)`.
- Agents are `NetworkAgent`s on nodes (reused, unchanged).

### 3.4 Handcrafted road-network reference model — `abm_auto/gis/_road_model.py`
- A simple deterministic road ABM: agents route from a source node to a destination
  along shortest paths; edge **load** accumulates as agents traverse. Seeded RNG.
- The gateable reference (the GeoNetwork analogue of Sub-project A's raster-SIR).

### 3.5 GeoNetwork gate — `abm_auto/gis/_geo_gate.py`
- Deterministic behavioural signature, concretely:
  1. **reachability** — every routed agent reaches its destination (finite path);
  2. **load concentrates on high-betweenness edges** — corr(edge_load,
     edge_betweenness) > 0 (traffic piles on central roads, not random edges);
  3. **trip metric distance ≈ network distance** (≥ straight-line, ≤ a sane factor).

### 3.6 Map output — `abm_auto/gis/_geo_viz.py`
- Plot edges as lines at real coords, node/edge load as colour/width; agents
  optional. `matplotlib` headless, no basemap.

---

## 4. Validation

- **Unit tests on synthetic small networks** built in-test (no external data) — like
  Sub-project A wrote its own GeoTIFFs.
- **The user's China road shapefile** (`zyd/Data/shp/路网*`): run
  `looks_like_gcj02_mislabeled` against an OSM/known sample; **document the verdict**
  (true WGS-84 vs mislabeled GCJ-02). Do **not** commit the 16 MB set — use a tiny
  clipped subset or an external path with provenance.
- **Zero-change:** base `engine_oracle.py --science` + `--check` green; base suite
  no regressions.

---

## 5. Risks (GeoNetwork-specific)

| Risk | Mitigation |
|---|---|
| Road endpoints don't coincide → fragmented graph | explicit `snap_tol`; documented; tested |
| GCJ-02 detection is heuristic | the verifier flags suspicion (needs a reference); it does not silently auto-fix |
| Chinese attribute encoding (.dbf/.cpg) | honour the codepage; test GBK + UTF-8 |
| geopandas/fiona (GDAL) install | under `[gis]` extra; verify install like rasterio did (it worked cleanly) |
| 16 MB real data too big to commit | tiny clipped subset or external path + provenance |

---

## 6. Decomposition

One buildable sub-project. Anticipated TDD tasks for writing-plans:
1. extend `[gis]` extra (+ geopandas/shapely) ·
2. CRS/datum layer (reproject + GCJ-02 transforms) ·
3. GCJ-02 mislabel verifier ·
4. vector loader (lines/points, encoding) ·
5. GeoNetwork build (snap + metric edges) ·
6. GeoNetwork ops (nearest/snap/network distance) ·
7. handcrafted road model ·
8. GeoNetwork gate ·
9. map output ·
10. run the verifier on the user's real road data + end-to-end + zero-change proof.

## 7. Next sub-projects (after this foundation)

- **Faithful Ge & Polhill 2016 reproduction** on GeoNetwork (real Aberdeen data;
  NetLogo headless as the oracle, via the existing `netlogo_oracle.py` path).
- **Polygon `VectorSpace`** — when a chosen COMSES model needs regions.
- **Sub-project B** (autonomous "one sentence → GIS model") — last.
