# Traffic Count Edge Matching Design

## Summary

Add a minimal traffic-count ingestion and edge-matching bridge for the existing
network observed validation seam. This phase turns local count-station CSV rows
into edge-keyed `ObservedNetworkTarget` values by assigning each station to the
nearest `GeoNetwork` edge within a caller-provided distance tolerance.

This is a GIS-only additive bridge. It does not download traffic data, reproject
station coordinates, parse OSM, infer routes, map-match trajectories, calibrate
road capacity, or prove traffic-flow realism.

## Runtime API

Create `abm_auto/gis/_traffic_counts.py`.

- `TrafficCountStation`
  - stores `station_id`, `x`, `y`, and non-negative `count`;
  - rejects blank ids, bools, non-finite coordinates, non-finite counts, and
    negative counts.
- `TrafficCountEdgeMatch`
  - stores `station_id`, normalized undirected `edge`, `distance_m`, and
    `count`;
  - records the nearest edge selected for each station.
- `load_traffic_count_csv(path, id_col="station_id", x_col="x", y_col="y", count_col="count")`
  - reads local CSV rows with the standard library;
  - returns stations in file order;
  - rejects missing columns and invalid row values.
- `match_traffic_counts_to_edges(geonet, stations, max_distance_m)`
  - builds each road edge geometry from node `x`/`y` attributes;
  - assigns each station to the nearest edge;
  - breaks equal-distance ties deterministically by edge `repr`;
  - rejects empty station lists, non-positive/invalid tolerance, invalid
    `GeoNetwork`, empty networks, and stations with no edge within tolerance.
- `observed_network_from_traffic_counts(geonet, stations, max_distance_m, source, dataset, metric="edge_load", aggregation="sum")`
  - matches stations to edges;
  - aggregates duplicate station counts on the same edge with `sum` or `mean`;
  - returns an `ObservedNetworkTarget` consumable by
    `network_validation_gate(...)` and `grid_search_network_calibration(...)`.
- `traffic_count_edge_matching_gate()`
  - uses a synthetic `GeoNetwork` and local station rows;
  - proves the count station is assigned to the intended edge and that the
    resulting observed target can pass network validation;
  - states the boundary clearly: nearest-edge count ingestion, not traffic-flow
    calibration and not full map matching.

## Data Rules

Coordinates are assumed to already be in the same CRS and units as the
`GeoNetwork`. Phase 1 performs no reprojection and no hidden resampling. The
distance field is named `distance_m` because the intended CRS is metric, but the
code does not attempt to infer whether the CRS is truly projected.

Station counts are non-negative finite numbers. Zero counts are allowed.

Edge keys follow the existing observed-network rule: undirected 2-tuples sorted
with stable `repr` ordering.

## Out Of Scope

- remote traffic-count downloads;
- official traffic dataset fixtures;
- CRS transformation between station files and road networks;
- OSM/road shapefile ingestion;
- GPS trajectory map matching;
- count-station snapping by road class, direction, lane, bearing, or side of
  road;
- OD estimation, route inference, BPR/capacity calibration, congestion validity;
- codegen templates.

## Success Criteria

- CSV rows become ordered `TrafficCountStation` objects;
- malformed CSVs and invalid numeric values fail clearly;
- stations match deterministically to nearest road edges within tolerance;
- too-far stations fail instead of silently disappearing;
- duplicate stations on one edge aggregate deterministically;
- the resulting `ObservedNetworkTarget` works with existing
  `network_validation_gate(...)`;
- docs record that this closes count-station ingestion Phase 1 only, not real
  traffic-flow calibration.
