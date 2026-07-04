# Evidence Foundry Registry Discovery Closure Design

**Status:** Closure audit, no new runtime code planned.
**Date:** 2026-07-01
**Scope:** Verify that existing producer-spec registry discovery and audit
helpers are adequate for Evidence Foundry registry maintenance and record them
under the Evidence Foundry capability map.

## Summary

The original AutoData-inspired registry discovery feature already exists in the
generic `abm_auto.repro_challenge` module. It scans committed
`producer-spec.json` files, derives registry entries from explicit registry
metadata, and audits the committed registry against discovered entries.

The current task is not to rebuild it. The task is to close the loop under the
Evidence Foundry framing:

- confirm discovery returns the committed curriculum registry shape;
- confirm audit detects missing and extra registry entries;
- confirm CLI discovery and audit commands work;
- record the capability as Evidence Foundry infrastructure;
- keep the existing command and schema names for compatibility.

## Existing Coverage

Implementation:

```text
abm_auto/repro_challenge.py::discover_challenge_registry
abm_auto/repro_challenge.py::audit_registry_discovery
python -m abm_auto.repro_challenge registry-discover
python -m abm_auto.repro_challenge registry-audit
```

Tests:

```text
tests/test_repro_challenge.py::test_discover_challenge_registry_matches_committed_registry
tests/test_repro_challenge.py::test_audit_registry_discovery_reports_missing_and_extra_entries
tests/test_repro_challenge.py::test_repro_challenge_module_cli_discovers_and_audits_registry
```

## Design Decision

Do not add a second registry discovery implementation under
`abm_auto.evidence_foundry_batch`. Registry discovery is challenge-curriculum
maintenance. The batch gate consumes committed registries and artifacts; it
should not become a producer-spec crawler.

## Non-Goals

- No automatic registry mutation.
- No new registry schema.
- No model execution.
- No answer generation.
- No command rename that breaks existing scripts.
- No claim that registry discovery proves scientific validity.

## Acceptance Criteria

- A status note records the existing implementation, tests, commands, and boundary.
- Platform capability registry includes `evidence_foundry_registry_discovery`.
- Existing discovery/audit tests pass.
- Evidence Foundry doctor still passes.
- Forbidden base-engine diff remains empty.
