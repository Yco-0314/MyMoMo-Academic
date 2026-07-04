# Native / Bridge / Audit Registry Phase 1 Design

**Status:** Design for a minimal implementation.
**Date:** 2026-07-01
**Scope:** Add a small platform capability disposition registry that records
whether a capability should be native MyMoMo work, an external bridge, an audit
baseline, or out of scope.

## Summary

NetLogo and GAMA semantic coverage both need the same decision vocabulary:

- `native`: implement in MyMoMo because the concept is a reusable ABM,
  GIS, MIR, or reproducibility semantic;
- `bridge`: call or package an external specialist tool when fidelity requires
  it;
- `audit_baseline`: compare against an external tool or fixture without making
  it part of the runtime;
- `out_of_scope`: record the concept but do not pursue it in the current open
  academic wedge.

Phase 1 makes that vocabulary machine-checkable with a small registry validator
and a committed seed registry. It does not drive codegen, does not execute
bridges, and does not introduce a `CoupledModel`-style abstraction.

## Architecture

Add a standalone module:

```text
abm_auto/platform_capabilities.py
```

The module validates registry JSON objects with schema:

```text
abm-auto/platform-capability-registry/v1
```

Each entry records:

- `key`: stable capability id;
- `domain`: `gis`, `netlogo`, `gama`, `transport`, `llm_society`, `closed_extension`,
  `evidence`, or `platform`;
- `concept`: reader-facing concept name;
- `disposition`: `native`, `bridge`, `audit_baseline`, or `out_of_scope`;
- `evidence_level`: `E0` through `E6`;
- `source`: where the classification came from;
- `next_action`: concrete next move;
- `boundary_note`: what not to claim.

The registry lives in:

```text
docs/reproduce/platform-capabilities/registry.json
```

## API

Phase 1 exports:

```python
validate_platform_capability_registry(registry: dict) -> dict
load_platform_capability_registry(path: Path) -> dict
list_platform_capabilities(
    registry: dict,
    *,
    domain: str | None = None,
    disposition: str | None = None,
    evidence_level: str | None = None,
) -> list[dict]
```

Validation returns:

```python
{"ok": bool, "issues": list[str], "entry_count": int}
```

No CLI is required in Phase 1. The module-level API is enough for tests and
future Evidence Foundry integration.

## Seed Registry

The seed registry should include entries from current architecture pressure:

- `gama_species`: native semantic pressure, E0;
- `gama_gis_import`: native GIS/data pressure, E2;
- `gama_3d_visualization`: out of scope, E0;
- `transport_sumo_matsim_bridge`: bridge, E1;
- `llm_synthetic_population_manifest`: native manifest pressure, E0;
- `closed_extension_backend_manifest`: bridge, E0;
- `evidence_foundry_challenge_pack`: native trust layer, E0.

The registry is intentionally small. It is a proof of the classification seam,
not a comprehensive platform inventory.

## Error Handling

Validation should reject:

- non-object registry;
- wrong schema;
- missing or duplicate `key`;
- unknown `domain`;
- unknown `disposition`;
- unknown `evidence_level`;
- missing or empty `concept`, `source`, `next_action`, or `boundary_note`.

Filtering should preserve registry order.

## Non-Goals

- No runtime bridge execution.
- No codegen integration.
- No GAMA, SUMO, MATSim, LLM, or closed extension dependency.
- No parser or model template.
- No broad capability inventory.
- No edits to forbidden base-engine directories.

## Acceptance Criteria

- Unit tests cover valid registry, duplicate keys, invalid disposition, invalid
  evidence level, and filtering by domain/disposition.
- The committed seed registry validates.
- The GAMA semantic coverage next action points at this registry.
- Forbidden base-engine diff remains empty.
- Existing Evidence Foundry challenge tests remain green.
