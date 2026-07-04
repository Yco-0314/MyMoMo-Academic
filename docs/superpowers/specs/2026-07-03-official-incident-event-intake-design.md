# Official Incident Event Intake + Edge Matching Phase 1 Design

## Context

The GIS platform now has three moving-agent dynamic routing mechanisms:

- dynamic flood evacuation,
- dynamic congestion routing,
- dynamic incident routing.

`dynamic_incident_routing` is implemented, gated, routed through the shared
dynamic lifecycle helper, and codegen-renderable. Its incident inputs are still
synthetic Python event dictionaries:

```python
{"t": 1, "edge": (u, v), "closed": True}
```

The traffic-count line already has a stronger real-data pattern:

- manifest-backed official intake,
- checksum and provenance validation,
- local fixture files,
- centerline edge matching,
- explicit diagnostics,
- cautious gate text.

This spec applies that same pattern to incident / closure / road-event rows.

## Goal

Add a small official incident-event intake bridge that loads manifest-backed
local event rows, matches them to `GeoNetwork` edges, reports explicit matching
diagnostics, and emits dynamic-routing-compatible incident dictionaries.

This is a data-intake and edge-matching bridge. It is not a dynamic rerouting
validation run yet.

## Non-Goals

- No remote download in tests or runtime.
- No production geocoder or full map-matching engine.
- No real traffic-flow validity claim.
- No optimal incident-management claim.
- No congestion, capacity, BPR, or travel-time inference.
- No codegen template changes.
- No `CoupledModel` extraction.
- No base-engine edits.

## Architecture

Add a new GIS-only module:

- `abm_auto/gis/_official_incident_intake.py`

The module owns four concerns:

1. Manifest validation.
2. Raw/prepared checksum verification.
3. Incident row loading.
4. Nearest-edge matching plus diagnostics.

It should mirror the style of `_official_traffic_intake.py` and
`_official_centerline_match.py`: small validators, explicit failure reasons,
and a gate that returns `(bool, str)`.

## Manifest Contract

Schema:

```text
abm-auto/official-incident-event-intake/v1
```

Required manifest fields:

- `schema`
- `dataset`
- `source_url`
- `source_agency`
- `license`
- `downloaded_at`
- `raw_local_path`
- `raw_sha256`
- `prepared_events_path`
- `prepared_sha256`
- `preparation_steps`
- `crs`
- `columns`
- `event_time_unit`
- `geographic_scope`
- `max_distance_m`
- `expected_min_coverage`
- `expected_max_match_distance_m`
- `expected_event_edges`
- `boundary_note`

`event_time_unit` must be `tick` in Phase 1. Real timestamp parsing belongs in a
future bridge that defines a simulation-clock mapping explicitly.

`columns` must map:

- `id`
- `x`
- `y`
- `t`
- `closed`

Optional columns can be preserved in row metadata when present, but Phase 1 only
requires the core five fields above.

`expected_event_edges` is keyed by event id and stores the deterministic edge
match plus the normalized event state:

```json
{
  "evt-1": {
    "edge": "(0, 0)|(100, 0)",
    "t": 1,
    "closed": true
  }
}
```

Edge strings use the existing test-manifest convention: `repr(node_a)|repr(node_b)`.
The loader normalizes each pair by `repr` order.

## Prepared Event Rows

Prepared event rows are CSV in Phase 1. Each row becomes an `OfficialIncidentEvent`
value with:

- `event_id`
- `x`
- `y`
- `t`
- `closed`
- `raw`

Validation rules:

- `event_id` is non-empty.
- `x` and `y` are finite numbers.
- `t` is a non-negative integer; bool is rejected.
- `closed` accepts deterministic boolean encodings only:
  - true: `true`, `1`, `yes`, `closed`
  - false: `false`, `0`, `no`, `open`, `reopened`
- duplicate event ids fail.

## Edge Matching

Add:

- `match_incident_events_to_edges(geonet, events, max_distance_m)`

Each event is matched by its point coordinate to the nearest `GeoNetwork` edge,
using the same deterministic nearest-edge style as traffic counts. A match
contains:

- `event_id`
- `edge`
- `distance_m`
- `t`
- `closed`

If an event is farther than `max_distance_m`, matching fails with a clear
`ValueError`. Phase 1 treats distance failure as an intake failure rather than
silently dropping rows.

## Report And Gate

Add:

- `official_incident_event_edge_match_report(manifest_path, geonet=None)`
- `official_incident_event_edge_match_gate(manifest_path, geonet=None)`

The report returns:

- `ok`
- `reason`
- `manifest`
- `checksum`
- `dataset`
- `source_url`
- `source_agency`
- `license`
- `downloaded_at`
- `geographic_scope`
- `boundary_note`
- `n_events`
- `diagnostics`
- `matched_incidents`

When `geonet=None`, the report uses the default synthetic incident detour
network described in the fixture section. Real or official centerline networks
must be passed explicitly by the caller.

Diagnostics include:

- `n_events`
- `matched_events`
- `coverage`
- `matched_edges`
- `max_match_distance_m`
- `mean_match_distance_m`
- `events_by_t`
- `closures`
- `reopenings`
- `unmatched_event_ids`
- `duplicate_edge_groups`

`matched_incidents` is a list of dictionaries directly compatible with
`run_dynamic_incident_routing`:

```python
{"t": t, "edge": edge, "closed": closed}
```

The gate passes only when:

- checksums pass,
- manifest CRS matches the `GeoNetwork`,
- all rows load,
- all events match within `max_distance_m`,
- coverage is at least `expected_min_coverage`,
- max distance is at most `expected_max_match_distance_m`,
- observed event-to-edge assignments match `expected_event_edges`.

Gate text must say this proves official incident-event intake and edge matching
only. It must not claim real traffic-flow validity, production map matching, or
optimal incident management.

## Fixtures

Add fixture directory:

- `data/fixtures/official-incident-events/`

Files:

- `README.md`
- `manifest.example.json`
- `test_manifest.json`
- `test_raw.csv`
- `test_prepared_events.csv`

The committed Phase 1 fixture is synthetic official-style data, matching the
earlier `official-traffic-count-intake` Phase 1 pattern. The manifest must state
that boundary explicitly. A later Phase 2 can commit a bounded real official
incident sample if a stable, license-compatible source is prepared.

Default synthetic network for tests:

- edge A: `(0, 0) -> (100, 0)`
- edge B: `(100, 0) -> (200, 0)`
- detour edge C: `(0, 100) -> (200, 0)`

Prepared events:

- close the direct bottleneck edge at `t=1`
- reopen it at `t=3`

This fixture is selected because it can later feed directly into
`dynamic_incident_routing` without changing event semantics.

## Tests

Add `tests/gis/test_official_incident_intake.py`.

Coverage:

- manifest loads and preserves provenance.
- checksum verification passes for unchanged files.
- checksum verification fails after file mutation.
- malformed schema/source/license/date/checksum/preparation/columns/CRS/tolerance
  fields fail clearly.
- event CSV loader rejects:
  - duplicate ids,
  - non-finite coordinates,
  - bool/non-integer/negative `t`,
  - ambiguous `closed` values.
- edge matching reports full coverage and deterministic event-edge assignments.
- report returns `matched_incidents` compatible with dynamic incident routing.
- gate passes with boundary text.
- gate fails on:
  - CRS mismatch,
  - too-strict max distance,
  - expected event-edge mismatch,
  - checksum mismatch.

Run targeted:

```bash
.venv/bin/python -m pytest tests/gis/test_official_incident_intake.py -q
```

Run final:

```bash
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

## Documentation Updates

Update:

- `docs/reproduce/coupled-seam/STATUS.md`

Record this as an official-data intake bridge for incident events, not as dynamic
rerouting validation. The natural follow-up is Official Dynamic Incident
Validation Smoke Phase 1, which will consume `matched_incidents` and run the
already implemented dynamic incident model on an official or official-style
`GeoNetwork`.

## Open/Closed Boundary

Open-source scope:

- manifest contract,
- checksum/provenance validation,
- local fixture,
- edge matching diagnostics,
- dynamic-routing-compatible incident rows.

Closed or future scope:

- private/full official incident datasets,
- production geocoding or map matching,
- calibrated incident impact models,
- traffic assignment validation,
- unified physical/social simulation strategy docs.
