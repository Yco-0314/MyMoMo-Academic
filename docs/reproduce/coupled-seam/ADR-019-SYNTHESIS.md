# ADR-019 Implementation Synthesis

**Date:** 2026-06-20
**Base commit:** `a9714dd`
**Scope:** What ADR-019 has become in code after the coupled seam, temporal and
dynamic flood, dynamic congestion routing, space zoo, mechanism library,
spatial validation/calibration, codegen registry, and self-extension scaffold
phases.

## Current Architecture

GIS is still an additive subpackage over the base `abm-auto` engine. The base
engine remains byte-identical; GIS work lives under `abm_auto/gis/`, with tests
under `tests/gis/` and reproduction/status docs under `docs/reproduce/`.

The practical architecture has four small seams:

1. **Layer adapters**
   - `RasterSpace`, `GeoNetwork`, `PointSpace`, `PolygonSpace`, and
     `RasterTimeline`.
   - These wrap geospatial state without changing the base runtime.

2. **Cross-layer operators**
   - `_coupling.py` holds the reusable spatial reads, such as
     `flood_depth_per_edge`, `combined_neighbors`, `point_risk_per_edge`, and
     `assign_points_to_polygons`.
   - These are the real coupled seam. They are small functions, not a framework.

3. **Mechanism-neighbor interface**
   - `_mechanisms.py` has space-agnostic mechanisms over `neighbors_of(i)`.
   - `run_contagion` and `run_threshold_adoption` can run over any layer that can
     provide neighbor ids.

4. **Capability registry and fidelity wall**
   - `_capabilities.py` is the codegen truth-table.
   - `_templates.py` renders only registered renderable capabilities.
   - `_codegen_gate.py` checks required tokens and wrong-runtime patterns.
   - `_self_extension.py` reports deterministic render/halt/scaffold outcomes.

## What Is Proven

The platform now has eight coupled/runtime adapter cells:

| Cell | Layers | Gate |
|---|---|---|
| Static flood evacuation | `GeoNetwork` x `RasterSpace` | `flood_gate` |
| Social-spatial contagion | spatial neighbors x social `Network` | `social_lift_gate` |
| Point-network risk | `PointSpace` x `GeoNetwork` | `point_network_risk_gate` |
| Polygon-point zoning | `PolygonSpace` x `PointSpace` | `polygon_point_zoning_gate` |
| Time-varying flood | `RasterTimeline` x `GeoNetwork` | `temporal_flood_gate` |
| Dynamic flood evacuation | `RasterTimeline` x `GeoNetwork` x moving agents | `dynamic_flood_reroute_gate` |
| Dynamic congestion routing | `GeoNetwork` x moving agents x per-tick edge loads | `dynamic_congestion_reroute_gate` |
| Dynamic incident routing | `GeoNetwork` x moving agents x per-tick incident events | `dynamic_incident_reroute_gate` |

The platform also has mechanism and layer-D validation cells:

| Cell | Runtime surface | Gate |
|---|---|---|
| Contagion mechanism | `run_contagion(neighbors_of)` | `mechanism_contagion_gate` |
| Threshold adoption mechanism | `run_threshold_adoption(neighbors_of)` | `mechanism_space_gate` |
| Raster spatial validation | simulated raster vs observed raster metrics | `raster_validation_gate` |
| Raster spatial calibration | deterministic grid search over raster loss | `raster_spatial_calibration_gate` |
| Observed raster bridge | local GeoTIFF/RasterField/RasterSpace observed target with provenance | `observed_raster_bridge_gate` |
| Observed raster repro pack | local manifest-backed observed GeoTIFF calibration | `observed_raster_repro_gate` |
| Base calibration objective bridge | GIS `simulate(params, targets) -> [spatial_loss]` adapter consumed by base ABC | `base_calibration_objective_bridge_gate` |
| Spatial method transfer runtime | Forman-style graph curvature transferred across `RasterSpace` and `GeoNetwork` neighbor adapters | `spatial_method_transfer_gate` |
| Network observed validation | simulated edge values vs observed edge-keyed target | `network_observed_validation_gate` |
| Traffic count edge matching | count-station rows matched to `GeoNetwork` edges and aggregated into observed edge values | `traffic_count_edge_matching_gate` |
| Traffic count repro pack | manifest-backed local count-station CSV to observed edge target with diagnostics | `traffic_count_repro_gate` |
| Official traffic-count intake | manifest-backed official count samples with checksums, CRS, preparation steps, and structured match diagnostics, including a bounded Seattle SDOT real public sample | `official_traffic_count_intake_gate` |
| Seattle centerline edge matching | official Seattle SDOT count points matched to official Seattle Streets centerline segments with street/objectid diagnostics | `official_centerline_edge_match_gate` |
| Official traffic calibration bridge | official Seattle count-to-centerline observed edge target consumed by deterministic network grid-search calibration | `official_traffic_calibration_gate` |
| Official dynamic congestion validation smoke | dynamic congestion edge-load output evaluated against official Seattle count-to-centerline observed target | `official_dynamic_congestion_validation_gate` |
| Official dynamic congestion repro pack | manifest-backed bounded Seattle dynamic congestion smoke with per-edge residual diagnostics | `official_dynamic_congestion_repro_gate` |
| Official incident-event intake | manifest-backed official-style incident closure/reopen rows with checksum, provenance, and edge-match diagnostics | `official_incident_event_edge_match_gate` |
| Official dynamic incident event effect smoke | manifest-backed incident events compared against a no-incident dynamic routing baseline | `official_dynamic_incident_event_effect_gate` |
| Official dynamic incident repro pack | manifest-backed dynamic incident event-effect smoke with locked expected diagnostics | `official_dynamic_incident_repro_gate` |
| Incident timestamp clock map | timestamped incident intervals converted into tick closure/reopen events with checksum and clock diagnostics | `official_incident_clock_map_gate` |
| Official incident real sample pack | bounded King County road-closure sample through timestamp clock, incident intake, and dynamic event-effect smoke | `official_incident_real_sample_gate` |

The official dynamic congestion smoke now exposes per-edge residual
diagnostics, and the repro pack fixes its parameters and expected evidence in a
manifest; this improves reproducibility and auditability, not scientific
strength.

The official incident validation smoke applies the same cautious bridge pattern
to dynamic incident events: the committed fixture is synthetic official-style
data, and the gate proves event-effect plumbing into the moving-agent runtime,
not traffic-flow validity, production map matching, real incident calibration,
or optimal incident management.

The incident repro pack fixes that smoke into a manifest-backed rerunnable
bundle; it strengthens auditability, not scientific validity.

The timestamp clock bridge adds the deterministic preparation layer needed
before bounded real incident feeds; it strengthens clock semantics, not dynamic
routing validity.

The official incident real sample pack applies that preparation layer to a
bounded King County Emergency Management road-closure sample. It improves
real-data provenance and auditability while preserving the same boundary: not
traffic-flow validity, not production map matching, not route-choice
validation, not incident calibration, and not a full live feed.

The spatial method transfer runtime cell adds the first small method-transfer
proof over existing neighbor adapters. The same Forman-style edge-curvature
method runs over a 1x4 `RasterSpace` rook-neighbor chain and a four-node
`GeoNetwork` chain, producing the same curvature signature. This closes the
runtime/gate side of ADR-019 layer E while staying narrow: not full Ollivier-
Ricci curvature, not TDA, not spatial validation, and not automatic scientific
method discovery.

The current codegen registry has one registered nonrenderable GIS gap:
`spatial_method_transfer`. Its runtime gate exists, but no runnable codegen
template exists yet. The currently renderable capabilities are:

- `raster_sir`
- `network_routing_load`
- `flood_evacuation`
- `social_spatial_contagion`
- `point_network_risk`
- `polygon_point_zoning`
- `temporal_flood_evacuation`
- `dynamic_flood_evacuation`
- `dynamic_congestion_routing`
- `raster_spatial_validation`
- `raster_spatial_calibration`
- `mechanism_contagion`
- `mechanism_threshold_adoption`

Self-extension is still bounded. It can classify unknown, invalid, renderable,
and registered-but-nonrenderable codegen-template requests. It can emit a
structured scaffold package for `spatial_method_transfer` or future registered
gaps. It does not generate source code by itself.

## What Is Not Proven

These are intentionally outside the current evidence:

- Official traffic-data download, full map matching, CRS reprojection for count
  stations, traffic-flow validity, capacity, BPR-style road dynamics, observed
  traffic-flow calibration, dynamic-congestion validity, or calibrated
  congestion.
- Real-time evacuation optimality.
- Real social diffusion against observed social-network data.
- Observed flood raster ingestion in generated templates.
- Remote GHSL/WorldPop download, committed official GHSL/WorldPop pixels, hidden
  raster resampling, complete official traffic-count datasets, or production
  traffic-count map matching against municipal/state centerlines.
- Full `BayesianCalibrator.run` workspace/artifact flow for GIS, RF/PyMC
  orchestration, or changes inside `abm_auto/calibration/`.
- Method-transfer beyond the first Forman-style graph-curvature proof cell.
- A shared `CoupledModel` or `CoupledSpace` abstraction.

## Why `CoupledModel` Is Still Deferred

The repeated shape is now clear:

```text
model owns layers -> small operator reads across layers -> mechanism/model loop
-> adapter-specific summary -> deterministic gate
```

That repeated shape is useful, but it is not yet a class contract. Outputs remain
adapter-specific: edge depths, neighbor sets, edge risk scores, polygon groups,
temporal evacuation summaries, dynamic agent states, raster pattern metrics, and
calibration results.

Dynamic flood and dynamic congestion now provide two true per-tick lifecycles:

```text
dynamic flood: read flood frame -> compute flooded edges -> plan/reroute at nodes
-> move agents -> summarize tick

dynamic congestion: compute costs from previous edge loads -> plan/reroute at
nodes -> enter/continue edges -> apply load-based movement penalty -> summarize
tick
```

They share a lifecycle shape, but Phase 1 keeps them as separate local modules
because no concrete shared API pressure has appeared yet. Extraction becomes
justified only when a third dynamic lifecycle mechanism or codegen registry
wiring needs the same lifecycle pieces: layer registration, CRS negotiation,
per-tick update order, route invalidation, agent lifecycle hooks, or common
temporal metrics.

## Verification Baseline

Latest verified baseline after Traffic Count Repro Pack Phase 1:

```bash
.venv/bin/python -m pytest tests/gis -q
# 423 passed, 1 skipped

.venv/bin/python engine_oracle.py --science
# SCIENCE GATE: PASS

.venv/bin/python engine_oracle.py --check
# ENGINE ORACLE: PASS

.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
# 488 passed, 4 skipped, 1 warning
```

Base-engine diff check remains mandatory:

```bash
git diff --name-only <base>..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
# expected: empty
```

Do not run `engine_oracle.py --science` and `engine_oracle.py --check` in
parallel. They touch the same example output surface and can race.

## Recommended Next Work

### Option 1: Third Dynamic Lifecycle Mechanism Or Lifecycle Helper

Add a third dynamic mechanism, or extract a tiny lifecycle helper only if the
third mechanism repeats the same code shape with real duplication pressure.

Success condition: shared lifecycle code removes concrete duplication without
forcing flood or congestion outputs into a fake common model type.

### Option 2: Real-Data Spatial Validation/Calibration Bridge

Extend the manifest-backed observed-raster bridge beyond local test fixtures:

- add a human-downloaded official GHSL/WorldPop clip with source attribution, if
  repository size and license constraints permit;
- extend official traffic-count intake beyond the bounded Seattle SDOT sample to
  a reviewer-prepared Caltrans AADT corridor slice or other public agency
  sample, while keeping large official raw datasets out of git;
- extend from base ABC smoke compatibility to full `BayesianCalibrator.run`
  workspace/artifact flow without editing `abm_auto/calibration/`;
- keep the GIS adapter additive.

Success condition: observed raster/vector targets change calibrated parameter
selection under deterministic gates, with provenance and no hidden resampling.

### Option 3: Add A Planned Registered Gap, Then Exercise Scaffold

The scaffold surface is idle because all registered GIS capabilities are
renderable. To test scaffold honestly again, first register a real planned gap
as nonrenderable. Do not invent a fake gap only to exercise the scaffold.

Success condition: the registered gap reports `action="scaffold"` with expected
files, test targets, and `required_human_review=True`, then a later template
phase closes it.

## Working Rule

Keep every next phase additive, TDD-first, and gate-first. A capability is not
accepted because it is generated or documented; it is accepted only when the
deterministic runtime gate, codegen fidelity gate, GIS suite, science oracle, and
base byte oracle agree.
