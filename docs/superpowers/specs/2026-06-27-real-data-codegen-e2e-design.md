# Real-Data Codegen End-to-End Phase 1 — Design Spec

**Status:** Draft. **Date:** 2026-06-27.
**Branch:** `codex/real-data-codegen-e2e`.
**Parent:** ADR-024 D3 step 2.

## Purpose

ADR-024 says the next post-candidate-#10 ladder step is real-data codegen
end-to-end: at least one generated GIS model must read a real/local data path
and pass a deterministic gate over that input. Without this, the codegen
fidelity wall mostly verifies synthetic fixtures.

Phase 1 uses the existing observed-raster repro pack. The committed GeoTIFF is
small and local, but it exercises the same manifest -> raster I/O -> provenance
-> calibration -> gate path that a real GHSL/WorldPop clip would use.

## Scope

- Extend `raster_spatial_calibration` rendering so a non-empty `data_path`
  is treated as an observed-raster manifest path.
- Generated code must call `calibrate_observed_raster_from_manifest(...)` and
  `observed_raster_repro_gate(...)`.
- Generated code must still define the simulator in the generated model, so
  codegen remains responsible for the model logic while the manifest supplies
  observed data and calibration settings.
- Preserve the existing synthetic `raster_spatial_calibration` template when
  `data_path` is empty.
- Keep `GISModelSpec` round-trip and CLI `gis run <spec.json>` behavior working
  without special CLI flags.

## Non-Goals

- No remote download, reprojection, resampling, or CRS repair.
- No extractor prompt changes; LLM real-data story extraction is a later step.
- No change to `raster_sir` or network templates.
- No Bayesian posterior inference and no edits under `abm_auto/calibration/`.
- No claim that the committed test GeoTIFF is official GHSL/WorldPop data.

## Verification

- A codegen test proves `data_path` renders manifest-backed code, not the
  synthetic calibration template.
- A generated model using
  `data/fixtures/observed-raster/test_manifest.json` executes and prints PASS.
- The fidelity gate passes for manifest-backed generated code.
- CLI `abm-auto gis run <spec.json>` executes the same path.
- GIS suite, engine oracle, base suite, and forbidden base-engine diff remain
  green.
