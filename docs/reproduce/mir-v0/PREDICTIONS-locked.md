# MIR v0 Half A — Locked Predictions (BEFORE any round-trip run)

**Locked:** 2026-06-23, BEFORE building/running. Anti-fabrication: write the
expected round-trip behaviour, commit, then implement, then read REAL output.

Spec: `docs/superpowers/specs/2026-06-23-mir-v0-forward-design.md`.

## Predictions

- **P1 field-identity**: `mir_to_gis_spec(gis_spec_to_mir(spec))` is field-equal
  to `spec` for `spatial_type`, `mechanism`, `capability`, `data_path`, `seed`,
  `params`.
- **P2 fidelity tokens survive**: `gis_spec_to_mir(spec).fidelity.required_tokens
  == resolve_capability(...).required_tokens`; same for `gate` and
  `wrong_space_tokens`.
- **P3 byte-identical render**: `render(round_tripped_spec)["main.py"] ==
  render(spec)["main.py"]` for every tested capability.
- **P4 gate + execute survive**: for `raster_sir`, `topology_clip`,
  `raster_focal`, `raster_coverage` — the round-tripped spec renders, passes
  `gis_codegen_gate`, executes, and prints a science-gate PASS.
- **P5 extensions seam**: `gis_spec_to_mir(spec).extensions == {}` (GIS never
  fills it); a MIR carrying arbitrary `extensions={"search_space": {...}}` still
  renders byte-identical GIS code (open side ignores extensions).
- **P6 empty clusters survive**: `entities/state/relations/layers/metrics` are
  empty after a GIS round-trip and survive dict + JSON serialisation as empty
  (present for Half B to fill, lossless in v0).
- **P7 zero-change**: `engine_oracle --science` + `--check` PASS; base suite
  unchanged; forbidden diff empty.

Any miss is reported as a miss; if a field does not survive, the MIR schema is
under-specified — fix the schema, do not paper over.
