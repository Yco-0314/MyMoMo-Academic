# MIR v0 Half A — FINDINGS (forward round-trip, open)

**Run:** 2026-06-23, after locking predictions
([PREDICTIONS-locked.md](PREDICTIONS-locked.md)). Implementation: `abm_auto/mir/`.
Tests: `tests/gis/test_mir_v0.py` (24 tests).

## Verdicts vs locked predictions

| Prediction | Verdict | Evidence |
|---|---|---|
| **P1 field-identity** | ✅ REPRO | spatial_type/mechanism/capability/data_path/seed/params all survive spec→MIR→spec on 5 caps |
| **P2 fidelity tokens survive** | ✅ REPRO | `mir.fidelity.required_tokens == cap.required_tokens` (+ gate, wrong_space) through json round-trip |
| **P3 byte-identical render** | ✅ REPRO | `render(round_tripped) == render(original)` byte-for-byte on 5 caps |
| **P4 gate + execute survive** | ✅ REPRO | round-tripped spec passes `gis_codegen_gate` + executes + prints science-gate PASS on 5 caps |
| **P5 extensions seam** | ✅ REPRO | `extensions == {}` for GIS; an injected `{"search_space":…,"audiences":…}` produces byte-identical GIS render (open side ignores it) |
| **P6 empty clusters survive** | ✅ REPRO | entities/state/relations/layers/metrics survive as empty through dict + JSON |
| **P7 zero-change** | ✅ REPRO | SCIENCE GATE PASS + ENGINE ORACLE PASS; base 488 passed; forbidden diff empty |

**7 / 7 predictions hold.** This is a full REPRO — the forward/open half of the
MIR is proven.

## What is proven

A real GIS model survives **`GISModelSpec → MIR → JSON → MIR → GISModelSpec →
render → run`** with:
- every field preserved (P1),
- the codegen-fidelity contract preserved so the regenerated model is still
  gateable (P2, P4),
- byte-identical generated code (P3),
- the science gate still passing on execution (P4),
- the `extensions` seam present, empty for GIS, and ignored by the open side
  even when a closed overlay is injected (P5) — the ADR-013 data contract works,
- the empty clusters (for Blueprint to fill in Half B) lossless (P6),
- zero base-engine change (P7).

The 5 capabilities exercised span raster (sir), coupled raster×network
(flood_evacuation), spatial×social (social_spatial_contagion), mechanism
(threshold_adoption), and polygon (polygon_point_zoning) — a diverse slice of the
merged `main` baseline.

## Honest scope (what this is NOT)

1. **Half A only.** The inverse round-trip (gaese `Blueprint` ↔ MIR core +
   extensions) is **not** done — that is Half B, in the closed gaese repo, and is
   what proves the open/closed *split* (drop the 3 closed clusters → still a valid
   forward Blueprint). Half A proves only that MIR core holds a forward GIS model
   losslessly.
2. **NetLogo-parity caps not exercised.** `topology_clip / raster_focal /
   raster_coverage` live on the unmerged `feat/codegen-netlogo-parity` branch.
   MIR v0 tests the merged `main` baseline. When Step 2 merges, the round-trip
   should extend to those caps (a one-line CASES addition).
3. **space × layers untested.** No existing model has both geometry and
   multi-scale layers; v0 exercised space-without-layers (GIS). The combination
   remains the known v0 gap (per the convergence analysis).
4. **GISModelSpec is thin.** It populates only space/processes/run/fidelity; the
   real test of MIR core's richness is the Blueprint round-trip (Half B).

## Next

- **Half B** (closed gaese): `Blueprint ↔ MIR core+extensions`, the inverse
  round-trip + the "MIR-core-alone is a valid forward Blueprint" proof.
- When `feat/codegen-netlogo-parity` merges: extend CASES to the 3 NetLogo caps.
