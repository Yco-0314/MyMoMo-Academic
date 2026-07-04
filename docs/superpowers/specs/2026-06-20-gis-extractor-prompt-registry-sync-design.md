# GIS Extractor Prompt Registry Sync Design

**Date:** 2026-06-20
**Status:** Approved for implementation
**Scope:** GIS-only extractor prompt consistency

## Summary

After `flood_evacuation` became codegen-renderable, the extractor prompt still
describes only the old raster SIR and network routing mechanisms. This phase
syncs the prompt with the renderable capability registry so newly renderable
capabilities are advertised consistently to the LLM.

The extractor validation behavior stays unchanged: nonrenderable registered
capabilities are still rejected after parsing, and unknown or mismatched specs
still fail through `GISModelSpec.validate()`.

## Goals

- Build the extractor prompt's capability guidance from
  `renderable_capabilities()`.
- Include each renderable capability key, spatial type, mechanism, and layers in
  a compact prompt table.
- Ensure `flood_evacuation` appears in the prompt once it is renderable.
- Ensure nonrenderable capabilities such as `dynamic_flood_evacuation` do not
  appear in the prompt.
- Preserve backward-compatible legacy JSON extraction where capability is
  omitted.

## Non-Goals

- No prompt tuning for model quality beyond registry synchronization.
- No new capabilities or templates.
- No extractor API change.
- No base codegen or base engine edits.

## Testing

Update `tests/gis/test_extractor.py` to assert:

- the LLM prompt passed to `client.create(...)` includes `flood_evacuation`;
- the prompt includes the matching `spatial_type="network"` and
  `mechanism="flood_evacuation"` guidance;
- the prompt does not include nonrenderable `dynamic_flood_evacuation`;
- old JSON without `capability` still extracts;
- registered nonrenderable dynamic flood output is still rejected.

Final verification:

```bash
.venv/bin/python -m pytest tests/gis/test_extractor.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```
