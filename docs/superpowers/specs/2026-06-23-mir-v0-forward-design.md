# MIR v0 — Half A (Forward / Open) — Design Spec

**Status:** Draft. **Date:** 2026-06-23. **Repo:** MyMoMo-GIS-Academic (open side).
**Governed by:** the Open/Closed Boundary (strategic ADR-013, private
`unified-abm-platform-docs/strategic-adrs/`) + the MIR convergence analysis
(`unified-abm-platform-docs/2026-06-23-mir-convergence-analysis.md`).

## Goal

The first executable proof of the open/closed merge: a shared **MIR core** schema
(open) + a **GISModelSpec ↔ MIR** adapter + a **forward round-trip** that proves a
real GIS model survives `GISModelSpec → MIR → GISModelSpec → render → run` with
**no fidelity token lost** and its science gate still passing.

This is **Half A only**. Half B (Blueprint ↔ MIR core+extensions, in the closed
gaese repo) is a separate effort.

## Scope (Half A ships)

- `abm_auto/mir/_schema.py` — MIR core as **dataclasses** (matching the house
  style of `_model_spec.py`: dataclass + `to_dict`/`from_dict` + `validate`). The
  11 open clusters from the convergence table + the **`extensions` seam**.
- `abm_auto/mir/_gis_adapter.py` — `gis_spec_to_mir(spec) -> MIR` and
  `mir_to_gis_spec(mir) -> GISModelSpec`.
- `tests/gis/test_mir_v0.py` — the forward round-trip + fidelity-token survival +
  JSON round-trip + extensions-stays-empty (the seam is unused on the open side).

## The MIR core shape (dataclass)

```text
MIR (core, OPEN)
├── metadata    name / description / domain / provenance
├── entities    [] (agents — empty for a thin forward GIS spec in v0)
├── state       [] (environment variables — empty in v0)
├── space       spatial_type / crs / data_path          ← GIS contributes this
├── relations   [] (causal links / coupling — empty in v0)
├── processes   [{mechanism, params}]
├── layers      [] (multi-scale — empty in v0)
├── metrics     [] (goal metrics — empty in v0)
├── run         seed / params
├── fidelity    capability / required_tokens / gate / wrong_space_tokens   ← GIS contributes this
├── trace       {} (provenance — minimal in v0)
└── extensions  {} (CLOSED overlay attaches here; OPEN side NEVER interprets) ← the seam
```

A thin GIS spec populates `space` + `processes` + `run` + `fidelity` and leaves
`entities/state/relations/layers/metrics` empty. Those empty clusters must
**survive the round-trip as empty** (they exist so Blueprint can fill them in
Half B). `extensions` stays `{}` on the open side — the data-contract seam from
ADR-013, present but unused here.

## Hard constraints

1. **Zero-change to `abm_auto/runtime/`, `codegen/`, `calibration/`, `agents/`,
   `pipeline/`.** MIR lives in a new `abm_auto/mir/` package.
2. **dataclass, no pydantic dependency** in MIR core (match `_model_spec.py`;
   keep the open standard dependency-light).
3. **Fidelity tokens survive.** After round-trip, `gis_codegen_gate` on the
   regenerated model still finds every `required_token` — the verification
   contract is not lost through MIR.
4. **MIR core alone is sufficient.** No `extensions` content is needed to
   regenerate a forward GIS model (extensions is empty for GIS).
5. Predictions locked before the round-trip run.

## Decomposition (TDD)

1. **A1 `MIR` schema** + `to_dict`/`from_dict`/`validate`. Test: empty MIR
   round-trips through dict + JSON; `validate` rejects an unknown top-level shape.
2. **A2 adapter** `gis_spec_to_mir` / `mir_to_gis_spec`. Test: a `raster_sir`
   spec → MIR → spec is field-identical (spatial_type/mechanism/capability/
   data_path/seed/params all survive).
3. **A3 forward round-trip** for several renderable capabilities (raster_sir,
   topology_clip, raster_focal, raster_coverage): `spec → MIR → json → MIR →
   spec → render → gis_codegen_gate PASS → execute → science gate PASS`. Assert
   `mir.fidelity.required_tokens == cap.required_tokens` (tokens survived) and the
   re-rendered code is byte-identical to the original render.
4. **A4 extensions seam** test: `mir.extensions == {}` after a GIS round-trip; a
   MIR carrying arbitrary `extensions={"search_space": {...}}` still produces an
   identical GIS render (the open side ignores extensions).

## Validation

```
.venv/bin/python -m pytest tests/gis/test_mir_v0.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline   # must be EMPTY
```

## Non-goals (Half A)

- **Half B** (Blueprint ↔ MIR core+extensions; the closed gaese side) — separate.
- **space × layers** coexistence — no existing model has both; v0 tests them
  separately; the combination is a known v0 gap, not a deliverable.
- **Decision Depth / search_space / audiences / memory** — closed extensions, not
  built here (only the empty `extensions` seam is present).
- **pydantic** MIR core — dataclass only.
- Merging the repos or replacing either runtime.
