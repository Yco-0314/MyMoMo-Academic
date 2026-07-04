# Official Dynamic Incident Event Effect Smoke Phase 1 Design

## Summary

This phase connects the official incident-event intake bridge to the existing
dynamic incident routing model. The goal is a thin deterministic validation
smoke: load manifest-backed incident closure/reopen rows, match them to
`GeoNetwork` edges, feed `matched_incidents` into `run_dynamic_incident_routing`,
and compare the result with a no-incident baseline.

This is not traffic-flow validity, not production map matching, not incident
impact calibration, and not optimal incident management. It proves only that a
provenance-bearing official-style incident manifest can change the moving-agent
dynamic incident model's time series.

## Inputs

- Existing default incident manifest:
  `data/fixtures/official-incident-events/test_manifest.json`
- Existing incident intake report:
  `official_incident_event_edge_match_report(...)`
- Existing dynamic incident model:
  `run_dynamic_incident_routing(...)`

The committed Phase 1 incident fixture is synthetic official-style data, not a
real official incident feed. It keeps the same boundary established by
`2026-07-03-official-incident-event-intake-design.md`.

## Runtime Contract

Add GIS-only module:

```text
abm_auto/gis/_official_incident_validation.py
```

Public report API:

```python
official_dynamic_incident_event_effect_report(
    manifest_path=DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST,
    *,
    geonet=None,
    safe_nodes=None,
    agent_nodes=None,
    n_steps=4,
    speed_m_per_tick=100.0,
    reroute=False,
) -> dict
```

The report must:

- call `official_incident_event_edge_match_report(...)`;
- fail before running the dynamic model if intake or edge matching fails;
- run a baseline dynamic model with no incidents;
- run an incident dynamic model with `intake_report["matched_incidents"]`;
- compare the two dynamic outputs;
- return intake provenance, parameters, baseline result, incident result,
  effect diagnostics, and a cautious boundary note.

The default `reroute=False` is intentional. Phase 1 isolates whether official
event rows affect the dynamic lifecycle. Reroute-improvement claims remain owned
by the existing synthetic `dynamic_incident_reroute_gate(...)`.

When `geonet=None`, the report uses a small validation `GeoNetwork` compatible
with the default incident fixture:

- `(0, 0) -> (100, 0)`
- `(100, 0) -> (200, 0)`
- `(0, 100) -> (200, 0)`

Default `agent_nodes` and `safe_nodes` are:

- agent start: `(0, 0)`
- safe node: `(200, 0)`

The default fixture closes the bottleneck edge at `t=1` and reopens it at `t=3`.
With `speed_m_per_tick=100.0` and `reroute=False`, the baseline arrives before
the incident run, while the incident run records closed-edge and waiting steps.

## Output Shape

Successful report:

```python
{
    "ok": True,
    "reason": "",
    "intake_report": {...},
    "params": {
        "n_steps": 4,
        "speed_m_per_tick": 100.0,
        "reroute": False,
        "safe_nodes": [(200, 0)],
        "agent_nodes": [(0, 0)],
    },
    "n_matched_incidents": 2,
    "baseline_result": {...},
    "incident_result": {...},
    "effect": {
        "changed": True,
        "baseline_mean_arrival_t": 1,
        "incident_mean_arrival_t": 3,
        "arrival_delay": 2,
        "baseline_total_waiting": 1,
        "incident_total_waiting": 3,
        "waiting_delta": 2,
        "incident_steps_with_closed_edges": [1, 2],
        "max_closed_edges": 1,
    },
    "boundary_note": "...",
}
```

Failure before the dynamic model:

```python
{
    "ok": False,
    "reason": "official incident event intake failed: ...",
    "intake_report": {...},
    "params": {...},
    "n_matched_incidents": 0,
    "baseline_result": None,
    "incident_result": None,
    "effect": None,
    "boundary_note": "...",
}
```

## Effect Diagnostics

The report should compute:

- `baseline_mean_arrival_t`
- `incident_mean_arrival_t`
- `arrival_delay`
- `baseline_total_waiting`
- `incident_total_waiting`
- `waiting_delta`
- `incident_steps_with_closed_edges`
- `max_closed_edges`
- `arrived_delta`
- `stranded_delta`
- `changed`

`changed` is true when at least one dynamic outcome differs between baseline and
incident runs:

- arrival time differs;
- total waiting differs;
- arrived or stranded counts differ;
- per-step closed-edge series differs;
- per-step movement summary differs.

The default passing fixture should rely on arrival delay, waiting delta, and
closed-edge steps. The raw waiting totals include the existing dynamic runtime's
tick-0 pre-arrival waiting record, so the event signal is `waiting_delta`, not a
zero baseline wait count. It should not require reroutes.

## Gate

Add:

```python
official_dynamic_incident_event_effect_gate(
    manifest_path=DEFAULT_OFFICIAL_INCIDENT_EVENT_MANIFEST,
) -> tuple[bool, str]
```

The gate passes only when:

- intake report is `ok`;
- at least one matched incident is present;
- the incident run records one or more closed-edge steps;
- the incident run changes at least one dynamic outcome relative to the
  no-incident baseline;
- the returned message states the scientific boundary.

Gate text must say this proves manifest-backed incident events affect a
moving-agent dynamic incident model. It must not claim traffic-flow validity,
production map matching, real incident calibration, route optimality, or
incident-management quality.

## Tests

Add `tests/gis/test_official_incident_validation.py`.

Required cases:

- default report loads matched incidents and runs both baseline and incident
  dynamic models;
- default report records closed-edge steps and later incident arrival than the
  no-incident baseline;
- default gate passes and includes boundary text;
- report fails before running the dynamic model when the intake manifest fails;
- report fails when no matched incidents are produced;
- gate fails when the incident run has no dynamic effect;
- invalid `agent_nodes`, `safe_nodes`, `n_steps`, or `speed_m_per_tick` values
  fail through existing dynamic model validation or explicit wrapper checks.

Targeted verification:

```bash
.venv/bin/python -m pytest tests/gis/test_official_incident_validation.py tests/gis/test_official_incident_intake.py tests/gis/test_dynamic_incident.py -q
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
- `docs/reproduce/coupled-seam/ADR-019-SYNTHESIS.md` if present and current

Record this as a dynamic incident validation smoke over an official-style
incident event manifest. It is stronger than pure synthetic event dictionaries
because the events pass manifest, checksum, provenance, and edge-match checks
before reaching the dynamic runtime. It is still not real traffic-flow validity
or real incident calibration.

## Open/Closed Boundary

Open-source scope:

- manifest-backed incident intake to dynamic runtime handoff;
- deterministic no-incident versus incident smoke comparison;
- explicit effect diagnostics;
- cautious gate text;
- local synthetic official-style fixture.

Future or closed scope:

- private/full official incident feeds;
- real timestamp-to-simulation-clock mapping;
- production geocoding or map matching;
- calibrated incident duration or severity models;
- route-choice or traffic-assignment validation;
- SUMO/MATSim bridge validation.
