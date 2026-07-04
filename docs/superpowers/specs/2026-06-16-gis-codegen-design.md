# GIS Codegen — Design Spec (Sub-project B main body)

**Status:** Draft. **Date:** 2026-06-16. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [GIS Mode](2026-06-16-gis-mode.md). **Builds on:** Sub-project A (RasterSpace),
GeoNetwork foundation, and the GIS intent axis (`abm_auto/gis/_intent.py`).

## Goal

Close the autonomous loop: **one sentence → a runnable GIS model**. When the GIS
intent axis routes a story to the GIS path, codegen emits model code that *loads
geographic data → builds the GIS space → runs the mechanism*, then runs through
A's / GeoNetwork's gates.

## The two halves (split by what needs the LLM)

```
story --(LLM)--> GISModelSpec --(deterministic)--> generated model code --> run + gate
        ^ story->spec extraction       ^ spec->code generation
        (needs API; last)              (offline, testable; FIRST)
```

- **`GISModelSpec` → code (deterministic, offline, testable):** a typed spec
  (spatial_type, data source, mechanism params) is rendered to runnable Python via
  per-spatial-type templates. This is the half we build + test first, with no API.
- **story → `GISModelSpec` (LLM, last):** the Phase -1 / mechanism-extraction LLM
  turns the story into the typed spec. Needs API + the lock-predictions discipline.

## Hard constraints

1. **Zero changes to the existing codegen path.** A GIS branch is additive; the
   non-GIS template path is untouched. Base gates stay green.
2. **Reuse the GIS runtime.** Generated raster models use `RasterSpace`; network
   models use `GeoNetwork`. Codegen emits *calls into* the runtime, not new physics.
3. **GIS deps stay in the `[gis]` extra**; generated GIS code lazy-imports.

## Components

### B1 `GISModelSpec` (typed schema) — `abm_auto/gis/_model_spec.py`
A dataclass: `spatial_type` (raster|network), `data` (path/loader hint + CRS target),
`mechanism` (a small enum + params, e.g. `sir`/`diffusion` for raster,
`routing_load`/`risk_exposure` for network), `outputs`, `seed`. JSON-(de)serializable;
`validate()` rejects unknown spatial types / missing params (fail at parse, not run).

### B2 GIS templates → code — `abm_auto/gis/_templates.py`
`render(spec) -> {"main.py": "...", ...}` per spatial type: raster template emits
`load_raster → RasterSpace → run_raster_sir → spatial gate → map`; network template
emits `load_vector → GeoNetwork → road model → gate → map`. Deterministic strings;
no placeholders in the output.

### B3 GIS codegen-fidelity gate — `abm_auto/gis/_codegen_gate.py`
Deterministic structural checks on generated code (the GIS analogue of the ADR-016
fidelity wall): imports from `abm_auto.gis` only; the right loader for the
spatial_type; no lat/lon used for metric math (degree/meter mix); array indexing in
`[row, col]` order; the gate is actually called. Returns pass/fail + reasons —
never trusts the generator's word.

### B4 story → `GISModelSpec` (LLM) — `abm_auto/gis/_extractor.py`
Phase -1 GIS extraction: the LLM reads the story (already flagged GIS by the intent
axis) and emits the typed `GISModelSpec`. Confidence-gated; GIS-but-underspecified
→ clarification halt (reuse ⑤). **Needs API; built last; predictions locked first.**

### B5 wiring
intent (GIS?) → B4 (story→spec) → B1.validate → B2.render → B3.gate → run + A/GeoNetwork gate.

## Decomposition (offline first)

1. B1 `GISModelSpec` + validate (offline, tested)
2. B2 raster template → code; generate + **execute** a raster-SIR model end-to-end (offline)
3. B2 network template → code; generate + execute a GeoNetwork model (offline)
4. B3 codegen-fidelity gate (offline; passes good code, fails injected faults)
5. B4 LLM story→spec extractor (API; locked predictions; last)
6. B5 wiring + an end-to-end "structured spec → runnable model" demo + zero-change proof

## Validation

- Offline (B1–B3, B5): generate code from a spec, **run it**, confirm A's/GeoNetwork's
  science gate passes; the fidelity gate fails on injected faults. No API.
- B4: locked-prediction reproduction-style check that the LLM spec matches a few
  hand-written reference specs.

## Out of scope

Vector/point templates (raster + network first), and any change to the non-GIS path.
