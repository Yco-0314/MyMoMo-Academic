# Failure Pack Phase 1 Design

**Status:** Design for minimal implementation.
**Date:** 2026-07-01
**Scope:** Add a small Evidence Foundry failure-pack format for MISS, PARTIAL,
scope ceilings, and residual patterns.

## Summary

A failed reproduction should not be a dead end. It should become a structured
artifact that records which claim failed, what evidence was used, which residual
pattern appeared, and what scope ceiling prevents overclaiming.

Phase 1 adds a validator, builder, and seed failure pack. It does not rerun any
model and does not convert failures into passes.

## Architecture

Add:

```text
abm_auto/failure_pack.py
```

Schema:

```text
abm-auto/failure-pack/v1
```

Seed pack:

```text
docs/reproduce/evidence-foundry/failure-pack-example/failure-pack.json
```

## Pack Fields

Required top-level fields:

- `schema`;
- `source_id`;
- `claims`;
- `scope_ceilings`;
- `residuals`;
- `boundary_note`.

Each claim contains:

- `id`;
- `verdict`: `MISS`, `PARTIAL`, `INCONCLUSIVE`, or `BLOCKED`;
- `reason`;
- `evidence_refs`.

Residuals contain:

- `metric`;
- `observed`;
- `predicted`;
- `error`;

## Non-Goals

- No model rerun.
- No automatic mechanism search.
- No rewriting a MISS as a pass.
- No hidden benchmark.
- No integration into all existing reproduction bundles in Phase 1.

## Acceptance Criteria

- Unit tests cover valid pack, builder output, invalid PASS verdict, missing
  evidence refs, invalid residual fields, committed seed pack, and summary.
- Platform capability registry includes `failure_pack`.
- Forbidden base-engine diff remains empty.
