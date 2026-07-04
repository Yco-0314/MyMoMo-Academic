# Coupled multi-layer space seam - status

The coupled-seam spine of [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md)
started with **two model-level adapters**, so the seam became real (one adapter =
hypothetical seam; two = real). The space-zoo work adds point-network and
polygon-point coupling cells; time-varying flood adds the first temporal layer
cell; and dynamic flood evacuation now adds Phase 2 per-tick lifecycle evidence
with moving agents. Raster spatial validation adds the first layer-D validation
cell over simulated-vs-observed raster patterns. All cells are additive,
deterministic, gated, and prove out on the existing GIS runtime with **zero
changes** to the base engine. GIS spatial calibration adds the next layer-D
cell by optimizing raster spatial validation loss with deterministic grid
search. Coupled flood codegen adds the first runnable multi-layer template for
the static raster-network flood cell; social-spatial codegen adds the first
runnable spatial-neighbor plus social-network template; space-zoo codegen adds
runnable point-network and polygon-point templates; validation/calibration
codegen adds runnable layer-D templates; mechanism codegen adds the first
runnable neighbor-callable mechanism template; and temporal flood codegen adds
the first runnable temporal template. Dynamic flood codegen adds the first
runnable moving-agent dynamic template. Dynamic congestion routing adds the
second runtime moving-agent lifecycle mechanism without flood rasters. Dynamic
congestion codegen adds runnable synthetic template coverage for that second
dynamic lifecycle cell. Dynamic incident routing adds the third runtime
moving-agent lifecycle mechanism with per-tick road closures and reopenings.
Dynamic incident codegen adds runnable synthetic template coverage for that
third dynamic lifecycle cell. The dynamic routing lifecycle helper now factors
out repeated private mechanics for moving-agent state, edge entry, movement,
finalization, and summary counts, while keeping `CoupledModel` deferred.
Terrain-to-network coupling adds the first terrain bridge consumer in the GIS
seam: a manifest-backed ASCII heightfield can be sampled along road edges to
produce elevation delta, grade proxy, and terrain-weighted edge cost, without
claiming 3D rendering or traffic-flow physics. Terrain-aware routing consumes
that edge-cost signal in a shortest-path comparison, proving route choice can
change under terrain-derived weights while still avoiding traffic-flow, vehicle
dynamics, or 3D terrain-physics claims.

## The adapters

| Adapter | Layers coupled | Cross-layer operator | Gate | Answers |
|---|---|---|---|---|
| **Flood** | road `GeoNetwork` × flood `RasterSpace` | `flood_depth_per_edge` (sample raster along each edge) | `flood_gate`: more flood → worse evacuation | Q1 urban flood |
| **Social-spatial** | a GIS spatial layer × a social `Network` | `combined_neighbors` (spatial ∪ social ties) | `social_lift_gate`: social ties extend reach | Q2 GIS + social network |
| **Point-network risk** | `PointSpace` × road `GeoNetwork` | `point_risk_per_edge` (nearby point count per edge) | `point_network_risk_gate`: loaded risky edge lights up | space zoo point adapter |
| **Polygon-point zoning** | `PolygonSpace` × `PointSpace` | `assign_points_to_polygons` (point ids grouped by region) | `polygon_point_zoning_gate`: known points land in known regions | space zoo polygon adapter |
| **Time-varying flood** | `RasterTimeline` × road `GeoNetwork` | `flood_depth_per_edge` per `RasterTimeline.at(t)` frame | `temporal_flood_gate`: flood worsens then recedes in repeated evacuation outcomes | temporal flood layer |
| **Dynamic flood evacuation** | `RasterTimeline` × `GeoNetwork` × moving agents | `flood_depth_per_edge` per tick | `dynamic_flood_reroute_gate`: rerouting changes deterministic moving-agent outcomes | dynamic evacuation layer |
| **Dynamic congestion routing** | `GeoNetwork` × moving agents × per-tick edge loads | congestion-dependent edge cost per tick | `dynamic_congestion_reroute_gate`: rerouting changes deterministic congestion outcomes | second dynamic lifecycle |
| **Dynamic incident routing** | `GeoNetwork` × moving agents × per-tick incident events | edge closure/reopen events update the routable graph per tick | `dynamic_incident_reroute_gate`: rerouting changes deterministic incident outcomes | third dynamic lifecycle |
| **Terrain-network cost** | terrain bridge heightfield × road `GeoNetwork` | `terrain_elevation_delta_per_edge`, `terrain_grade_proxy_per_edge`, `terrain_cost_per_edge` (sample heightfield along each edge) | `terrain_network_coupling_gate`: terrain changes network edge cost | terrain / physical-space bridge |
| **Terrain-aware routing** | terrain bridge heightfield × road `GeoNetwork` | `terrain_aware_shortest_path` (compare length-only vs terrain-cost route) | `terrain_aware_routing_gate`: terrain changes shortest-path routing | terrain / route-choice bridge |
| **Line × polygon clip** | polyline layer × polygon layer | `lines_in_polygon` (clipped line length inside polygon) | `line_polygon_gate`: inside-clipped length positive, outside-clipped length zero | NetLogo parity (DE-9IM) |
| **Polygon × polygon overlap** | polygon layer × polygon layer | `polygon_overlap_areas` (STRtree-indexed pairwise intersection area) | `polygon_overlap_gate`: identical-input self-overlap is full area, empty-layer overlap is empty | NetLogo parity (DE-9IM) |

The table's operator column names only the cross-layer read operators. Those
spatial operators live in `abm_auto/gis/_coupling.py`. Temporal flood reuses the
raster-network operator per frame and keeps the time-loop model summary in
`abm_auto/gis/_flood_model.py`. Dynamic flood evacuation reuses the same
raster-network operator per tick, then runs node planning/rerouting, edge
movement, and per-step summaries in `abm_auto/gis/_dynamic_flood.py`. Dynamic
congestion routing uses only `GeoNetwork` plus moving agents and per-tick edge
loads; it keeps congestion costs and movement summaries in
`abm_auto/gis/_dynamic_congestion.py`. Dynamic incident routing also uses only
`GeoNetwork` plus moving agents, but updates edge availability from incident
events; it keeps closure-aware route invalidation and movement summaries in
`abm_auto/gis/_dynamic_incident.py`. Flood gates live in
`abm_auto/gis/_flood_gate.py`; congestion gates live in
`abm_auto/gis/_congestion_gate.py`; incident gates live in
`abm_auto/gis/_incident_gate.py`. Terrain-network cost is a static cross-layer
operator in `abm_auto/gis/_coupling.py`; it consumes terrain bridge manifests
with explicit extent and CRS, and remains a coupling/cost signal rather than a
renderer, mesh generator, hydrology model, or traffic-flow physics model.
Terrain-aware routing is also static and lives in `_coupling.py`: it assigns
the terrain-derived edge costs to a temporary graph and compares NetworkX
shortest paths under `length` and `terrain_cost`. It proves terrain can affect a
route-choice calculation, not that MyMoMo now validates real traffic flow,
vehicle dynamics, or 3D terrain physics.

## What the adapters reveal as the *real* seam

- **Cross-layer operators are the seam.** A coupled model holds two or more layers and reads
  across them through small spatial operators in `_coupling.py`, or through a thin
  model orchestration loop that applies those operators over time. Dynamic flood
  evacuation adds the first per-tick lifecycle evidence, but it still composes the
  same small operator rather than requiring a grand class.
- **Mechanisms can be space-agnostic.** `run_contagion` takes a
  `spatial_neighbors_of` function, so the same contagion runs over a raster grid or a
  GeoNetwork. This is layer C of the vision (a reusable, space-agnostic mechanism
  library) showing up naturally.
- **Each coupling has its own deterministic gate.** Verification stays structural and
  per-adapter (the anti-fabrication discipline), not a shared rubber stamp.

## What is deliberately NOT extracted yet (YAGNI)

A grand `CoupledModel` / `CoupledSpace` class is still not extracted. The
adapter table now includes three dynamic lifecycle mechanisms: dynamic flood
evacuation, dynamic congestion routing, and dynamic incident routing. They all
use a per-tick loop with node planning/rerouting, edge movement, and step
summaries. The lifecycle-helper audit in
`docs/superpowers/specs/2026-07-03-dynamic-lifecycle-helper-audit-design.md`
found enough repeated mechanics to justify
`abm_auto/gis/_dynamic_routing_lifecycle.py`, a tiny private helper for the
moving-route state shape: deterministic edge keys, blocked-edge graph copies,
edge entry, no-carryover edge movement, reroute counters, not-arrived
finalization, common movement counts, mean arrival time, and agent-state
serialization. The helper is now used by dynamic flood, dynamic congestion, and
dynamic incident routing. It is not a model abstraction. Outputs remain
adapter-specific: per-edge depths, neighbour sets, per-edge point counts, point
groups by polygon, repeated evacuation summaries, dynamic flood agent states,
dynamic congestion load summaries, and dynamic incident closure/reroute
summaries. Do not extract `CoupledModel` yet; extraction still waits for
concrete shared lifecycle API pressure such as layer registration, CRS
negotiation, per-tick update order, route invalidation, agent lifecycle hooks,
or common temporal metrics.

## Verification

Adapters are unit-tested on synthetic layers; the flood path is real-data-capable
when callers provide a road network and flood DEM; social tests use deterministic
NetworkX graphs. Temporal flood evidence is synthetic: `temporal_flood_gate`
verifies repeated evacuation outcomes worsen and then recede across flood frames.
Phase 2 dynamic flood evidence is also synthetic:
`dynamic_flood_reroute_gate` compares rerouting enabled and disabled to prove a
deterministic moving-agent outcome difference under time-varying flood. This is
now moving-agent dynamic evacuation, but it is still not a traffic-flow model or
an optimal emergency evacuation model. Dynamic congestion routing evidence is
synthetic too: `dynamic_congestion_reroute_gate` compares rerouting enabled and
disabled to prove congestion-sensitive moving agents can change deterministic
outcomes, without claiming traffic-flow validity. Dynamic incident routing
evidence is synthetic too: `dynamic_incident_reroute_gate` compares rerouting
enabled and disabled under per-tick closure events to prove incident-sensitive
moving agents can change deterministic outcomes, without claiming real traffic
flow or optimal incident management. The targeted temporal/flood tests cover
`test_flood_model.py`, `test_dynamic_flood.py`, `test_flood_gate.py`, and
`test_temporal.py`; dynamic congestion is covered by
`test_dynamic_congestion.py` and `test_congestion_gate.py`; dynamic incident is
covered by `test_dynamic_incident.py`, `test_incident_gate.py`, and its
codegen template coverage in `test_codegen.py` / `test_codegen_gate.py`;
space-zoo gates cover point-network risk and polygon-point zoning in
`test_space_zoo_gate.py`. Terrain-network and terrain-aware routing are covered
by `test_terrain_network_coupling.py` and `test_terrain_aware_routing.py`.
The full GIS and base-engine zero-change gates remain final branch verification
commands for this implementation. See `tests/gis/test_coupling.py`,
`test_social.py`, `test_point_space.py`, `test_polygon_space.py`, and
`test_risk.py` for the other adapter cells.

Mechanism Library Phase 1 adds a small mechanism seam: `run_contagion` and
`run_threshold_adoption` operate over `neighbors_of(i)`, while raster, point,
and GeoNetwork adapters translate spaces into that callable. This is layer C
evidence for the mechanism x space matrix. It still does not justify a
`CoupledModel`: the new seam is a mechanism-neighbor interface, not a shared
multi-layer lifecycle abstraction.

Mechanism Codegen Template Phase 1 adds the first runnable mechanism-library
codegen cell: explicit `mechanism_threshold_adoption` specs render a synthetic
chain `neighbors_of(i)` callable, call `run_threshold_adoption`, and verify with
`mechanism_space_gate`.

Mechanism Contagion Codegen Template Phase 1 closes the remaining registered
mechanism-library codegen gap: explicit or implicit `mechanism_contagion` specs
render a synthetic chain `neighbors_of(i)` callable, call `run_contagion`, and
verify with `mechanism_contagion_gate`. The gate compares connected and isolated
neighbor seams for stochastic contagion and states the boundary clearly: this is
synthetic mechanism evidence, not spatial validation.

Raster Spatial Validation Phase 1 adds the first layer-D validation seam:
`raster_pattern_metrics`, `raster_spatial_loss`, and `raster_validation_gate`
compare simulated and observed raster patterns using overlap and centroid
distance, while computing and reporting Moran's I error. This is spatial
validation evidence only. It does not yet wire Bayesian calibration, load
observed rasters from disk, or modify `abm_auto/calibration/`.

GIS Spatial Calibration Adapter Phase 1 wraps `raster_spatial_loss` in a
deterministic grid-search objective: `params -> simulator(params) -> raster ->
metrics -> loss`. The synthetic gate proves the adapter can select a lower-loss
raster-producing parameter set. This is calibration over spatial loss, but it
is not Bayesian posterior inference, multi-fidelity scheduling, observed raster
I/O, or a change to `abm_auto/calibration/`.

Observed Raster Calibration Bridge Phase 1 adds the first real-data layer-D
bridge: `_observed_raster_bridge.py` loads or wraps local observed GeoTIFF,
`RasterField`, or `RasterSpace` targets, preserves source/dataset provenance,
and feeds the observed array into the existing raster validation and
deterministic grid-search calibration adapters. The gate proves a
provenance-bearing observed raster target can select lower-loss parameters.
This is local observed-raster plumbing only: no remote GHSL/WorldPop download,
no hidden reprojection/resampling, no vector/network calibration, and no
Bayesian posterior inference.

Observed Raster Repro Pack Phase 1 adds manifest-backed reproducibility around
that bridge: `_observed_raster_repro.py` validates a local JSON manifest,
resolves the GeoTIFF path, loads the observed target, and runs deterministic
calibration with manifest-defined threshold/grid/expected parameters. The
committed `data/fixtures/observed-raster/test_observed.tif` is explicitly a
tiny local test fixture, not official GHSL or WorldPop pixels. The pack documents
the real workflow: download an official GHSL/WorldPop tile externally, clip a
small window, write a manifest, then run the same loader/gate without changing
runtime code.

GIS Base Calibration Objective Bridge Phase 1 adds
`_calibration_objective_bridge.py`, a simulator-like adapter that returns
`np.array([spatial_loss])` from `simulate(params, targets)`. Existing base
calibration backends already optimize `||sim_stats - obs_stats||`, so the GIS
observed target becomes `obs_stats=np.array([0.0])` with
`targets=["spatial_loss"]`. The gate runs the base ABC backend against GIS
spatial loss and selects a zero-loss raster parameter region. This proves
interface compatibility without editing `abm_auto/calibration/`; it is not the
full `BayesianCalibrator.run` workspace/artifact pipeline.

Network Observed Validation Phase 1 adds `_network_validation.py`, the first
vector/network layer-D validation seam. It stores observed edge-keyed values
with provenance, compares simulated edge loads against the observed edge subset,
reports coverage, RMSE, relative RMSE, bias, top-edge match, and runs
deterministic grid-search calibration over that loss. The gate proves observed
edge values can select lower-loss network parameters. This is edge-level
validation plumbing only: no count-station ingestion, no map matching, no
traffic-flow validity claim, and no congestion capacity calibration.

Traffic Count Edge Matching Phase 1 adds the next local network-validation
bridge: `TrafficCountStation` rows near synthetic `GeoNetwork` edges are matched
to nearest edges, aggregated with `aggregation="sum"`, and checked through
`network_validation_gate` by `traffic_count_edge_matching_gate`. This proves
count-station-to-edge observed-value plumbing only: not traffic-flow
calibration, not full map matching, and not congestion capacity validation.

Traffic Count Repro Pack Phase 1 adds `_traffic_count_repro.py` and
`data/fixtures/traffic-counts/`: a local JSON manifest points at a local
count-station CSV, validates source/license/CRS/column metadata, loads stations,
matches them to a synthetic `GeoNetwork`, emits explicit match diagnostics, and
feeds the resulting `ObservedNetworkTarget` into `network_validation_gate`. This
is manifest-backed local reproducibility plumbing only: no official traffic
download, no CRS reprojection, no full map matching, and no traffic-flow or
capacity calibration.

Official Traffic Count Intake Pack Phase 1 adds `_official_traffic_intake.py`
and `data/fixtures/official-traffic-counts/`: a manifest-backed official-data
intake contract for externally prepared Caltrans AADT / Traffic Census slices.
The committed fixture is synthetic, but the manifest records source agency,
source URL, license text, download date, raw and prepared checksums, CRS,
preparation steps, count metric, year, geographic scope, match thresholds, and
boundary notes. The gate reuses the existing traffic-count loader and edge-match
diagnostics, then refuses stale checksums, CRS mismatch, low coverage, excessive
match distance, or unexpected observed edge values. This is official-data intake
and map-match-quality plumbing only: no official data is committed, no remote
download occurs in tests, no hidden reprojection happens, and no traffic-flow
validity is claimed.

Official Traffic Count Repro Pack Phase 2 adds the first committed real public
official traffic-count sample: Seattle SDOT Traffic Study Flow Counts 2023
FLOWMAP. The pack stores a bounded raw ArcGIS sample, a normalized prepared CSV,
SHA-256 manifest checksums, and structured edge-match diagnostics. It proves
official count intake plus match-quality reporting on real public coordinates
and ADT values. It does not prove traffic-flow validity, congestion calibration,
or production map matching against Seattle centerlines.

Official Incident Event Intake Phase 1 adds `_official_incident_intake.py` and
`data/fixtures/official-incident-events/`: a manifest-backed official-style
incident-event intake contract for prepared closure/reopen rows. The gate
validates provenance, checksums, CRS, deterministic CSV event parsing, nearest
edge matching, explicit diagnostics, and dynamic-incident-compatible event
dictionaries. This is official-data intake and edge-match plumbing only: the
committed fixture is synthetic official-style data, no remote download occurs,
no production map matching is claimed, and no real traffic-flow or optimal
incident-management validity is claimed.

Official Dynamic Incident Event Effect Smoke Phase 1 adds
`_official_incident_validation.py`, which consumes the manifest-backed
`matched_incidents` emitted by `_official_incident_intake.py`, runs the existing
dynamic incident moving-agent model with and without those events, and reports
arrival-delay, waiting, closed-edge-step, arrived-count, and stranded-count
deltas. The gate passes only when the official-style incident events change the
dynamic model output. This proves an intake-to-runtime event-effect bridge; it
is not traffic-flow validity, not production map matching, not real incident
calibration, and not optimal incident management.

Official Dynamic Incident Repro Pack Phase 1 adds
`_official_incident_repro.py` and
`data/fixtures/official-incident-events/official-dynamic-incident-repro/`.
The pack points at the existing incident intake manifest, fixes the event-effect
smoke parameters, checks expected matched incident count, arrival delay, waiting
delta, closed-edge steps, max closed edges, and changed flag, and emits a
manifest-backed repro gate. This improves reproducibility and auditability of
the official incident smoke; it is still synthetic official-style evidence, not
traffic-flow validity, production map matching, real incident calibration, route
optimality, or optimal incident management.

Incident Timestamp-to-Simulation-Clock Bridge Phase 1 adds
`_official_incident_clock.py` and
`data/fixtures/official-incident-events/timestamp-clock-map/`. The bridge maps
timestamped incident intervals (`started_at` / `ended_at`) into deterministic
tick closure/reopen events using an explicit simulation clock, verifies fixture
checksums, and gates the expected close-at-1 / reopen-at-3 conversion. This is
data-preparation rigor for future real incident feeds; it does not change the
existing tick-based incident intake contract and does not claim traffic-flow
validity, production map matching, incident calibration, or route-choice
validity.

Official Incident Real Sample Pack Phase 1 adds
`_official_incident_real_sample.py` and
`data/fixtures/official-incident-events/king-county-road-closures-sample/`.
It stores a bounded King County Emergency Management road-closure sample,
verifies checksums, prepares timestamped closure intervals, maps them to
simulation ticks through the incident clock bridge, and runs the existing
incident intake plus dynamic event-effect smoke on a deterministic local
GeoNetwork. This is bounded real official incident-data plumbing only: not
traffic-flow validity, not production map matching, not route-choice
validation, not incident calibration, and not a full live feed.

Seattle Centerline Edge Matching Phase 1 adds `_official_centerline_match.py`
and a bounded official Seattle Streets fixture paired with the Seattle SDOT 2023
FLOWMAP count sample. The adapter verifies the count manifest checksums, verifies
the centerline raw checksum, parses ArcGIS polyline `paths`, splits them into
straight `GeoNetwork` segments, and reports station-to-street/objectid
diagnostics. The deterministic gate proves that the three committed official
count points match official Seattle Streets centerline geometry with complete
coverage and bounded distance. It is still a small reproducibility bridge only:
not full-city Seattle map matching, not traffic-flow validity, not congestion
calibration, and not a production geocoder.

Official Traffic Calibration Bridge Phase 1 adds
`_official_traffic_calibration.py`, which converts the Seattle SDOT official
count-to-centerline match report into an `ObservedNetworkTarget` and feeds it
through the existing deterministic network calibration grid search. The default
demand-scale simulator is deliberately proportional and only proves that
official observed edge targets can drive the calibration objective. It is not
traffic-flow validity, congestion calibration, capacity inference, full-city map
matching, or production traffic assignment.

Official Dynamic Congestion Validation Smoke Phase 1 adds
`_official_congestion_validation.py`, which consumes the same Seattle SDOT
official count-to-centerline observed target, runs the existing dynamic
congestion moving-agent model on the official Seattle Streets `GeoNetwork`,
aggregates per-tick `edge_loads` over the observed edge subset, and evaluates
the result with `network_edge_metrics` / `network_edge_loss`. The gate compares
one versus two agents per observed edge and passes only when coverage is
complete and the validation loss changes. The report also emits JSON-ready
per-edge diagnostics with official street/objectid metadata and residuals, so
reviewers can inspect the observed-vs-simulated gap without trusting a scalar
loss alone. This proves dynamic congestion output can be checked against an
official observed edge target; it is not traffic-flow validity, congestion
calibration, capacity inference, full-city map matching, or production traffic
assignment.

Official Dynamic Congestion Repro Pack Phase 1 adds
`_official_congestion_repro.py` and a small manifest under
`data/fixtures/official-traffic-counts/`. The pack fixes dynamic validation
parameters, points at the existing Seattle centerline match manifest, reruns
low/high `agents_per_edge` comparisons, checks expected coverage/totals/loss
delta/worst-edge metadata, and preserves the per-edge residual diagnostics for
review. This improves reproducibility and auditability of the official dynamic
congestion smoke; it is still not traffic-flow validity, congestion
calibration, capacity inference, full-city map matching, or production traffic
assignment.

Evacuation Calibration Diagnostics Phase 1 hardens the Anshuka evacuation
outcome calibration adapter: `diagnose_evac_calibration` runs the existing base
ABC bridge, replays the best parameters, and reports `[evac, incap]` residuals,
MAE, RMSE, relative RMSE, max absolute error, and a tolerance flag.
`evac_calibration_diagnostic_gate` passes only when synthetic truth recovers
`belief` and the best-fit residual is within tolerance. This is calibration
instrumentation and identifiability evidence only: no locked Anshuka verdict
change, no P5 prior-experience mechanism, no real traffic-flow or evacuation
validity claim, and no `abm_auto/calibration/` edit.

Anshuka P5 Prior-Experience Gate Phase 1 adds the missing social-uptake knob
as default-off mechanism evidence: `prior_experience_frac=None` preserves the
locked historical behavior, while explicit values in `[0, 1]` assign agents a
prior-experience state and require it before social collaboration can make an
uninformed agent act. The gate proves prior-experience gating can reduce
collaboration lift on synthetic truth. It does not change the real-DEM verdict
bundle, does not tune to the paper's figures, and does not prove real evacuation
or traffic-flow validity.

Anshuka P5 Real-DEM Prior Calibration Phase 1 adds
`_anshuka_p5_calibration.py`, which scans `prior_experience_frac` against the
real Ba DEM P5 null target: `|evac(collab on)-evac(collab off)| < 5` across
low/medium/high belief. The selector chooses the least restrictive passing
prior, so it does not collapse to the trivial `0.0` gate when a higher passing
value exists. This is a post-hoc real-data calibration diagnostic only: no
locked prediction rerun, no verdict-bundle rewrite, no all-lever calibration,
and no evacuation-validity claim.

The public projection preserves the original Anshuka H5 falsification in
`verdict-bundle.json`. Later internal P5 diagnostics are deliberately outside
this public package and are not treated as a retroactive pass.

Validation And Calibration Codegen Template Phase 1 adds runnable layer-D
codegen cells. Explicit `raster_spatial_validation` specs render synthetic
matching raster clusters, call `raster_pattern_metrics` and
`raster_spatial_loss`, and verify with `raster_validation_gate`. Explicit
`raster_spatial_calibration` specs render a deterministic row/col grid search,
call `grid_search_raster_calibration` and `raster_spatial_loss`, and verify with
`raster_spatial_calibration_gate`. These templates remain synthetic: no observed
raster file I/O, no Bayesian posterior inference, and no base
`abm_auto/calibration/` changes.

Real-Data Codegen End-to-End Phase 1 upgrades the raster calibration template
when `GISModelSpec.data_path` points at an observed-raster manifest. Generated
code now calls `calibrate_observed_raster_from_manifest(...)` and
`observed_raster_repro_gate(...)`, so `abm-auto gis run spec.json` reaches the
local manifest -> GeoTIFF -> provenance -> calibration -> gate path. The
committed fixture remains a tiny local raster, not official GHSL/WorldPop data;
the evidence is that codegen can drive real/local file I/O through the same
manifest contract a real clipped raster would use.

Coupled Flood Codegen Template Phase 1 adds the first runnable coupled codegen
cell: explicit `flood_evacuation` specs render a synthetic `GeoNetwork` plus
`RasterSpace`, call `run_flood_evacuation`, and verify with `flood_gate`. This
is static raster-network codegen only; temporal, dynamic, social-spatial,
point-network, polygon-point, validation, and calibration templates were left to
their own template phases.

Social-Spatial Codegen Template Phase 1 adds the first runnable social-network
plus spatial-neighbor codegen cell: explicit `social_spatial_contagion` specs
render a deterministic `grid_neighbors` function plus a synthetic NetworkX
social graph, call `run_contagion`, and verify with `social_lift_gate`. This is
synthetic social-spatial contagion evidence only; it does not validate real
social network structure or observed social diffusion.

Space Zoo Codegen Template Phase 1 adds runnable point-network and polygon-point
codegen cells. Explicit `point_network_risk` specs render a synthetic
`PointSpace` plus `GeoNetwork`, call `point_risk_per_edge` and `risk_exposure`,
and verify with `point_network_risk_gate`. Explicit
`polygon_point_zoning` specs render a synthetic `PointSpace` plus
`PolygonSpace`, call `assign_points_to_polygons`, and verify with
`polygon_point_zoning_gate`. These are synthetic space-zoo evidence only; they
do not validate real hazard exposure, traffic, zoning, or observed point
patterns.

Temporal Flood Codegen Template Phase 1 adds the first runnable temporal codegen
cell: explicit `temporal_flood_evacuation` specs render a synthetic
`RasterTimeline` plus `GeoNetwork`, call `run_temporal_flood_evacuation`, and
verify with `temporal_flood_gate`. This proves codegen can emit a temporal layer
adapter. It still does not generate moving-agent rerouting or traffic-flow
logic.

Dynamic Flood Codegen Template Phase 1 adds the first runnable moving-agent
dynamic codegen cell: explicit `dynamic_flood_evacuation` specs render a
synthetic `RasterTimeline` plus `GeoNetwork`, call
`run_dynamic_flood_evacuation`, and verify with
`dynamic_flood_reroute_gate`. This is synthetic moving-agent rerouting evidence
only; it does not prove real traffic flow, congestion, or emergency evacuation
optimality.

GIS Self-Extension Gap/Halt Phase 1 adds a deterministic codegen preflight:
renderable specs report `action="render"`, while registered-but-nonrenderable,
unknown, and invalid requests report `action="halt"` with structured reasons.
This is the honest fallback surface only; it does not scaffold or generate new
capabilities.

GIS Self-Extension Scaffold Phase 1 adds the next bounded control surface:
registered-but-nonrenderable gaps can now produce a structured
`action="scaffold"` report with capability metadata, expected files, test
targets, and `required_human_review=True`. It still does not generate source
code. `gis_self_extension_scaffold_gate` verifies registered gaps scaffold,
renderable specs stay renderable, and unknown requests halt.

After the mechanism contagion template, all previously registered GIS codegen
capabilities were renderable. Spatial Method Transfer Runtime Cell Phase 1 now
keeps `spatial_method_transfer` as a registered nonrenderable codegen-template
gap: its runtime/gate cell exists, but no runnable template exists yet. The
scaffold surface therefore has a real current gap again, while
`mechanism_contagion` still reports `action="render"` and scaffold refuses it as
already renderable.

Spatial Method Transfer Runtime Cell Phase 1 adds `_spatial_method_transfer.py`,
a small Forman-style edge-curvature proof over existing neighbor adapters. The
same method runs over a 1x4 `RasterSpace` rook-neighbor chain and a four-node
`GeoNetwork` chain, producing the same curvature signature `[0.0, 1.0, 1.0]`.
This closes the runtime/gate side of ADR-019 layer E while keeping
`spatial_method_transfer` nonrenderable in codegen. It is not full Ollivier-
Ricci curvature, not TDA, not spatial validation, and not automatic scientific
method discovery.

Terrain Codegen Registry Gaps Phase 1 records terrain runtime/gate cells in the
capability truth-table. Terrain Network Cost Codegen Phase 1 turns
`terrain_network_cost` into a runnable synthetic template: it builds a mixed
flat/uphill `GeoNetwork`, writes a temporary ASCII heightfield manifest, calls
`terrain_cost_per_edge`, and verifies with `terrain_network_coupling_gate`.
Terrain-Aware Routing Codegen Phase 1 turns `terrain_aware_routing` into a
runnable synthetic template: it builds a two-route `GeoNetwork`, writes a
temporary ASCII heightfield manifest, calls `terrain_aware_shortest_path`, and
verifies with `terrain_aware_routing_gate`. These are synthetic codegen coverage
for edge-cost and route-choice evidence only, not traffic flow, vehicle
dynamics, 3D terrain physics, or real terrain data validation.

Dynamic Congestion Routing Phase 1 adds the second moving-agent lifecycle
mechanism. Unlike dynamic flood, it does not read a raster layer. It updates
network edge costs from previous tick edge loads, replans only at nodes, moves
agents one edge per tick, and verifies rerouting with
`dynamic_congestion_reroute_gate`. This is lifecycle evidence only; it does not
claim traffic-flow realism, capacity modeling, or congestion calibration.

Dynamic Congestion Codegen Template Phase 1 adds runnable codegen coverage for
that second dynamic lifecycle cell. Explicit `dynamic_congestion_routing` specs
render a synthetic `GeoNetwork`, call `run_dynamic_congestion_routing`, and
verify with `dynamic_congestion_reroute_gate`. This is synthetic codegen
coverage only; it does not claim traffic-flow validity, capacity modeling, real
road-data calibration, or optimal routing.

Dynamic Incident Routing Phase 1 adds the third moving-agent lifecycle
mechanism. It updates road-edge availability from per-tick incident closure and
reopen events, replans only at nodes, moves agents along edges, and verifies
rerouting with `dynamic_incident_reroute_gate`. This is synthetic lifecycle
evidence only; it does not claim real traffic-flow validity, optimal incident
management, or real incident-data calibration.

## Next (per ADR-019 sequence)

Space zoo point/polygon spaces are completed, time-varying flood Phase 1 has the
first temporal layer cell, dynamic flood evacuation Phase 2 has moving agents
plus flood-aware node rerouting, and dynamic congestion routing now provides the
second dynamic lifecycle mechanism without flood rasters. Dynamic incident
routing now provides the third dynamic lifecycle mechanism with road closure
events, and dynamic incident codegen now adds runnable synthetic template
coverage for that third dynamic lifecycle cell. The codegen registry now records
runtime-only mechanism-library cells, and codegen now has runnable static flood,
social-spatial, point-network, polygon-point, temporal flood, dynamic flood,
dynamic congestion, and dynamic incident templates plus runnable raster spatial
validation/calibration templates and both mechanism-library templates. Raster
spatial validation covers the first layer-D metric/gate cell, and GIS spatial
calibration now covers the first deterministic objective adapter over that loss.
Self-extension has deterministic gap/halt and scaffold reporting, and the
registered nonrenderable `spatial_method_transfer` gap is now explicitly a
codegen-template gap rather than a runtime-missing gap. Terrain-network cost and
terrain-aware routing are now runnable synthetic codegen templates. The dynamic
routing lifecycle helper implementation is complete and remains bounded to
private moving-route mechanics. See `ADR-019-SYNTHESIS.md` for the current
architecture summary and next-work decision points. Next candidates: create a
new locked P5 rerun only if the private addendum should become a formal
reproduction update, add a new real-data validation bridge beyond the current
observed-raster and traffic-count packs, turn `spatial_method_transfer` into a
runnable codegen template, or add real terrain-data ingestion/validation around
the terrain bridge. `CoupledModel` extraction still waits for concrete shared
lifecycle API pressure such as layer registration, CRS negotiation, per-tick
update order, route invalidation, agent lifecycle hooks, or common temporal
metrics.
