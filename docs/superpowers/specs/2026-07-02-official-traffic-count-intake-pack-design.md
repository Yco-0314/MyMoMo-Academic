# Official Traffic Count Intake Pack Phase 1 Design

**Status:** Design for implementation plan.
**Date:** 2026-07-02
**Scope:** Add a manifest-backed intake pack for an externally prepared official
traffic-count dataset, starting with Caltrans AADT / Traffic Census data.

## Summary

MyMoMo already has a local traffic-count bridge: station rows can be loaded,
matched to `GeoNetwork` edges, aggregated into observed edge targets, and checked
with explicit match diagnostics. The next useful real-data step is not another
synthetic fixture. It is a small intake contract for official traffic-count
data that records provenance, local preparation, checksums, CRS, and diagnostic
quality before the data is allowed to influence validation or calibration.

Phase 1 targets Caltrans Traffic Census / AADT because it is an official public
traffic-count source, it exposes annual average daily traffic and GIS-oriented
data, and it maps directly onto the existing edge-load validation bridge.

## Source Candidates

### Primary: Caltrans AADT / Traffic Census

- Official source page:
  `https://dot.ca.gov/programs/traffic-operations/census`
- Why primary:
  - official transportation source;
  - AADT is already an edge-load-like observed metric;
  - current MyMoMo traffic-count bridge already expects point stations with
    counts and map-match diagnostics;
  - a small district or corridor slice can be prepared outside git.

### Secondary: GHSL / WorldPop Population Rasters

- GHSL official data tools:
  `https://human-settlement.emergency.copernicus.eu/GHSLDataTools.php`
- WorldPop data hub:
  `https://hub.worldpop.org/`
- Why secondary:
  - useful for observed-raster validation and calibration;
  - but raster download, clipping, CRS, resolution, and license/provenance are
    more complex than the traffic-count path;
  - should follow after the official traffic-count intake contract is proven.

## Design

Add a new official-data intake pack around the existing traffic-count repro
helpers. The pack should not commit official data. It should commit only schema,
example manifests, tiny synthetic fixtures, and docs that tell a reviewer how to
prepare and validate a local official slice.

The implementation should add a new small module, likely
`abm_auto/gis/_official_traffic_intake.py`, that validates an intake manifest and
summarizes provenance. It should reuse existing traffic-count loading and
matching helpers instead of creating a parallel traffic pipeline.

## Manifest Contract

The official intake manifest should include:

- `schema`: `abm-auto/official-traffic-count-intake/v1`
- `dataset`: human-readable dataset name, for example `Caltrans 2024 AADT`
- `source_url`: official data source page
- `source_agency`: for example `California Department of Transportation`
- `license`: public use / attribution statement recorded from the source
- `downloaded_at`: ISO date when the user downloaded the raw file
- `raw_local_path`: local absolute or relative path to the raw official file;
  not committed
- `raw_sha256`: checksum of the raw downloaded file
- `prepared_csv_path`: path to the prepared station CSV consumed by MyMoMo;
  not committed unless it is a tiny synthetic fixture
- `prepared_sha256`: checksum of the prepared CSV
- `preparation_steps`: ordered list of human-readable commands or actions used
  to produce the prepared CSV
- `crs`: CRS of the prepared coordinates, matching the target `GeoNetwork`
- `columns`: mapping for station id, x, y, count, and optional metadata columns
- `count_metric`: for example `AADT`
- `year`: data year
- `geographic_scope`: district, corridor, county, bbox, or route slice
- `max_distance_m`: map-matching tolerance
- `aggregation`: `sum` or `mean`
- `expected_min_coverage`: minimum accepted match coverage
- `expected_max_match_distance_m`: maximum accepted snapped distance
- `boundary_note`: explicit statement that this validates official-data intake
  and map-match quality, not traffic-flow realism.

## Prepared CSV Contract

The prepared CSV should be the narrow interface between official data and
MyMoMo. It should include at least:

```text
station_id,x,y,count
```

Optional columns can preserve official identifiers:

```text
station_id,x,y,count,route,postmile,direction,county,raw_record_id
```

The implementation should not hide projection, route/postmile conversion, or
station filtering. If the source file does not provide usable coordinates, the
preparation step must say how coordinates were derived. If that derivation is
manual or lossy, the manifest must record it.

## Gate

Add `official_traffic_count_intake_gate(manifest_path, geonet=None)`:

- loads and validates the manifest;
- verifies raw and prepared checksums when files are present;
- loads prepared station rows through existing traffic-count helpers;
- matches rows to a synthetic or provided `GeoNetwork`;
- returns explicit diagnostics:
  - number of stations;
  - matched stations;
  - coverage;
  - mean and max match distance;
  - duplicate edge groups;
  - source agency, dataset, year, scope, and metric;
  - boundary note.

The gate should pass only when manifest validity, checksum validity, and match
quality thresholds pass. It must not claim traffic-model validity or optimal
routing validity.

## Docs And Fixtures

Add:

- `data/fixtures/official-traffic-counts/manifest.example.json`
- `data/fixtures/official-traffic-counts/test_manifest.json`
- `data/fixtures/official-traffic-counts/test_counts.csv`
- `data/fixtures/official-traffic-counts/README.md`
- optional `docs/reproduce/official-traffic-count-intake/STATUS.md`

The committed `test_counts.csv` should remain synthetic and tiny. The README
should explain how to download Caltrans data externally, prepare a local CSV,
compute checksums, and run the gate. Official raw files and large prepared CSVs
remain out of git.

## Integration Points

- Existing bridge: `abm_auto/gis/_traffic_count_repro.py`
- Existing station loader: `abm_auto/gis/_traffic_counts.py`
- Existing tests: `tests/gis/test_traffic_count_repro.py`
- Existing architecture docs:
  - `docs/reproduce/coupled-seam/STATUS.md`
  - `docs/reproduce/coupled-seam/ADR-019-SYNTHESIS.md`

Phase 1 should be additive and should not touch forbidden base-engine paths.

## Non-Goals

- No remote download inside tests.
- No committed official Caltrans data.
- No automatic CRS reprojection in the intake validator.
- No full map matching or route/postmile geocoding engine.
- No traffic-flow validity claim.
- No SUMO/MATSim bridge.
- No changes to `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, or `abm_auto/pipeline`.

## Test Plan

- Manifest validation accepts a complete official-style fixture.
- Manifest validation rejects missing source URL, missing agency, missing
  checksums, invalid year, invalid thresholds, unknown aggregation, and missing
  boundary note.
- Checksum validation detects a changed raw or prepared file when the file is
  present.
- Prepared CSV loading reuses the existing traffic-count station loader.
- Gate passes on a tiny synthetic official-style fixture with deterministic
  match diagnostics.
- Gate fails when coverage is below `expected_min_coverage`.
- Gate fails when max match distance exceeds
  `expected_max_match_distance_m`.
- Docs mention that official data is externally prepared and not committed.

## Acceptance Criteria

- A reviewer can prepare a small Caltrans AADT slice locally and point a
  manifest at it.
- The manifest records source, agency, license, year, scope, CRS, checksums, and
  preparation steps.
- The gate emits explicit match diagnostics and boundary text.
- Existing traffic-count repro tests still pass.
- `docs/reproduce/coupled-seam/STATUS.md` records this as official-data intake
  plumbing, not a traffic-flow validation result.
- Forbidden base-engine diff remains empty.

## Implementation Priority

1. Manifest validator and checksum helper.
2. Tiny synthetic official-style fixture.
3. Gate that reuses existing traffic-count matching and diagnostics.
4. README and status update.
5. Full GIS targeted tests and engine oracle.
