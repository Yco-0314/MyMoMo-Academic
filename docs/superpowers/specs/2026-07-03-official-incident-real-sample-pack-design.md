# Official Incident Real Sample Pack Phase 1 Design

**Date:** 2026-07-03
**Roadmap lane:** GISABM Real-Data Validity

## Summary

Add a bounded real official road-closure sample pack for the incident line. The
pack uses King County Emergency Management's public `RoadClosures_public`
ArcGIS FeatureServer, stores a small raw JSON sample in the repo, prepares one
or more timestamped closure intervals, maps them to deterministic simulation
ticks through the existing `_official_incident_clock.py` bridge, then verifies
that the generated tick events can feed the existing incident intake and dynamic
incident event-effect smoke.

This is the first real official incident-data sample after the synthetic
official-style incident fixtures. It strengthens data provenance, timestamp
semantics, and auditability. It does not claim traffic-flow validity, production
map matching, route-choice validation, incident calibration, full feed support,
or optimal incident management.

## Data Source

Use the public King County Emergency Management road closures service:

- Service:
  `https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/RoadClosures_public_6e0ca9e8f25344ffa4c4a11b305884c3/FeatureServer`
- Layer: `1` / `Closures`
- Geometry: `esriGeometryPolyline`
- CRS: Web Mercator, `EPSG:3857`
- Relevant fields:
  - `OBJECTID`
  - `street`
  - `reason`
  - `laneimpact`
  - `accessallowed`
  - `description`
  - `starttime`
  - `endtime`
  - `activeincid`
  - `globalid`
  - `geometry.paths`

The committed sample must be bounded and deterministic: a saved raw ArcGIS JSON
response, not a live query during tests. The recommended first record is a
non-test closure with both `starttime` and `endtime` populated, such as a
landslide or water-over-roadway closure. Records whose description contains
`TEST` must be rejected by the pack gate.

## Architecture

Add one GIS-only module:

`abm_auto/gis/_official_incident_real_sample.py`

The module owns:

1. real-sample manifest loading and validation;
2. raw ArcGIS JSON checksum verification;
3. conversion from ArcGIS epoch-millisecond closure features to timestamped
   interval rows;
4. conversion from closure polyline to a representative point by using the
   midpoint of the first segment in the raw Web Mercator geometry;
5. delegation to `_official_incident_clock.py` for timestamp-to-tick mapping;
6. delegation to `_official_incident_intake.py` for tick-event CSV parsing and
   edge matching;
7. delegation to `_official_incident_validation.py` or
   `_official_incident_repro.py` for dynamic incident event-effect evidence;
8. a single cautious real-sample repro gate.

No existing incident intake contract changes. The existing prepared event CSV
schema remains `event_id,x,y,t,closed,...`. The real-sample pack may generate or
validate that prepared CSV, but the downstream modules still see the same
tick-based incident events.

## Files

Create:

- `abm_auto/gis/_official_incident_real_sample.py`
- `tests/gis/test_official_incident_real_sample.py`
- `data/fixtures/official-incident-events/king-county-road-closures-sample/README.md`
- `data/fixtures/official-incident-events/king-county-road-closures-sample/raw.json`
- `data/fixtures/official-incident-events/king-county-road-closures-sample/timestamped_events.csv`
- `data/fixtures/official-incident-events/king-county-road-closures-sample/prepared_events.csv`
- `data/fixtures/official-incident-events/king-county-road-closures-sample/clock_manifest.json`
- `data/fixtures/official-incident-events/king-county-road-closures-sample/intake_manifest.json`
- `data/fixtures/official-incident-events/king-county-road-closures-sample/repro_manifest.json`

Modify:

- `docs/reproduce/coupled-seam/STATUS.md`
- `docs/reproduce/coupled-seam/ADR-019-SYNTHESIS.md`

Do not modify:

- `abm_auto/runtime/`
- `abm_auto/codegen/`
- `abm_auto/calibration/`
- `abm_auto/agents/`
- `abm_auto/pipeline/`

## Manifest Contract

Add schema:

`abm-auto/official-incident-real-sample-repro/v1`

The repro manifest should include:

```json
{
  "schema": "abm-auto/official-incident-real-sample-repro/v1",
  "dataset": "King County RoadClosures_public bounded closure sample",
  "source_url": "https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/RoadClosures_public_6e0ca9e8f25344ffa4c4a11b305884c3/FeatureServer/1",
  "source_agency": "King County Emergency Management",
  "license": "King County public road-closure service terms; bounded sample for reproducibility tests",
  "downloaded_at": "2026-07-03",
  "raw_arcgis_path": "raw.json",
  "raw_arcgis_sha256": "<sha256>",
  "clock_manifest_path": "clock_manifest.json",
  "intake_manifest_path": "intake_manifest.json",
  "expected": {
    "expected_raw_features": 1,
    "expected_timestamped_intervals": 1,
    "expected_tick_events": 2,
    "expected_matched_incidents": 2,
    "expected_dynamic_changed": true
  },
  "boundary_note": "Bounded real official road-closure sample only; not traffic-flow validity, not production map matching, not route-choice validation, not incident calibration, and not a full live feed."
}
```

The exact SHA-256 values are generated during implementation after the fixture
files are committed into their final form.

## Raw-To-Prepared Rules

The conversion function must:

- require a JSON object with `features`;
- require at least one feature;
- reject features whose description contains `TEST` case-insensitively;
- require `OBJECTID` or `globalid`;
- require `starttime` and `endtime`;
- reject `endtime <= starttime`;
- require `geometry.paths` with at least one path and at least two vertices;
- compute the representative `x,y` from the midpoint of the first segment of
  the first path;
- convert epoch-millisecond timestamps to ISO-8601 UTC strings;
- create `incident_id` from `globalid` if present, else `OBJECTID`;
- preserve street/reason/lane/access/description metadata in the timestamped
  CSV raw columns.

The timestamped CSV then feeds `_official_incident_clock.py`.

## Clock And Intake Rules

The clock manifest uses the existing schema:

`abm-auto/official-incident-clock-map/v1`

Default settings:

- `tick_seconds`: `3600`
- `simulation_start`: the top of the UTC hour at or before the first
  `started_at`
- `start_rounding`: `floor`
- `end_rounding`: `ceil`

The prepared intake manifest uses the existing schema:

`abm-auto/official-incident-event-intake/v1`

It points at `prepared_events.csv`, records CRS `EPSG:3857`, and uses a local
synthetic `GeoNetwork` built from the real closure geometry plus a detour edge.
This keeps the gate deterministic and avoids claiming production map matching.

## Runtime API

Expose:

```python
OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_SCHEMA
OFFICIAL_INCIDENT_REAL_SAMPLE_REPRO_MANIFEST
load_official_incident_real_sample_manifest(path) -> dict
verify_official_incident_real_sample_checksums(manifest) -> dict
load_arcgis_closure_features(path) -> list[dict]
prepare_arcgis_closure_timestamp_rows(features) -> list[dict]
official_incident_real_sample_report(manifest_path=...) -> dict
official_incident_real_sample_gate(manifest_path=...) -> tuple[bool, str]
```

The report includes:

- `ok`
- `reason`
- `manifest`
- `checksum`
- `n_raw_features`
- `n_timestamped_intervals`
- `clock_report`
- `intake_report`
- `dynamic_report`
- `summary`
- `boundary_note`

## Gate Semantics

`official_incident_real_sample_gate(...)` passes only when:

- raw checksum passes;
- raw JSON has the expected feature count;
- timestamp preparation produces the expected interval count;
- clock report passes and produces expected tick-event count;
- intake report passes and matches expected incident count;
- dynamic event-effect smoke passes and reports changed output;
- gate text includes cautious boundary language.

This proves a real official closure sample can move through the pipeline:

```text
ArcGIS raw JSON
-> timestamped closure interval
-> deterministic simulation ticks
-> prepared incident event CSV
-> edge-matched incident events
-> dynamic incident event-effect smoke
```

It does not prove the route, edge, or closure effect is scientifically correct
for King County traffic.

## Tests

Add `tests/gis/test_official_incident_real_sample.py` covering:

- manifest load resolves all local paths and validates schema;
- checksum verification passes for the committed raw sample;
- raw ArcGIS JSON loader returns the expected feature count;
- timestamp preparation converts epoch milliseconds to ISO UTC strings;
- TEST descriptions are rejected;
- missing `endtime` fails;
- bad geometry fails;
- real-sample report passes and includes clock/intake/dynamic subreports;
- real-sample gate passes with explicit boundary text;
- expected count mismatch fails with a deterministic reason.

Run:

```bash
.venv/bin/python -m pytest tests/gis/test_official_incident_real_sample.py -q
.venv/bin/python -m pytest tests/gis/test_official_incident_real_sample.py tests/gis/test_official_incident_clock.py tests/gis/test_official_incident_intake.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only <base>..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Documentation

Update the ADR-019 coupled-seam docs to record:

- this is the first bounded real official incident sample pack;
- it builds on the timestamp clock bridge;
- it improves real-data auditability;
- it is not traffic-flow validity, production map matching, route-choice
  validation, or incident calibration.

## Handoff

Owner: Codex.

Claude should not take over this pack unless Codex stops at a limit boundary and
hands off through `docs/agent-handoff-protocol.md`. Claude remains owner of
paper reproduction payloads and private addenda, not this public incident sample
pack.
