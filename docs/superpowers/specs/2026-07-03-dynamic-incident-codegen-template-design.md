# Dynamic Incident Codegen Template Design

## Context

`dynamic_incident_routing` already exists as a runtime adapter and deterministic
gate. It models moving agents on a `GeoNetwork` while per-tick incident events
close or reopen road edges. The current codegen registry renders dynamic flood
and dynamic congestion, but incident routing is not yet a renderable capability.

## Goal

Promote the existing incident runtime cell into a codegen-renderable GIS
capability without changing runtime science behavior.

## Scope

In scope:

- Register `dynamic_incident_routing` as a renderable GIS capability.
- Add declarative render params for `n_steps` and `speed_m_per_tick`.
- Add a synthetic generated template that builds a small detour network, closes
  the direct edge at tick 1, runs `run_dynamic_incident_routing`, and calls
  `dynamic_incident_reroute_gate`.
- Extend codegen, gate, extractor, and self-extension tests to cover the new
  renderable cell.
- Update coupled-seam status docs to record codegen coverage.

Out of scope:

- No change to `run_dynamic_incident_routing` semantics.
- No new incident mechanism, traffic-flow model, congestion, real incident data,
  or optimal incident-management claim.
- No base-engine edits.
- No `CoupledModel` abstraction.

## Capability Contract

Capability key: `dynamic_incident_routing`

- `spatial_type`: `network`
- `mechanism`: `dynamic_incident_routing`
- `layers`: `GeoNetwork`, `moving agents`, `per-tick incident events`
- `coupling`: `dynamic_network_incident`
- `dynamic`: `True`
- `temporal`: `False`
- `renderable`: `True`
- `gate`: `dynamic_incident_reroute_gate`
- required tokens:
  - `GeoNetwork`
  - `LineString`
  - `run_dynamic_incident_routing`
  - `dynamic_incident_reroute_gate`

Render params:

- `n_steps`: integer, default `6`, minimum `1`
- `speed_m_per_tick`: float, default `100.0`, minimum strictly positive at
  runtime; registry lower bound remains `0.0` to match current dynamic congestion
  conventions.

## Generated Model Behavior

The generated model builds the same deterministic detour pattern used by the
incident runtime gate:

- direct path: start -> bottleneck -> safe
- detour path: start -> detour -> safe
- incident: at tick 1, close `bottleneck -> safe`

With rerouting enabled, the generated model should pass
`dynamic_incident_reroute_gate` and print a `PASS:` line that explicitly remains
within the gate's scientific boundary: moving-agent incident rerouting changes
deterministic outcomes, but this does not prove real traffic flow or optimal
incident management.

## Acceptance

- Registry exposes the new capability as renderable and dynamic.
- `GISModelSpec(... capability="dynamic_incident_routing")` validates without a
  `data_path`.
- `render(spec)["main.py"]` contains the required runtime and gate calls.
- Generated code executes successfully and prints `PASS`.
- `gis_codegen_gate` uses registry required tokens for this capability.
- Extractor prompt advertises the capability and accepts explicit JSON for it.
- Self-extension preflight classifies it as renderable.
- GIS tests pass.
- Engine oracle science and byte checks pass.
- Forbidden base-engine diff is empty.
