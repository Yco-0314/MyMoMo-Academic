# Transport Bridge Manifest Phase 1 Design

**Status:** Design for minimal implementation.
**Date:** 2026-07-01
**Scope:** Define and validate a transport bridge manifest for future SUMO/MATSim
or similar traffic-engine bridges without executing external engines.

## Summary

MyMoMo's dynamic flood and congestion models prove moving-agent lifecycle
semantics. They do not prove traffic-flow validity. Before adding deeper traffic
claims, the platform needs a bridge manifest that records exactly what an
external traffic engine would run and how its outputs would be reduced into
MyMoMo evidence.

Phase 1 adds a manifest validator only. It does not install SUMO or MATSim, run
traffic simulations, or claim fidelity.

## Sources Checked

- Eclipse SUMO homepage: <https://eclipse.dev/sumo/>
- MATSim homepage: <https://matsim.org/>

SUMO is treated as a bridge candidate because it is a microscopic, continuous,
multi-modal traffic simulation package designed for large networks. MATSim is
treated as a bridge candidate because it is an open-source large-scale
agent-based transport simulation framework. MyMoMo should package calls to such
specialist tools before claiming traffic-flow fidelity.

## Manifest Purpose

A transport bridge manifest records:

- bridge id and engine name;
- engine version or version policy;
- command that would run the engine;
- scenario scope and time unit;
- input artifacts and their roles;
- output artifacts and reduction metrics;
- claims the bridge is allowed to support;
- boundary notes that prevent overclaiming.

The manifest is an Evidence Foundry object: it supports provenance and audit. It
is not the bridge execution layer.

## Architecture

Add a standalone module:

```text
abm_auto/transport_bridge.py
```

Exports:

```python
validate_transport_bridge_manifest(manifest: dict) -> dict
load_transport_bridge_manifest(path: Path) -> dict
summarize_transport_bridge_manifest(manifest: dict) -> dict
```

Schema:

```text
abm-auto/transport-bridge-manifest/v1
```

Seed manifest:

```text
docs/reproduce/transport-bridge/synthetic-evacuation/bridge-manifest.json
```

## Validation Rules

Reject:

- non-object manifest;
- wrong schema;
- missing `bridge_id`;
- unsupported engine name;
- missing or empty engine command;
- absolute input or output paths;
- missing scenario `time_unit`;
- duplicate input/output keys;
- missing reduction metrics for outputs;
- missing claim `id`, `metric`, or `boundary_note`.

Supported engine names in Phase 1:

- `SUMO`
- `MATSim`
- `external`

## Seed Manifest

The seed manifest should describe a synthetic flood-evacuation bridge contract.
It should not pretend that SUMO/MATSim was run. Use `engine.name = "external"`
and a command such as:

```json
["external-traffic-engine", "--scenario", "scenario.json"]
```

The boundary note must state that this is a manifest contract only.

## Non-Goals

- No SUMO or MATSim dependency.
- No external command execution.
- No traffic physics.
- No router integration.
- No GIS runtime change.
- No codegen integration.
- No claim that native dynamic congestion is traffic-flow valid.

## Acceptance Criteria

- Unit tests cover valid manifest, invalid engine, absolute paths, duplicate
  keys, missing reduction metrics, committed seed manifest validation, and
  summary output.
- The seed manifest is committed under `docs/reproduce/transport-bridge/`.
- Platform capability registry keeps transport as `bridge`.
- Forbidden base-engine diff remains empty.
