# Incident Timestamp-to-Simulation-Clock Bridge Phase 1 Design

## Summary

Add a small manifest-backed clock bridge that converts timestamped incident
interval rows into deterministic tick-based closure/reopen events compatible
with the existing official incident intake and dynamic incident runtime.

This phase does not change the existing `official-incident-event-intake/v1`
contract, which still requires `event_time_unit == "tick"`. Instead, it adds a
separate preparatory bridge that maps `started_at` / `ended_at` timestamps to
the tick events already accepted downstream.

This is timestamp normalization and simulation-clock plumbing only. It is not a
real official incident feed, not traffic-flow validity, not production map
matching, not incident calibration, not route-choice validation, and not
SUMO/MATSim integration.

## Current Context

The current incident line is:

```text
official-style incident CSV with t ticks
-> official_incident_event_edge_match_report(...)
-> official_dynamic_incident_event_effect_report(...)
-> official_dynamic_incident_repro_report(...)
```

That line is reproducible, but it assumes incident rows already have integer
simulation ticks. Real public feeds usually expose timestamps, such as
`started_at` and `ended_at`, not model ticks. The missing bridge is a
deterministic conversion step:

```text
timestamped incident intervals
-> clock map
-> tick closure/reopen event rows
-> existing incident intake
```

## Architecture

Add GIS-only module:

```text
abm_auto/gis/_official_incident_clock.py
```

Schema:

```text
abm-auto/official-incident-clock-map/v1
```

Default fixture manifest:

```python
DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST = Path(
    "data/fixtures/official-incident-events/"
    "timestamp-clock-map/manifest.json"
)
```

Public APIs:

```python
load_official_incident_clock_map_manifest(path) -> dict

load_timestamped_incident_intervals_csv(path, columns, local_utc_offset=None)
    -> list[TimestampedIncidentInterval]

map_incident_intervals_to_tick_events(intervals, clock) -> list[dict]

official_incident_clock_map_report(
    manifest_path=DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST,
) -> dict

official_incident_clock_map_gate(
    manifest_path=DEFAULT_OFFICIAL_INCIDENT_CLOCK_MAP_MANIFEST,
) -> tuple[bool, str]
```

The module should not import or call edge matching. It only maps temporal rows
to tick event dictionaries. The output dictionaries should be directly
serializable to the existing prepared-event CSV shape:

```python
{
    "event_id": "incident-1:close",
    "incident_id": "incident-1",
    "x": 150.0,
    "y": 0.2,
    "t": 1,
    "closed": True,
}
```

The reopen event uses `event_id == "incident-1:reopen"` and `closed == False`.

## Timestamp Policy

Phase 1 supports deterministic timestamp parsing only:

- ISO-8601 timestamps with explicit UTC offsets, for example
  `2026-07-03T08:10:00-07:00`;
- ISO-8601 timestamps without offsets only when the manifest supplies
  `local_utc_offset`, for example `-07:00`;
- no IANA timezone names in Phase 1;
- no daylight-saving ambiguity handling in Phase 1;
- no fuzzy date parsing.

All parsed datetimes are normalized to UTC before tick calculation. This avoids
host-locale and machine-timezone dependence.

## Clock Rule

The manifest clock contains:

- `simulation_start`: ISO timestamp, parsed with the same timestamp policy;
- `tick_seconds`: positive integer, bool rejected;
- `start_rounding`: must be `floor`;
- `end_rounding`: must be `ceil`.

For each interval:

```text
start_tick = floor((started_at - simulation_start) / tick_seconds)
end_tick   = ceil((ended_at   - simulation_start) / tick_seconds)
```

Validation:

- `started_at` must be at or after `simulation_start`;
- `ended_at` must be strictly after `started_at`;
- resulting ticks must be non-negative integers;
- duplicate incident ids fail;
- start and end ticks may be equal only if the interval is shorter than one tick
  and both round to the same tick; in that case the row fails because a close
  and reopen at the same tick has no stable dynamic-runtime meaning in Phase 1.

The bridge deliberately does not clip incidents that start before the simulation
window. Window clipping is a future extension because it changes scientific
interpretation.

## Manifest Contract

Required fields:

- `schema`
- `dataset`
- `source_url`
- `source_agency`
- `license`
- `downloaded_at`
- `timestamped_events_path`
- `timestamped_sha256`
- `preparation_steps`
- `columns`
- `clock`
- `expected_tick_events`
- `boundary_note`

`columns` must map:

- `id`
- `x`
- `y`
- `started_at`
- `ended_at`

`clock` must contain:

- `simulation_start`
- `tick_seconds`
- `local_utc_offset`
- `start_rounding`
- `end_rounding`

`local_utc_offset` may be `null` only when every timestamp has an explicit UTC
offset.

`expected_tick_events` is keyed by generated event id and stores deterministic
event expectations:

```json
{
  "evt-closure:close": {
    "incident_id": "evt-closure",
    "t": 1,
    "closed": true
  },
  "evt-closure:reopen": {
    "incident_id": "evt-closure",
    "t": 3,
    "closed": false
  }
}
```

## Fixture

Add:

```text
data/fixtures/official-incident-events/timestamp-clock-map/
```

Files:

- `README.md`
- `manifest.json`
- `timestamped_events.csv`

Fixture interval:

```csv
incident_id,x,y,started_at,ended_at,description
evt-closure,150,0.2,2026-07-03T08:10:00-07:00,2026-07-03T08:30:00-07:00,Closure interval matching the tick fixture
```

Clock:

```json
{
  "simulation_start": "2026-07-03T08:00:00-07:00",
  "tick_seconds": 600,
  "local_utc_offset": null,
  "start_rounding": "floor",
  "end_rounding": "ceil"
}
```

Expected output:

- `evt-closure:close`, `t=1`, `closed=true`;
- `evt-closure:reopen`, `t=3`, `closed=false`.

This mirrors the existing close-at-1, reopen-at-3 dynamic incident fixture
without changing the downstream intake contract.

## Report And Gate

`official_incident_clock_map_report(...)` returns:

```python
{
    "ok": True,
    "reason": "",
    "manifest": {...},
    "checksum": {...},
    "dataset": "...",
    "source_url": "...",
    "source_agency": "...",
    "license": "...",
    "downloaded_at": "2026-07-03",
    "clock": {...},
    "n_intervals": 1,
    "n_tick_events": 2,
    "tick_events": [...],
    "events_by_t": {1: 1, 3: 1},
    "closures": 1,
    "reopenings": 1,
    "boundary_note": "...",
}
```

Failure reports keep the same top-level fields where possible and include:

- `ok=False`;
- a clear `reason`;
- `tick_events=None` when conversion did not complete.

The gate passes only when:

- checksum passes;
- all intervals parse;
- tick events match `expected_tick_events`;
- at least one close and one reopen event are present;
- gate text states the boundary.

Gate text must explicitly say this proves timestamp-to-tick conversion only,
not real incident validity, traffic-flow validity, production map matching, or
incident calibration.

## Tests

Add `tests/gis/test_official_incident_clock.py`.

Required cases:

- manifest loads and resolves `timestamped_events_path`;
- checksum passes for the committed fixture;
- report produces close `t=1` and reopen `t=3`;
- gate passes with boundary text;
- naive timestamps parse only when `local_utc_offset` is supplied;
- timestamp without offset and without `local_utc_offset` fails;
- bool `tick_seconds` fails;
- `ended_at <= started_at` fails;
- `started_at < simulation_start` fails;
- empty or duplicate incident ids fail;
- expected tick event mismatch fails the report.

Targeted verification:

```bash
.venv/bin/python -m pytest tests/gis/test_official_incident_clock.py tests/gis/test_official_incident_intake.py -q
```

Final verification:

```bash
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

The final diff check must be empty.

## Documentation

Update:

- `docs/reproduce/coupled-seam/STATUS.md`
- `docs/reproduce/coupled-seam/ADR-019-SYNTHESIS.md`

Record the bridge as the deterministic timestamp-to-tick preparation layer
needed before bounded real official incident feeds. It strengthens data
preparation rigor, not dynamic routing validity.

## Non-Goals

- No changes to `official-incident-event-intake/v1`.
- No real official incident feed.
- No edge matching in the clock bridge.
- No production timezone database or DST ambiguity handling.
- No incident window clipping.
- No traffic-flow validity or traffic assignment.
- No route-choice validation.
- No SUMO/MATSim bridge.
- No codegen changes.
- No base-engine edits.
