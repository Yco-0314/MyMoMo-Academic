# Anshuka 2026 Real-DEM Reproduction (candidate #10) — Design Spec

**Status:** Draft. **Date:** 2026-06-24. **Repo:** MyMoMo-GIS-Academic.
**Implements:** [ADR-023](../decisions/ADR-023-reproducibility-engine-north-star.md) candidate #10
+ [ADR-024](../decisions/ADR-024-strategic-sequencing-and-domain-migration.md) D3 step 1 (the fidelity
test-stone). **Predictions locked first:** [PREDICTIONS-locked.md](../reproduce/anshuka-2026-real-dem/PREDICTIONS-locked.md).

## Goal

Turn the honest scaffold into an **earned scientific claim**: replace the synthetic 20×20 grid in
[`_anshuka_2026.py`](../../abm_auto/gis/_anshuka_2026.py) with the **real Ba catchment SRTM DEM + OSM**
road/building/shelter layers, re-run the 5 levers, and test the locked hypothesis that real
agent-to-shelter geometry closes the magnitude gaps and recovers the P2 MISS. Single controlled
variable: **only the world geometry becomes real; the mechanism is untouched.**

This is simultaneously **ladder step #2** (real-data codegen end-to-end): it forces the
`data_path → load_raster` path to become a real, gated path instead of the `np.random` synthetic default.

## Scope (ships)

A new module `abm_auto/gis/_anshuka_real.py` (additive; the synthetic `_anshuka_2026.py` stays as the
control) that swaps ONLY the world builders:

- **`build_elevation_from_dem(dem_path, bbox, grid_size) -> np.ndarray`** — replaces the synthetic
  `_build_elevation(rng)`. Uses the existing I/O: [`_io.py`](../../abm_auto/gis/_io.py) `load_raster`
  (rasterio) to read the DEM, [`_crs.py`](../../abm_auto/gis/_crs.py) to reproject to **UTM 60S
  (EPSG:32760)** (Fiji is WGS-84 — the China GCJ-02 path does NOT apply; the mislabel verifier is
  asserted to find no offset), then clip to `bbox` and resample to `grid_size` (~100×100) to match the
  paper's 10,000-cell geometry. Elevation drives the unchanged `_bathtub_step`.
- **`load_world_from_osm(osm_path, bbox)`** — roads → a `GeoNetwork` ([`_geo_network.py`](../../abm_auto/gis/_geo_network.py))
  for shortest-path evacuation routing; buildings (`building=*`) → agent start cells; evacuation
  shelters (high-ground `amenity=shelter` / school / community centre) → target cells. Vector read via
  [`_vector_io.py`](../../abm_auto/gis/_vector_io.py); building/shelter polygons rasterised onto the grid
  via [`_coverage.py`](../../abm_auto/gis/_coverage.py) `apply_coverage`.
- **`run_scenario_real(...)`** — identical signature + mechanism to `_anshuka_2026.run_scenario`, but
  the elevation/road/building/shelter arrays come from the real-world builders above. The 5-lever sweep
  runner (`examples/reproduce_anshuka_real/run.py`) mirrors `examples/reproduce_anshuka_2026/run.py`.

## Hard constraints

1. **Single-variable discipline:** the agent mechanism, belief/vision/mobility/collaboration rules, the
   bathtub flood mechanic, n=100 agents, and the seed protocol are **byte-identical** to the first
   reproduction. Only elevation/roads/buildings/shelters become real. Any magnitude movement must be
   attributable to geometry alone.
2. **Real-data gate (ladder #2):** the run MUST verify it ran on the REAL DEM, not a synthetic fallback
   — assert the loaded elevation has real dynamic range / known Ba extent, and that `load_raster` was
   actually invoked (no `np.random` elevation). A synthetic fallback is a hard fail, not a silent pass.
   This is the fix for "the gate certifies np.random."
3. **Zero-change** to `abm_auto/runtime/`, `codegen/`, `calibration/`, `agents/`, `pipeline/` (additive
   GIS module only).
4. **Predictions locked before any run** (done — the PREDICTIONS-locked.md commit).
5. **Determinism:** same seed + same DEM/OSM inputs ⇒ identical outputs.
6. **Data provenance:** record the exact SRTM tile + OSM extract + date + license in the FINDINGS, and
   hash the input rasters so the run is reproducible by a reviewer (this is the seed of the L3 bundle, ladder #6).

## Decomposition (TDD)

1. **`build_elevation_from_dem`** on a small real DEM fixture → returns a `grid_size` float array with
   real elevation range; reproject+resample is deterministic; mislabel verifier finds no GCJ-02 offset.
2. **`load_world_from_osm`** → roads form a connected `GeoNetwork`; buildings/shelters rasterise to known
   cells; shelters sit on higher ground than buildings (sanity).
3. **`run_scenario_real` parity of mechanism** → with a *flat synthetic* DEM passed in, it reproduces the
   synthetic `run_scenario` numbers (proves only geometry changed, not the mechanism).
4. **Real-data gate** → a run with a synthetic-elevation fallback FAILS the gate; a run on the real DEM passes.
5. **The 5-lever sweep** on the real Ba grid → produces the numbers the FINDINGS will compare to PREDICTIONS-locked.

## Validation

```
.venv/bin/python -m pytest tests/gis/test_anshuka_real.py -q
.venv/bin/python examples/reproduce_anshuka_real/run.py     # the 5-lever sweep on the real grid
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science    # SCIENCE GATE: PASS
.venv/bin/python engine_oracle.py --check      # ENGINE ORACLE: PASS
# forbidden base-engine diff — must print NOTHING:
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

After the run, write `docs/reproduce/anshuka-2026-real-dem/FINDINGS.md` citing actual outputs and a
per-hypothesis (H1–H6) verdict against PREDICTIONS-locked.md.

## Data dependency

Real SRTM DEM + OSM for the Ba catchment — see
[DATA-acquisition.md](../reproduce/anshuka-2026-real-dem/DATA-acquisition.md). Data download + the real
run need the user's environment (network + the `[gis]` extra); the module, tests, and locked predictions
are written first.

## Non-goals (deferred)

- P6 Sobol'/variance-based sensitivity (needs SALib + many runs) — ladder step beyond #10.
- The P5 prior-experience gate (the mechanism fix) — that is ladder step #5 (calibration), and H5
  predicts the P5 low-belief deviation persists until then.
- A general DEM-driven flood solver — this is one study area; generality is not the goal of the test-stone.
