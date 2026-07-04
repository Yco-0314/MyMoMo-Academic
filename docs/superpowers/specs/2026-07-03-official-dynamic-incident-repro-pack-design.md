# Official Dynamic Incident Repro Pack Phase 1 Design

## Summary

Wrap the existing Official Dynamic Incident Event Effect Smoke in a small
manifest-backed repro pack. The pack fixes the incident intake manifest, run
parameters, expected event-effect diagnostics, and boundary text so reviewers
can rerun the same evidence without relying on an ad hoc function call.

This phase adds reproducibility and auditability only. It does not add real
incident data, timestamp parsing, traffic-flow validity, production map
matching, incident calibration, route optimality, or SUMO/MATSim execution.

## Inputs

- Existing incident intake manifest:
  `data/fixtures/official-incident-events/test_manifest.json`
- Existing validation smoke:
  `official_dynamic_incident_event_effect_report(...)`
- Existing validation gate:
  `official_dynamic_incident_event_effect_gate(...)`

The committed incident input remains the synthetic official-style fixture
introduced by the intake bridge. The repro pack must repeat that boundary in
its manifest and gate output.

## Runtime Contract

Add GIS-only module:

```text
abm_auto/gis/_official_incident_repro.py
```

Schema:

```text
abm-auto/official-dynamic-incident-event-effect-repro/v1
```

Default manifest constant:

```python
OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST = Path(
    "data/fixtures/official-incident-events/"
    "official-dynamic-incident-repro/manifest.json"
)
```

Public APIs:

```python
load_official_dynamic_incident_repro_manifest(path) -> dict

official_dynamic_incident_repro_report(
    manifest_path=OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST,
) -> dict

official_dynamic_incident_repro_gate(
    manifest_path=OFFICIAL_DYNAMIC_INCIDENT_REPRO_MANIFEST,
) -> tuple[bool, str]
```

The report must:

- load and validate the repro manifest;
- resolve the referenced incident intake manifest relative to the repro
  manifest path;
- call `official_dynamic_incident_event_effect_report(...)` with the manifest
  parameters;
- fail if the validation smoke itself fails;
- compare the smoke summary with expected values in the repro manifest;
- return provenance, run parameters, expected values, summary, smoke report, and
  boundary note.

The gate must pass only when the report passes and must include the boundary
text.

## Manifest Contract

Required fields:

- `schema`
- `dataset`
- `source_url`
- `source_agency`
- `license`
- `downloaded_at`
- `incident_manifest_path`
- `run`
- `expected`
- `boundary_note`

`run` fields:

- `n_steps`: positive integer, bool rejected
- `speed_m_per_tick`: positive finite number
- `reroute`: boolean

Phase 1 uses the validation smoke's default geonet and default scenario nodes.
The manifest must not introduce arbitrary geonet, safe-node, or agent-node
serialization in this phase.

`expected` fields:

- `expected_n_matched_incidents`: positive integer
- `expected_arrival_delay`: finite number
- `expected_waiting_delta`: finite number
- `expected_incident_steps_with_closed_edges`: non-empty list of non-negative
  integers
- `expected_max_closed_edges`: positive integer
- `expected_changed`: boolean

Expected values are deterministic repro assertions over the committed fixture.
They are not scientific truth labels for real incident impact.

## Fixture

Add:

```text
data/fixtures/official-incident-events/official-dynamic-incident-repro/
```

Files:

- `README.md`
- `manifest.json`

Manifest values:

```json
{
  "schema": "abm-auto/official-dynamic-incident-event-effect-repro/v1",
  "dataset": "Synthetic official-style incident dynamic event-effect smoke",
  "source_url": "https://example.test/transport/incidents",
  "source_agency": "Example Department of Transportation",
  "license": "Synthetic fixture for tests; cite source in real manifests",
  "downloaded_at": "2026-07-03",
  "incident_manifest_path": "../test_manifest.json",
  "run": {
    "n_steps": 4,
    "speed_m_per_tick": 100.0,
    "reroute": false
  },
  "expected": {
    "expected_n_matched_incidents": 2,
    "expected_arrival_delay": 2.0,
    "expected_waiting_delta": 2.0,
    "expected_incident_steps_with_closed_edges": [1, 2],
    "expected_max_closed_edges": 1,
    "expected_changed": true
  },
  "boundary_note": "Official dynamic incident reproducibility pack over a synthetic official-style fixture only; not traffic-flow validity, not production map matching, not real incident calibration, not route optimality, and not optimal incident management."
}
```

## Report Shape

Successful report:

```python
{
    "ok": True,
    "reason": "",
    "manifest": {...},
    "dataset": "...",
    "source_url": "...",
    "source_agency": "...",
    "license": "...",
    "downloaded_at": "2026-07-03",
    "run": {...},
    "expected": {...},
    "summary": {
        "n_matched_incidents": 2,
        "arrival_delay": 2.0,
        "waiting_delta": 2.0,
        "incident_steps_with_closed_edges": [1, 2],
        "max_closed_edges": 1,
        "changed": True,
        "baseline_mean_arrival_t": 1.0,
        "incident_mean_arrival_t": 3.0,
    },
    "smoke_report": {...},
    "boundary_note": "...",
}
```

Failure report:

```python
{
    "ok": False,
    "reason": "...",
    "manifest": {...},
    "dataset": "...",
    "source_url": "...",
    "source_agency": "...",
    "license": "...",
    "downloaded_at": "...",
    "run": {...},
    "expected": {...},
    "summary": None,
    "smoke_report": {...} | None,
    "boundary_note": "...",
}
```

Required failure reasons:

- smoke report failed;
- matched incident count mismatch;
- arrival delay mismatch;
- waiting delta mismatch;
- closed-edge steps mismatch;
- max closed edges mismatch;
- changed flag mismatch.

Numeric comparisons should use exact deterministic equality with a tiny
absolute tolerance such as `1e-9`, matching the congestion repro pack style.

## Tests

Add `tests/gis/test_official_incident_repro.py`.

Required cases:

- manifest loads and resolves `incident_manifest_path`;
- report passes with expected summary values;
- gate passes with boundary text;
- report fails when `expected_waiting_delta` is too strict or incorrect;
- manifest rejects invalid `n_steps` bool;
- manifest rejects an empty `expected_incident_steps_with_closed_edges`.

Targeted verification:

```bash
.venv/bin/python -m pytest tests/gis/test_official_incident_repro.py tests/gis/test_official_incident_validation.py tests/gis/test_official_incident_intake.py -q
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

Record the pack as a reproducibility wrapper around the official dynamic
incident event-effect smoke. It strengthens auditability, not scientific
validity.

## Non-Goals

- No real official incident sample.
- No timestamp-to-simulation-clock bridge.
- No external download.
- No production map matching.
- No traffic-flow validity or traffic assignment.
- No incident severity/duration calibration.
- No route-choice validation.
- No SUMO/MATSim bridge.
- No codegen changes.
- No base-engine edits.
