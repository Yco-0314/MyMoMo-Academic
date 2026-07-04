# Official Traffic Count Repro Pack Phase 2 Design

## Summary

Phase 2 turns the official traffic-count intake seam into a small, committed
real-data repro pack. The first source is Seattle Department of Transportation
Traffic Study Flow Counts, exposed through Seattle's public ArcGIS Open Data
Feature Service.

The pack is intentionally small. It stores a bounded public sample, a prepared
CSV, a manifest with checksums, and explicit edge-match diagnostics. The gate
proves that MyMoMo can ingest an official traffic-count sample, validate local
provenance, match count points to a `GeoNetwork`, and report match quality. It
does not prove traffic-flow validity, congestion calibration, route assignment,
or full production map matching.

## Source

- Dataset: Seattle SDOT Traffic Study Flow Counts.
- Open data item:
  `https://data-seattlecitygis.opendata.arcgis.com/api/search/v1/collections/dataset/items/0f8fcff4d1e04ae7abbda101b6013a52`
- Feature Service:
  `https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/Traffic_Study_Flow_Counts/FeatureServer`
- Layer:
  `https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/Traffic_Study_Flow_Counts/FeatureServer/0`
- Access date: 2026-07-02.
- Agency: Seattle Department of Transportation.
- CRS: EPSG:2926, Washington State Plane North, US feet.

The sample query used during design was:

```text
where=STDY_YEAR=2023 AND FLOWMAP='Y'
outFields=*
returnGeometry=true
resultRecordCount=3
f=json
```

The feature layer exposed `STUDY_ID`, `STDY_YEAR`, `FLOWMAP`, `STUDY_ADT`,
street labels, and point geometry. The sample included 2023 FLOWMAP records with
`STUDY_ADT` values 5497, 1164, and 1047 in EPSG:2926 coordinates.

## Architecture

The existing `abm_auto.gis._official_traffic_intake` module remains the owner of
official traffic-count manifests and gates. Phase 2 adds a report function:

```python
official_traffic_count_intake_report(manifest_path, geonet=None) -> dict
```

The report returns structured fields for:

- manifest metadata and source provenance
- checksum status
- station count
- edge-match diagnostics
- observed edge values
- pass/fail state
- failure reason when applicable
- boundary text

`official_traffic_count_intake_gate(...)` becomes a small wrapper over the
report. Existing gate text remains stable in spirit, but failure messages now
come from the structured report so tests and future docs can inspect diagnostics
without parsing prose.

## Real Repro Pack

Add a committed directory:

```text
data/fixtures/official-traffic-counts/seattle-sdot-2023-flowmap/
```

Files:

- `raw_source.json`: the bounded official API sample response.
- `prepared_counts.csv`: normalized station rows with `station_id`, `x`, `y`,
  `count`, and official source columns.
- `manifest.json`: official intake manifest with SHA-256 checksums.
- `README.md`: provenance, source URL, preparation notes, and boundary.

The pack uses a tiny synthetic `GeoNetwork` whose edges pass through the three
real official point coordinates. This keeps tests deterministic while preserving
real official station coordinates and ADT values. The geonet is not claimed to
be Seattle's full road network; it is a deterministic validation harness for the
intake and edge-match seam.

## Validation Behavior

The Phase 2 gate passes only when:

- manifest schema and required fields validate
- raw and prepared SHA-256 checksums match
- `GeoNetwork.crs` equals manifest CRS
- all stations load from the prepared CSV
- all stations match to an edge within `max_distance_m`
- match coverage meets `expected_min_coverage`
- max match distance is no larger than `expected_max_match_distance_m`
- observed edge values match `expected_edge_values`

The report must include `diagnostics` even on threshold failures whenever the
failure happens after station matching. Checksum and CRS failures may return
before matching, but still include manifest and checksum status where available.

## Scope Boundaries

This phase does not:

- download data during tests
- depend on live network availability
- implement a general ArcGIS client
- reproject official coordinates
- infer road geometry from Seattle centerlines
- perform route/postmile geocoding
- calibrate a traffic-flow or congestion model
- update GIS codegen templates
- touch base-engine directories

## Tests

Extend `tests/gis/test_official_traffic_intake.py` to cover:

- committed Seattle pack manifest loads and verifies checksums
- report returns source metadata, diagnostics, and observed edge values
- gate passes on the Seattle pack with boundary text
- checksum mutation fails with a structured reason
- strict match-distance threshold fails with diagnostics preserved
- CRS mismatch fails before matching

The existing synthetic fixture remains. It is still useful for fast malformed
manifest tests and edge-case failures. The Seattle pack becomes the first real
official-data fixture for the official intake seam.

## Documentation Updates

Update `docs/reproduce/coupled-seam/STATUS.md` and
`docs/reproduce/coupled-seam/ADR-019-SYNTHESIS.md` to record that the official
traffic-count bridge now has a manifest-backed real public sample with explicit
match diagnostics.

The docs must state the same boundary as the gate: this proves official-data
intake and edge-match quality plumbing, not traffic-flow validity.
