# Evidence Foundry Registry Discovery Status

**Status:** Covered by existing implementation.
**Date:** 2026-07-01

## What Is Covered

Evidence Foundry registry discovery and audit are implemented by the generic
challenge helpers:

```text
abm_auto.repro_challenge.discover_challenge_registry
abm_auto.repro_challenge.audit_registry_discovery
```

CLI:

```bash
.venv/bin/python -m abm_auto.repro_challenge registry-discover \
  docs/reproduce/autodata-challenges \
  --repo .

.venv/bin/python -m abm_auto.repro_challenge registry-audit \
  docs/reproduce/autodata-challenges/registry.json \
  docs/reproduce/autodata-challenges \
  --repo .
```

The discovery flow:

- scans committed `producer-spec.json` files;
- reads explicit `registry` metadata;
- derives registry entries with repo-relative paths;
- audits the committed registry for missing, extra, or divergent entries.

## Verification Coverage

The behavior is covered by:

```text
tests/test_repro_challenge.py::test_discover_challenge_registry_matches_committed_registry
tests/test_repro_challenge.py::test_audit_registry_discovery_reports_missing_and_extra_entries
tests/test_repro_challenge.py::test_repro_challenge_module_cli_discovers_and_audits_registry
```

## Design Boundary

No new runtime implementation is needed in `abm_auto.evidence_foundry_batch`.
Registry discovery belongs to challenge-curriculum maintenance. The batch gate
consumes committed registries and artifacts; it should not become a
producer-spec crawler.

This helper checks registry consistency. It does not mutate registries, generate
answers, execute models, or certify scientific truth. Discovered registries must
still pass validation, registry gates, batch gates, or the top-level Evidence
Foundry doctor.
