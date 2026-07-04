# AutoData Registry Auto-Discovery Design

## Summary

Registry auto-discovery scans committed AutoData challenge producer specs and
reconstructs the registry entries that should exist. This gives Codex/Claude a
deterministic way to detect stale, missing, or extra registry entries without
hand-auditing JSON.

## Scope

In scope:

- Discover `producer-spec.json` files under a challenge root.
- Read explicit `registry` metadata from each producer spec.
- Produce a registry-shaped object with stable ordering.
- Audit a committed registry against discovery and report missing, extra, or
  changed entries.
- Provide CLI commands for discovery and audit.

Out of scope:

- No model execution.
- No claim extraction from prose.
- No automatic mutation of `registry.json`; discovery is reported, not silently
  written over the committed registry.
- No base-engine directory edits.

## Commands

Discover:

```bash
.venv/bin/python -m abm_auto.repro_challenge registry-discover \
  docs/reproduce/autodata-challenges \
  --repo .
```

Audit:

```bash
.venv/bin/python -m abm_auto.repro_challenge registry-audit \
  docs/reproduce/autodata-challenges/registry.json \
  docs/reproduce/autodata-challenges \
  --repo .
```

The audit result is a deterministic quality gate for the registry. It proves the
registry matches committed producer specs; it does not prove the scientific
claims inside the evidence artifacts.
