import pytest

from abm_auto.gis._capabilities import (
    get_capability,
    renderable_capabilities,
    resolve_capability,
)


def test_legacy_raster_and_network_specs_resolve_to_capabilities():
    raster = resolve_capability("raster", "sir")
    network = resolve_capability("network", "routing_load")

    assert raster.key == "raster_sir"
    assert network.key == "network_routing_load"


def test_flood_evacuation_is_first_renderable_coupled_capability():
    capability = get_capability("flood_evacuation")

    assert capability.renderable is True
    assert capability.layers == ("GeoNetwork", "RasterSpace")
    assert "run_flood_evacuation" in capability.required_tokens
    assert "flood_gate" in capability.required_tokens


def test_social_spatial_contagion_is_renderable_capability():
    capability = get_capability("social_spatial_contagion")

    assert capability.renderable is True
    assert capability.coupling == "spatial_social"
    assert "networkx" in capability.required_tokens
    assert "combined_neighbors" in capability.required_tokens
    assert "run_contagion" in capability.required_tokens
    assert "social_lift_gate" in capability.required_tokens


def test_point_network_risk_is_renderable_space_zoo_capability():
    capability = get_capability("point_network_risk")

    assert capability.renderable is True
    assert capability.coupling == "point_network"
    assert "PointSpace" in capability.required_tokens
    assert "GeoNetwork" in capability.required_tokens
    assert "point_risk_per_edge" in capability.required_tokens
    assert "risk_exposure" in capability.required_tokens
    assert "point_network_risk_gate" in capability.required_tokens


def test_polygon_point_zoning_is_renderable_space_zoo_capability():
    capability = get_capability("polygon_point_zoning")

    assert capability.renderable is True
    assert capability.coupling == "polygon_point"
    assert "PointSpace" in capability.required_tokens
    assert "PolygonSpace" in capability.required_tokens
    assert "assign_points_to_polygons" in capability.required_tokens
    assert "polygon_point_zoning_gate" in capability.required_tokens


def test_raster_spatial_validation_is_renderable_layer_d_capability():
    capability = get_capability("raster_spatial_validation")

    assert capability.renderable is True
    assert capability.spatial_type == "validation"
    assert "raster_pattern_metrics" in capability.required_tokens
    assert "raster_spatial_loss" in capability.required_tokens
    assert "raster_validation_gate" in capability.required_tokens


def test_raster_spatial_calibration_is_renderable_layer_d_capability():
    capability = get_capability("raster_spatial_calibration")

    assert capability.renderable is True
    assert capability.spatial_type == "calibration"
    assert "grid_search_raster_calibration" in capability.required_tokens
    assert "raster_spatial_loss" in capability.required_tokens
    assert "raster_spatial_calibration_gate" in capability.required_tokens


def test_temporal_flood_evacuation_is_renderable_temporal_capability():
    capability = get_capability("temporal_flood_evacuation")

    assert capability.renderable is True
    assert capability.temporal is True
    assert capability.dynamic is False
    assert capability.layers == ("RasterTimeline", "GeoNetwork")
    assert "RasterTimeline" in capability.required_tokens
    assert "run_temporal_flood_evacuation" in capability.required_tokens
    assert "temporal_flood_gate" in capability.required_tokens


def test_dynamic_flood_evacuation_is_renderable_dynamic_capability():
    capability = get_capability("dynamic_flood_evacuation")

    assert capability.renderable is True
    assert capability.temporal is True
    assert capability.dynamic is True
    assert "RasterTimeline" in capability.required_tokens
    assert "run_dynamic_flood_evacuation" in capability.required_tokens
    assert "dynamic_flood_reroute_gate" in capability.required_tokens


def test_dynamic_congestion_routing_is_renderable_dynamic_capability():
    capability = get_capability("dynamic_congestion_routing")

    assert capability.renderable is True
    assert capability.spatial_type == "network"
    assert capability.mechanism == "dynamic_congestion_routing"
    assert capability.temporal is False
    assert capability.dynamic is True
    assert capability.coupling == "dynamic_network_congestion"
    assert capability.layers == ("GeoNetwork", "moving agents", "per-tick edge loads")
    assert "GeoNetwork" in capability.required_tokens
    assert "run_dynamic_congestion_routing" in capability.required_tokens
    assert "dynamic_congestion_reroute_gate" in capability.required_tokens
    assert capability.gate == "dynamic_congestion_reroute_gate"


def test_mechanism_contagion_is_renderable_capability():
    capability = get_capability("mechanism_contagion")

    assert capability.spatial_type == "mechanism"
    assert capability.renderable is True
    assert "run_contagion" in capability.required_tokens
    assert "mechanism_contagion_gate" in capability.required_tokens
    assert capability.gate == "mechanism_contagion_gate"


def test_mechanism_threshold_adoption_is_renderable_capability():
    capability = get_capability("mechanism_threshold_adoption")

    assert capability.spatial_type == "mechanism"
    assert capability.renderable is True
    assert "run_threshold_adoption" in capability.required_tokens
    assert "mechanism_space_gate" in capability.required_tokens
    assert capability.gate == "mechanism_space_gate"


def test_mechanism_contagion_capability_resolves_explicitly():
    capability = resolve_capability(
        "mechanism",
        "contagion",
        "mechanism_contagion",
    )

    assert capability.key == "mechanism_contagion"


def test_mechanism_contagion_spec_resolves_implicitly():
    capability = resolve_capability("mechanism", "contagion")

    assert capability.key == "mechanism_contagion"


def test_renderable_capability_list_only_contains_codegen_supported_cells():
    assert {cap.key for cap in renderable_capabilities()} == {
        "raster_sir",
        "network_routing_load",
        "flood_evacuation",
        "social_spatial_contagion",
        "point_network_risk",
        "polygon_point_zoning",
        "raster_spatial_validation",
        "raster_spatial_calibration",
        "mechanism_contagion",
        "mechanism_threshold_adoption",
        "temporal_flood_evacuation",
        "dynamic_flood_evacuation",
        "dynamic_congestion_routing",
        # NetLogo gis-extension parity (Phase 1 / 2 / 3)
        "topology_clip",
        "raster_focal",
        "raster_coverage",
        # Platform ABM: codegen emits a full GISAgent/GISModel ABM
        "gis_abm_platform",
    }


def test_unknown_capability_fails_deterministically():
    with pytest.raises(ValueError, match="unknown capability"):
        get_capability("missing_cell")


def test_explicit_capability_must_match_spatial_type_and_mechanism():
    with pytest.raises(ValueError, match="does not match"):
        resolve_capability("raster", "sir", "network_routing_load")
