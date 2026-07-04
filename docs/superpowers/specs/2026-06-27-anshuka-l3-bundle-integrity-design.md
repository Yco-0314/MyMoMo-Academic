# Anshuka L3 Bundle Integrity Phase 1 — Design Spec

**Status:** Draft. **Date:** 2026-06-27.
**Branch:** `codex/anshuka-l3-bundle-integrity`.
**Parent:** ADR-024 D3 step 6.

## Purpose

The Anshuka real-DEM reproduction already has the core L3 artifacts:
locked predictions, findings, public data provenance, and
`verdict-bundle.json`. The missing piece is an explicit machine-checkable
diagnostic that says whether the bundle is internally replayable and portable.

Phase 1 adds a small integrity gate for the committed bundle. It should catch
schema drift, missing verdict evidence, stale document hashes, and absolute local
paths that make a reviewer artifact machine-specific.

## Scope

- Add bundle validation helpers to `abm_auto/gis/_repro_bundle.py`.
- Add `repro_bundle_integrity_gate(path, repo=None)` returning `(ok, desc)`.
- Validate:
  - schema is `abm-auto/repro-bundle/v1`;
  - paper/headline/verdicts/data/docs sections exist;
  - verdicts carry gate, tier, passed, and two-number salient values;
  - docs include locked predictions, findings, and design spec;
  - doc fingerprints match current committed files when those files exist;
  - data artifacts include sha256 fingerprints and portable relative paths;
  - no bundle path is an absolute local user path.
- Update the committed Anshuka `verdict-bundle.json` paths to be repo-relative.
- Update `MANIFEST.md` with the integrity gate command.

## Non-Goals

- Do not re-run the real DEM reproduction.
- Do not change H1-H6 verdicts, numbers, thresholds, or headline.
- Do not require the large gitignored DEM to exist in CI.
- Do not download remote data.
- Do not change scientific claims; this is packaging integrity only.

## Verification

- Unit tests cover successful committed-bundle validation.
- Unit tests cover stale doc hash detection and absolute path rejection.
- Target tests: `tests/gis/test_repro_bundle.py`.
- Final GIS and base-engine checks remain required before merge.
