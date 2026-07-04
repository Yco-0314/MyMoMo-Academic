"""GIS codegen capability registry.

This is the deterministic truth-table for what GIS codegen knows about. A
registered capability may exist in the runtime without being renderable by the
template layer yet.
"""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ParamSpec:
    """Declarative contract for one render parameter: name, coercion type
    (int/float/str), default, optional inclusive numeric range, unit, and a
    one-line doc. The single source of truth shared by the extractor prompt (so
    the LLM stops guessing names) and GISModelSpec.validate() (which rejects
    unknown / mistyped / out-of-range params instead of silently substituting a
    default, as the render branches used to)."""

    name: str
    type: type
    default: object
    min: float | None = None
    max: float | None = None
    unit: str = ""
    doc: str = ""


@dataclass(frozen=True)
class GISCapability:
    key: str
    spatial_type: str
    mechanism: str
    layers: tuple[str, ...]
    coupling: str = ""
    temporal: bool = False
    dynamic: bool = False
    renderable: bool = False
    required_tokens: tuple[str, ...] = ()
    gate: str = ""
    wrong_space_tokens: tuple[str, ...] = ()
    params: tuple["ParamSpec", ...] = ()


CAPABILITIES: dict[str, GISCapability] = {
    "raster_sir": GISCapability(
        key="raster_sir",
        spatial_type="raster",
        mechanism="sir",
        layers=("RasterSpace",),
        renderable=True,
        required_tokens=("RasterSpace", "run_raster_sir", "spatial_spread_gate"),
        gate="spatial_spread_gate",
        wrong_space_tokens=("GeoNetwork",),
    ),
    "network_routing_load": GISCapability(
        key="network_routing_load",
        spatial_type="network",
        mechanism="routing_load",
        layers=("GeoNetwork",),
        renderable=True,
        required_tokens=("GeoNetwork", "run_road_model", "geo_network_gate"),
        gate="geo_network_gate",
        wrong_space_tokens=("RasterSpace",),
    ),
    "flood_evacuation": GISCapability(
        key="flood_evacuation",
        spatial_type="network",
        mechanism="flood_evacuation",
        layers=("GeoNetwork", "RasterSpace"),
        coupling="raster_network_flood",
        renderable=True,
        required_tokens=(
            "GeoNetwork",
            "RasterSpace",
            "run_flood_evacuation",
            "flood_gate",
        ),
        gate="flood_gate",
    ),
    "social_spatial_contagion": GISCapability(
        key="social_spatial_contagion",
        spatial_type="coupled",
        mechanism="social_spatial_contagion",
        layers=("GIS spatial layer", "Network"),
        coupling="spatial_social",
        renderable=True,
        required_tokens=(
            "networkx",
            "combined_neighbors",
            "run_contagion",
            "social_lift_gate",
        ),
        gate="social_lift_gate",
    ),
    "point_network_risk": GISCapability(
        key="point_network_risk",
        spatial_type="point",
        mechanism="point_network_risk",
        layers=("PointSpace", "GeoNetwork"),
        coupling="point_network",
        renderable=True,
        required_tokens=(
            "PointSpace",
            "GeoNetwork",
            "point_risk_per_edge",
            "risk_exposure",
            "point_network_risk_gate",
        ),
        gate="point_network_risk_gate",
    ),
    "polygon_point_zoning": GISCapability(
        key="polygon_point_zoning",
        spatial_type="polygon",
        mechanism="polygon_point_zoning",
        layers=("PolygonSpace", "PointSpace"),
        coupling="polygon_point",
        renderable=True,
        required_tokens=(
            "PointSpace",
            "PolygonSpace",
            "assign_points_to_polygons",
            "polygon_point_zoning_gate",
        ),
        gate="polygon_point_zoning_gate",
    ),
    "temporal_flood_evacuation": GISCapability(
        key="temporal_flood_evacuation",
        spatial_type="temporal",
        mechanism="temporal_flood_evacuation",
        layers=("RasterTimeline", "GeoNetwork"),
        coupling="temporal_raster_network_flood",
        temporal=True,
        renderable=True,
        required_tokens=(
            "RasterTimeline",
            "RasterSpace",
            "GeoNetwork",
            "run_temporal_flood_evacuation",
            "temporal_flood_gate",
        ),
        gate="temporal_flood_gate",
    ),
    "dynamic_flood_evacuation": GISCapability(
        key="dynamic_flood_evacuation",
        spatial_type="network",
        mechanism="dynamic_flood_evacuation",
        layers=("RasterTimeline", "GeoNetwork", "moving agents"),
        coupling="dynamic_raster_network_flood",
        temporal=True,
        dynamic=True,
        renderable=True,
        required_tokens=(
            "RasterTimeline",
            "RasterSpace",
            "GeoNetwork",
            "run_dynamic_flood_evacuation",
            "dynamic_flood_reroute_gate",
        ),
        gate="dynamic_flood_reroute_gate",
    ),
    "dynamic_congestion_routing": GISCapability(
        key="dynamic_congestion_routing",
        spatial_type="network",
        mechanism="dynamic_congestion_routing",
        layers=("GeoNetwork", "moving agents", "per-tick edge loads"),
        coupling="dynamic_network_congestion",
        dynamic=True,
        renderable=True,
        required_tokens=(
            "GeoNetwork",
            "run_dynamic_congestion_routing",
            "dynamic_congestion_reroute_gate",
        ),
        gate="dynamic_congestion_reroute_gate",
    ),
    "dynamic_incident_routing": GISCapability(
        key="dynamic_incident_routing",
        spatial_type="network",
        mechanism="dynamic_incident_routing",
        layers=("GeoNetwork", "moving agents", "per-tick incident events"),
        coupling="dynamic_network_incident",
        dynamic=True,
        renderable=True,
        required_tokens=(
            "GeoNetwork",
            "LineString",
            "run_dynamic_incident_routing",
            "dynamic_incident_reroute_gate",
        ),
        gate="dynamic_incident_reroute_gate",
    ),
    "raster_spatial_validation": GISCapability(
        key="raster_spatial_validation",
        spatial_type="validation",
        mechanism="raster_spatial_validation",
        layers=("raster pattern", "observed raster"),
        renderable=True,
        required_tokens=(
            "raster_pattern_metrics",
            "raster_spatial_loss",
            "raster_validation_gate",
        ),
        gate="raster_validation_gate",
    ),
    "raster_spatial_calibration": GISCapability(
        key="raster_spatial_calibration",
        spatial_type="calibration",
        mechanism="raster_spatial_calibration",
        layers=("raster simulator", "observed raster", "parameter grid"),
        renderable=True,
        required_tokens=(
            "grid_search_raster_calibration",
            "raster_spatial_loss",
            "raster_spatial_calibration_gate",
        ),
        gate="raster_spatial_calibration_gate",
    ),
    "mechanism_contagion": GISCapability(
        key="mechanism_contagion",
        spatial_type="mechanism",
        mechanism="contagion",
        layers=("neighbors_of",),
        renderable=True,
        required_tokens=("run_contagion", "mechanism_contagion_gate"),
        gate="mechanism_contagion_gate",
    ),
    "mechanism_threshold_adoption": GISCapability(
        key="mechanism_threshold_adoption",
        spatial_type="mechanism",
        mechanism="threshold_adoption",
        layers=("neighbors_of",),
        renderable=True,
        required_tokens=("run_threshold_adoption", "mechanism_space_gate"),
        gate="mechanism_space_gate",
    ),
    # ── NetLogo gis-extension parity (Phase 1 / 2 / 3 wired into codegen) ────
    "topology_clip": GISCapability(
        key="topology_clip",
        spatial_type="topology",
        mechanism="line_polygon_clip",
        layers=("LineLayer", "Polygon"),
        coupling="line_polygon",
        renderable=True,
        required_tokens=("lines_in_polygon", "line_polygon_gate", "LineString",
                         "box"),
        gate="line_polygon_gate",
        wrong_space_tokens=("RasterSpace", "GeoNetwork"),
    ),
    "raster_focal": GISCapability(
        key="raster_focal",
        spatial_type="raster",
        mechanism="focal_smoothing",
        layers=("RasterField",),
        renderable=True,
        required_tokens=("RasterField", "convolve", "focal_gate"),
        gate="focal_gate",
        wrong_space_tokens=("GeoNetwork",),
    ),
    "raster_coverage": GISCapability(
        key="raster_coverage",
        spatial_type="raster",
        mechanism="areal_coverage",
        layers=("Polygon", "RasterField"),
        coupling="polygon_raster",
        renderable=True,
        required_tokens=("RasterField", "apply_coverage", "apply_coverage_gate",
                         "box"),
        gate="apply_coverage_gate",
        wrong_space_tokens=("GeoNetwork",),
    ),
    # ── Platform ABM (ADR-020): codegen emits a full GISAgent/GISModel ABM ──
    "gis_abm_platform": GISCapability(
        key="gis_abm_platform",
        spatial_type="platform",
        mechanism="diffusion",
        layers=("GISAgent", "GISModel"),
        renderable=True,
        required_tokens=("GISAgent", "GISModel", "DataCollector", "step"),
        gate="(inline)",
    ),
    # ── Terrain bridge consumers: runtime/gate exists, no codegen template yet ──
    "terrain_network_cost": GISCapability(
        key="terrain_network_cost",
        spatial_type="terrain",
        mechanism="terrain_network_cost",
        layers=("terrain bridge heightfield", "GeoNetwork"),
        coupling="terrain_network",
        renderable=True,
        required_tokens=(
            "GeoNetwork",
            "LineString",
            "terrain_cost_per_edge",
            "terrain_network_coupling_gate",
        ),
        gate="terrain_network_coupling_gate",
    ),
    "terrain_aware_routing": GISCapability(
        key="terrain_aware_routing",
        spatial_type="terrain",
        mechanism="terrain_aware_routing",
        layers=("terrain bridge heightfield", "GeoNetwork"),
        coupling="terrain_network_routing",
        renderable=True,
        required_tokens=(
            "GeoNetwork",
            "LineString",
            "terrain_aware_shortest_path",
            "terrain_aware_routing_gate",
        ),
        gate="terrain_aware_routing_gate",
    ),
    # ── ADR-019 layer E: method-transfer on the model's intermediate spatial
    #    state (TDA / Ricci curvature / hot-spot). The runtime/gate cell exists,
    #    but no runnable codegen template exists yet, so it remains REGISTERED
    #    but NOT renderable. This keeps the self-extension loop's gap/scaffold
    #    path real rather than vacuous: the platform DETECTS it deterministically
    #    and HALTS to a human (auto-fill is generate-then-verify, never
    #    generate-then-trust).
    "spatial_method_transfer": GISCapability(
        key="spatial_method_transfer",
        spatial_type="method_transfer",
        mechanism="ricci_curvature",
        layers=("RasterSpace",),
        renderable=False,
        required_tokens=("ricci_curvature", "spatial_method_transfer_gate"),
        gate="spatial_method_transfer_gate",
    ),
}

# ── Declarative parameter contracts ──────────────────────────────────────────
# The single source of truth for each renderable capability's render params,
# shared by the extractor prompt and GISModelSpec.validate(). Attached to each
# capability's `params` below so the contract lives on the capability. Ranges are
# set only where semantically meaningful (probabilities 0..1, counts >= 1); other
# numerics stay unbounded. `seed` is a spec-level field, not listed here.
def _p(name, type_, default, lo=None, hi=None, unit="", doc=""):
    return ParamSpec(name, type_, default, lo, hi, unit, doc)


_PARAM_SCHEMAS: dict[str, tuple[ParamSpec, ...]] = {
    "raster_sir": (_p("steps", int, 60, 1, None, "ticks", "number of simulation steps"),),
    "flood_evacuation": (
        _p("threshold", float, 1.0, 0.0, None, "depth", "flood depth above which an edge is impassable"),
    ),
    "social_spatial_contagion": (
        _p("n_agents", int, 100, 1, None, "agents", "number of agents"),
        _p("side", int, 10, 1, None, "cells", "grid side length"),
        _p("beta", float, 0.2, 0.0, 1.0, "prob", "per-contact contagion probability"),
        _p("steps", int, 6, 1, None, "ticks", "number of simulation steps"),
    ),
    "point_network_risk": (
        _p("radius", float, 10.0, 0.0, None, "m", "distance within which a point counts toward an edge"),
    ),
    "mechanism_threshold_adoption": (
        _p("n_agents", int, 8, 1, None, "agents", "number of agents"),
        _p("threshold", int, 1, 0, None, "neighbors", "adopting-neighbor count that triggers adoption"),
        _p("steps", int, 7, 1, None, "ticks", "number of simulation steps"),
    ),
    "mechanism_contagion": (
        _p("n_agents", int, 8, 1, None, "agents", "number of agents"),
        _p("beta", float, 1.0, 0.0, 1.0, "prob", "per-contact contagion probability"),
        _p("steps", int, 7, 1, None, "ticks", "number of simulation steps"),
    ),
    "temporal_flood_evacuation": (
        _p("threshold", float, 1.0, 0.0, None, "depth", "flood depth above which an edge is impassable"),
    ),
    "dynamic_flood_evacuation": (
        _p("threshold", float, 1.0, 0.0, None, "depth", "flood depth above which an edge is impassable"),
    ),
    "dynamic_congestion_routing": (
        _p("n_steps", int, 8, 1, None, "ticks", "number of routing steps"),
        _p("speed_m_per_tick", float, 100.0, 0.0, None, "m/tick", "agent travel speed per tick"),
        _p("congestion_alpha", float, 3.0, 0.0, None, "", "congestion cost sensitivity"),
    ),
    "dynamic_incident_routing": (
        _p("n_steps", int, 6, 1, None, "ticks", "number of routing steps"),
        _p("speed_m_per_tick", float, 100.0, 0.0, None, "m/tick", "agent travel speed per tick"),
    ),
    "raster_focal": (
        _p("rows", int, 15, 1, None, "cells", "raster row count"),
        _p("cols", int, 15, 1, None, "cells", "raster column count"),
    ),
    "raster_coverage": (
        _p("rows", int, 4, 1, None, "cells", "raster row count"),
        _p("cols", int, 4, 1, None, "cells", "raster column count"),
    ),
    "gis_abm_platform": (_p("n", int, 12, 1, None, "agents", "number of agents"),),
    "terrain_network_cost": (
        _p("grade_weight", float, 1.0, 0.0, None, "", "terrain grade cost sensitivity"),
        _p("n_samples", int, 5, 2, None, "samples", "terrain samples per edge"),
        _p("threshold", float, 0.01, 0.0, None, "", "minimum grade proxy required by the gate"),
    ),
    "terrain_aware_routing": (
        _p("grade_weight", float, 0.25, 0.0, None, "", "terrain grade cost sensitivity"),
        _p("n_samples", int, 5, 2, None, "samples", "terrain samples per edge"),
    ),
    "network_routing_load": (
        _p("crs", str, "EPSG:27700", None, None, "", "coordinate reference system code"),
        _p("n_trips", int, 300, 1, None, "trips", "number of trips to simulate"),
    ),
}

# Attach the param contracts onto the (frozen) capabilities.
CAPABILITIES = {
    key: (replace(cap, params=_PARAM_SCHEMAS[key]) if key in _PARAM_SCHEMAS else cap)
    for key, cap in CAPABILITIES.items()
}


# Implicit legacy specs are codegen-renderable only; runtime-only cells require
# explicit capability keys.
_LEGACY_CAPABILITIES = tuple(cap for cap in CAPABILITIES.values() if cap.renderable)

_LEGACY_BY_SPEC = {
    (cap.spatial_type, cap.mechanism): cap.key
    for cap in _LEGACY_CAPABILITIES
}

SPATIAL_TYPES = tuple(sorted({cap.spatial_type for cap in _LEGACY_CAPABILITIES}))
MECHANISMS = {
    spatial_type: tuple(
        cap.mechanism for cap in _LEGACY_CAPABILITIES
        if cap.spatial_type == spatial_type
    )
    for spatial_type in SPATIAL_TYPES
}


def get_capability(key: str) -> GISCapability:
    try:
        return CAPABILITIES[key]
    except KeyError as exc:
        raise ValueError(f"unknown capability {key!r}") from exc


def resolve_capability(
    spatial_type: str,
    mechanism: str,
    capability: str = "",
) -> GISCapability:
    """Resolve a spec to a registered capability and validate consistency."""
    if capability:
        cap = get_capability(capability)
        if cap.spatial_type != spatial_type or cap.mechanism != mechanism:
            raise ValueError(
                f"capability {capability!r} does not match "
                f"spatial_type={spatial_type!r}, mechanism={mechanism!r}"
            )
        return cap

    if spatial_type not in SPATIAL_TYPES:
        raise ValueError(f"unknown spatial_type {spatial_type!r}; "
                         f"expected one of {SPATIAL_TYPES}")

    key = _LEGACY_BY_SPEC.get((spatial_type, mechanism))
    if key is None:
        allowed = MECHANISMS[spatial_type]
        raise ValueError(f"mechanism {mechanism!r} not valid for "
                         f"{spatial_type!r}; expected {allowed}")
    return CAPABILITIES[key]


def renderable_capabilities() -> tuple[GISCapability, ...]:
    return tuple(cap for cap in CAPABILITIES.values() if cap.renderable)
