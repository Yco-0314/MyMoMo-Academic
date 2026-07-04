# Official Dynamic Congestion Validation Smoke Phase 1 Design

## Summary

This phase connects the existing official Seattle SDOT count-to-centerline
observed edge target to the existing dynamic congestion routing model. The goal
is a thin, deterministic validation smoke: run the dynamic model on the bounded
official Seattle Streets `GeoNetwork`, aggregate per-tick edge loads for the
officially observed edges, and evaluate them with the existing network
validation metrics and loss.

This is **not** traffic-flow validity, **not** calibrated congestion, **not**
capacity inference, and **not** production map matching. It proves that the
moving-agent dynamic congestion adapter can emit edge-level outputs that are
checked against a provenance-bearing official observed target.

## Inputs

- Existing official centerline match manifest:
  `data/fixtures/official-traffic-counts/seattle-sdot-2023-centerline-match/manifest.json`
- Existing official observed target bridge:
  `official_traffic_observed_target_from_centerline_match(...)`
- Existing centerline `GeoNetwork` loader:
  `load_official_centerline_match_manifest(...)` and
  `load_official_centerline_geonet(...)`
- Existing dynamic congestion model:
  `run_dynamic_congestion_routing(...)`
- Existing network validation:
  `network_edge_metrics(...)` and `network_edge_loss(...)`

## Runtime Contract

Add `abm_auto/gis/_official_congestion_validation.py`.

Public API:

```python
official_dynamic_congestion_validation_report(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
    *,
    agents_per_edge=1,
    n_steps=2,
    speed_m_per_tick=1000.0,
    congestion_alpha=0.0,
    reroute=True,
) -> dict
```

The report must:

- load the official traffic observed target;
- fail before running the dynamic model if the official centerline match fails;
- load the official Seattle Streets `GeoNetwork`;
- create one or more agents per observed edge, starting at one endpoint and
  targeting the other endpoint as a safe node;
- run `run_dynamic_congestion_routing(...)`;
- aggregate `steps[*]["edge_loads"]` over the observed edge subset;
- evaluate the aggregate edge loads with `network_edge_metrics(...)`;
- compute `network_edge_loss(...)`;
- return provenance, diagnostics, model parameters, simulated edge values,
  metrics, loss, dynamic result, and a cautious boundary note.

Validation:

- `agents_per_edge` must be a positive integer and must reject bool.
- Existing dynamic model validation continues to own `n_steps`,
  `speed_m_per_tick`, and `congestion_alpha`.

Public gate:

```python
official_dynamic_congestion_validation_gate(
    manifest_path=SEATTLE_SDOT_2023_CENTERLINE_MATCH_MANIFEST,
) -> tuple[bool, str]
```

The gate compares `agents_per_edge=1` with `agents_per_edge=2`. It passes only
when:

- both reports pass;
- all observed edges are covered;
- the simulated total changes;
- the validation loss changes;
- the returned message states the scientific boundary.

## Output Shape

Successful report:

```python
{
    "ok": True,
    "reason": "",
    "observed_provenance": {...},
    "centerline_diagnostics": {...},
    "station_streets": {...},
    "station_objectids": {...},
    "params": {
        "agents_per_edge": 1,
        "n_steps": 2,
        "speed_m_per_tick": 1000.0,
        "congestion_alpha": 0.0,
        "reroute": True,
    },
    "simulated_edge_values": {edge: value, ...},
    "simulated_total": 3.0,
    "metrics": {...},
    "loss": float,
    "dynamic_result": {...},
    "boundary_note": "...not traffic-flow validity...",
}
```

Failure before the model:

```python
{
    "ok": False,
    "reason": "official centerline edge match failed: ...",
    "centerline_report": {...},
    "observed_provenance": None,
    "centerline_diagnostics": {...} | None,
    "station_streets": {...} | None,
    "station_objectids": {...} | None,
    "params": {...},
    "simulated_edge_values": None,
    "simulated_total": None,
    "metrics": None,
    "loss": None,
    "dynamic_result": None,
    "boundary_note": "...",
}
```

## Tests

Add `tests/gis/test_official_congestion_validation.py`.

Required cases:

- report covers all three official observed centerline edges;
- `agents_per_edge` changes simulated total and validation loss;
- gate passes and includes the boundary text;
- report fails before the dynamic model when the official centerline match
  manifest is made too strict;
- invalid `agents_per_edge` values fail.

## Documentation

Update:

- `docs/reproduce/coupled-seam/STATUS.md`
- `docs/reproduce/coupled-seam/ADR-019-SYNTHESIS.md`

The docs must record this as a validation smoke over official observed edge
targets, not as a traffic-flow or congestion-calibration result.

## Final Verification

Run:

```bash
.venv/bin/python -m pytest tests/gis/test_official_congestion_validation.py tests/gis/test_official_traffic_calibration.py tests/gis/test_dynamic_congestion.py tests/gis/test_network_validation.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

The final diff check must be empty.
