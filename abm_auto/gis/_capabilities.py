"""GIS codegen capability registry.

This is the deterministic truth-table for what GIS codegen knows about. A
registered capability may exist in the runtime without being renderable by the
template layer yet.
"""
from __future__ import annotations

from dataclasses import dataclass


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
    # ── Platform ABM: codegen emits a full GISAgent/GISModel ABM ──
    "gis_abm_platform": GISCapability(
        key="gis_abm_platform",
        spatial_type="platform",
        mechanism="diffusion",
        layers=("GISAgent", "GISModel"),
        renderable=True,
        required_tokens=("GISAgent", "GISModel", "DataCollector", "step"),
        gate="(inline)",
    ),
    # ── Method-transfer on the model's intermediate spatial state (TDA / Ricci
    #    curvature / hot-spot). A GENUINE standing gap — the runtime cell does NOT
    #    exist yet, so it is REGISTERED but NOT renderable. The platform DETECTS
    #    this deterministically and HALTS to a human rather than emitting
    #    unverified code (generate-then-verify, never generate-then-trust).
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
