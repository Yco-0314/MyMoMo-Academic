# Traffic Count Repro Pack And Diagnostics Design

## Summary

Add a manifest-backed local traffic-count reproducibility pack and explicit match
diagnostics on top of the existing traffic-count edge matching bridge.

This phase turns a local manifest plus local CSV count-station file into:

- validated `TrafficCountStation` rows;
- deterministic nearest-edge matches against a caller-provided `GeoNetwork`;
- an `ObservedNetworkTarget`;
- a diagnostics report that explains match quality and duplicate edge grouping;
- a deterministic gate proving the manifest-backed path can feed network
  validation.

This is not an official traffic-data download, not full map matching, not CRS
reprojection, and not traffic-flow or capacity calibration.

## Runtime API

Create `abm_auto/gis/_traffic_count_repro.py`.

- `DEFAULT_TRAFFIC_COUNT_MANIFEST`
  - points at `data/fixtures/traffic-counts/test_manifest.json`.

- `load_traffic_count_manifest(path)`
  - reads a JSON object;
  - resolves `csv_path` relative to the manifest file;
  - validates required fields:
    - `csv_path`
    - `dataset`
    - `source_url`
    - `license`
    - `crs`
    - `columns`
    - `max_distance_m`
    - `aggregation`
    - `expected_edge_values`
  - keeps optional `description`;
  - rejects missing local CSV files;
  - performs no CRS reprojection.

- `load_traffic_count_stations_from_manifest(path)`
  - loads the manifest;
  - passes manifest column names to `load_traffic_count_csv(...)`;
  - returns stations plus manifest metadata.

- `traffic_count_match_diagnostics(geonet, stations, matches, max_distance_m)`
  - returns explicit, deterministic match diagnostics:
    - `n_stations`
    - `matched_stations`
    - `unmatched_stations`
    - `coverage`
    - `max_distance_m`
    - `mean_distance_m`
    - `max_match_distance_m`
    - `matched_edges`
    - `duplicate_edge_groups`
  - accepts only matches produced for the provided stations;
  - does not hide failed matches. If a match call raises because a station is too
    far from every edge, callers must surface that error.

- `observed_network_from_traffic_count_manifest(geonet, manifest_path)`
  - loads manifest and stations;
  - calls `match_traffic_counts_to_edges(...)`;
  - calls `observed_network_from_traffic_counts(...)`;
  - returns:
    - `observed`
    - `stations`
    - `matches`
    - `diagnostics`
    - manifest provenance fields.

- `traffic_count_repro_gate(manifest_path=DEFAULT_TRAFFIC_COUNT_MANIFEST)`
  - builds a synthetic `GeoNetwork` matching the committed fixture;
  - loads the manifest-backed CSV;
  - verifies produced observed edge values equal manifest `expected_edge_values`;
  - verifies diagnostics coverage and duplicate edge grouping;
  - calls `network_validation_gate(...)`;
  - pass text states the boundary:
    - manifest-backed local traffic-count repro pack;
    - not official traffic-data download;
    - not full map matching;
    - not traffic-flow calibration.

## Manifest Shape

The local manifest is JSON:

```json
{
  "csv_path": "test_counts.csv",
  "dataset": "local-test-traffic-counts",
  "source_url": "local://data/fixtures/traffic-counts",
  "license": "local test fixture; not official traffic data",
  "crs": "EPSG:3857",
  "columns": {
    "id": "station_id",
    "x": "x",
    "y": "y",
    "count": "count"
  },
  "max_distance_m": 1.0,
  "aggregation": "sum",
  "expected_edge_values": {
    "(0, 0)|(10, 0)": 100.0,
    "(0, 10)|(10, 10)": 40.0
  },
  "description": "Tiny local count-station fixture for manifest plumbing."
}
```

The manifest stores `expected_edge_values` with string edge keys because JSON
cannot preserve tuple node ids. The repro module will parse keys in the stable
`repr(node_a)|repr(node_b)` format used only by this manifest layer, then pass
normalized tuple keys into `ObservedNetworkTarget`.

## Fixture Pack

Add `data/fixtures/traffic-counts/`:

- `test_counts.csv`
  - tiny local count station rows near a synthetic projected `GeoNetwork`;
  - includes duplicate stations on one edge to prove aggregation diagnostics.
- `test_manifest.json`
  - automated-test manifest for the local fixture.
- `manifest.example.json`
  - template showing how a user can point to a human-downloaded traffic-count
    CSV without changing runtime code.
- `README.md`
  - explains that no official traffic data is committed;
  - documents how to download/prepare a real traffic-count CSV externally;
  - states that CRS alignment must be explicit before using this phase.

## Data Rules

All station coordinates must already be in the same CRS and units as the
`GeoNetwork`. The manifest records `crs` for provenance and sanity checks only;
Phase 1 does not reproject or resample anything.

Counts must be non-negative finite numbers. `aggregation` is limited to `sum`
and `mean`, matching the existing traffic-count bridge.

## Out Of Scope

- remote or authenticated data downloads;
- committed official traffic-count datasets;
- road-network ingestion from OSM/shapefiles;
- CRS transformation between station CSV and road network;
- bearing, lane, side-of-road, direction, or road-class matching;
- GPS trajectory map matching;
- OD estimation, BPR/capacity calibration, congestion validity;
- codegen templates.

## Success Criteria

- manifest loader resolves relative CSV paths and rejects malformed manifests;
- manifest-backed CSV loading uses manifest column names;
- diagnostics report station count, coverage, distance summary, matched edge
  count, and duplicate edge groups;
- manifest-backed observed target equals expected manifest edge values;
- gate proves the manifest-backed path reaches `network_validation_gate`;
- docs record that this is local reproducibility plumbing, not official data or
  traffic-flow calibration.
