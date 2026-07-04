from unittest.mock import MagicMock

import pytest

from abm_auto.gis._extractor import extract_gis_spec


def _client(reply):
    c = MagicMock()
    c.create.return_value = reply
    return c


def test_extracts_raster_spec():
    c = _client('{"spatial_type": "raster", "mechanism": "sir", "data_path": "", "params": {"steps": 40}}')
    spec = extract_gis_spec("epidemic on density raster", c)
    assert spec.spatial_type == "raster" and spec.mechanism == "sir"
    assert spec.capability == ""
    assert spec.params["steps"] == 40


def test_prompt_lists_renderable_registry_capabilities_only():
    c = _client('{"spatial_type": "raster", "mechanism": "sir", "data_path": "", "params": {}}')

    extract_gis_spec("epidemic on density raster", c)

    prompt = c.create.call_args.kwargs["user"]
    assert "flood_evacuation" in prompt
    assert 'spatial_type="network"' in prompt
    assert 'mechanism="flood_evacuation"' in prompt
    assert "social_spatial_contagion" in prompt
    assert 'spatial_type="coupled"' in prompt
    assert 'mechanism="social_spatial_contagion"' in prompt
    assert "point_network_risk" in prompt
    assert 'spatial_type="point"' in prompt
    assert 'mechanism="point_network_risk"' in prompt
    assert "polygon_point_zoning" in prompt
    assert 'spatial_type="polygon"' in prompt
    assert 'mechanism="polygon_point_zoning"' in prompt
    assert "raster_spatial_validation" in prompt
    assert 'spatial_type="validation"' in prompt
    assert 'mechanism="raster_spatial_validation"' in prompt
    assert "raster_spatial_calibration" in prompt
    assert 'spatial_type="calibration"' in prompt
    assert 'mechanism="raster_spatial_calibration"' in prompt
    assert "mechanism_threshold_adoption" in prompt
    assert 'spatial_type="mechanism"' in prompt
    assert 'mechanism="threshold_adoption"' in prompt
    assert "mechanism_contagion" in prompt
    assert 'mechanism="contagion"' in prompt
    assert "temporal_flood_evacuation" in prompt
    assert 'spatial_type="temporal"' in prompt
    assert 'mechanism="temporal_flood_evacuation"' in prompt
    assert "dynamic_flood_evacuation" in prompt
    assert 'mechanism="dynamic_flood_evacuation"' in prompt
    assert "dynamic_congestion_routing" in prompt
    assert 'mechanism="dynamic_congestion_routing"' in prompt
    assert "dynamic_incident_routing" in prompt
    assert 'mechanism="dynamic_incident_routing"' in prompt
    assert "terrain_network_cost" in prompt
    assert 'mechanism="terrain_network_cost"' in prompt
    assert "terrain_aware_routing" in prompt
    assert 'spatial_type="terrain"' in prompt
    assert 'mechanism="terrain_aware_routing"' in prompt


def test_extracts_network_spec_with_path():
    c = _client('{"spatial_type": "network", "mechanism": "routing_load", "data_path": "/d/roads.shp", "params": {}}')
    spec = extract_gis_spec("traffic on a road network shapefile", c)
    assert spec.spatial_type == "network" and spec.data_path == "/d/roads.shp"


def test_strips_code_fences():
    c = _client('```json\n{"spatial_type": "raster", "mechanism": "sir", "data_path": "", "params": {}}\n```')
    spec = extract_gis_spec("...", c)
    assert spec.spatial_type == "raster"


def test_invalid_extraction_fails_validation():
    # LLM emits a mechanism that doesn't match the spatial type -> rejected at parse
    c = _client('{"spatial_type": "raster", "mechanism": "routing_load", "data_path": "", "params": {}}')
    with pytest.raises(ValueError, match="mechanism"):
        extract_gis_spec("...", c)


def test_extracts_explicit_renderable_capability():
    c = _client('{"capability": "raster_sir", "spatial_type": "raster", "mechanism": "sir", "data_path": "", "params": {}}')
    spec = extract_gis_spec("epidemic on density raster", c)
    assert spec.capability == "raster_sir"


def test_extracts_explicit_flood_renderable_capability():
    c = _client(
        '{"capability": "flood_evacuation", "spatial_type": "network", '
        '"mechanism": "flood_evacuation", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("flood evacuation on a road network", c)
    assert spec.capability == "flood_evacuation"
    assert spec.mechanism == "flood_evacuation"


def test_extracts_explicit_social_spatial_renderable_capability():
    c = _client(
        '{"capability": "social_spatial_contagion", "spatial_type": "coupled", '
        '"mechanism": "social_spatial_contagion", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("social ties plus spatial contagion", c)
    assert spec.capability == "social_spatial_contagion"
    assert spec.mechanism == "social_spatial_contagion"


def test_extracts_explicit_point_network_risk_renderable_capability():
    c = _client(
        '{"capability": "point_network_risk", "spatial_type": "point", '
        '"mechanism": "point_network_risk", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("risk points near roads", c)
    assert spec.capability == "point_network_risk"
    assert spec.mechanism == "point_network_risk"


def test_extracts_explicit_polygon_point_zoning_renderable_capability():
    c = _client(
        '{"capability": "polygon_point_zoning", "spatial_type": "polygon", '
        '"mechanism": "polygon_point_zoning", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("assign points to zones", c)
    assert spec.capability == "polygon_point_zoning"
    assert spec.mechanism == "polygon_point_zoning"


def test_extracts_explicit_raster_spatial_validation_renderable_capability():
    c = _client(
        '{"capability": "raster_spatial_validation", "spatial_type": "validation", '
        '"mechanism": "raster_spatial_validation", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("validate raster pattern against observed raster", c)
    assert spec.capability == "raster_spatial_validation"
    assert spec.mechanism == "raster_spatial_validation"


def test_extracts_explicit_raster_spatial_calibration_renderable_capability():
    c = _client(
        '{"capability": "raster_spatial_calibration", "spatial_type": "calibration", '
        '"mechanism": "raster_spatial_calibration", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("calibrate raster simulation to spatial loss", c)
    assert spec.capability == "raster_spatial_calibration"
    assert spec.mechanism == "raster_spatial_calibration"


def test_extracts_explicit_mechanism_threshold_adoption_renderable_capability():
    c = _client(
        '{"capability": "mechanism_threshold_adoption", "spatial_type": "mechanism", '
        '"mechanism": "threshold_adoption", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("threshold adoption over neighbors", c)
    assert spec.capability == "mechanism_threshold_adoption"
    assert spec.mechanism == "threshold_adoption"


def test_extracts_explicit_temporal_flood_renderable_capability():
    c = _client(
        '{"capability": "temporal_flood_evacuation", "spatial_type": "temporal", '
        '"mechanism": "temporal_flood_evacuation", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("time varying flood evacuation", c)
    assert spec.capability == "temporal_flood_evacuation"
    assert spec.mechanism == "temporal_flood_evacuation"


def test_extracts_explicit_dynamic_flood_renderable_capability():
    c = _client(
        '{"capability": "dynamic_flood_evacuation", "spatial_type": "network", '
        '"mechanism": "dynamic_flood_evacuation", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("dynamic flood evacuation on roads", c)
    assert spec.capability == "dynamic_flood_evacuation"
    assert spec.mechanism == "dynamic_flood_evacuation"


def test_extracts_explicit_dynamic_congestion_renderable_capability():
    c = _client(
        '{"capability": "dynamic_congestion_routing", "spatial_type": "network", '
        '"mechanism": "dynamic_congestion_routing", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("dynamic congestion rerouting on roads", c)
    assert spec.capability == "dynamic_congestion_routing"
    assert spec.mechanism == "dynamic_congestion_routing"


def test_extracts_explicit_dynamic_incident_renderable_capability():
    c = _client(
        '{"capability": "dynamic_incident_routing", "spatial_type": "network", '
        '"mechanism": "dynamic_incident_routing", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("dynamic incident rerouting on roads", c)
    assert spec.capability == "dynamic_incident_routing"
    assert spec.mechanism == "dynamic_incident_routing"


def test_extracts_explicit_mechanism_contagion_renderable_capability():
    c = _client(
        '{"capability": "mechanism_contagion", "spatial_type": "mechanism", '
        '"mechanism": "contagion", "data_path": "", "params": {}}'
    )
    spec = extract_gis_spec("contagion over neighbors", c)
    assert spec.capability == "mechanism_contagion"
    assert spec.mechanism == "contagion"


def test_extracts_explicit_terrain_aware_routing_renderable_capability():
    c = _client(
        '{"capability": "terrain_aware_routing", "spatial_type": "terrain", '
        '"mechanism": "terrain_aware_routing", "data_path": "", '
        '"params": {"grade_weight": 0.25, "n_samples": 5}}'
    )

    spec = extract_gis_spec("terrain-aware routing over a synthetic road network", c)

    assert spec.capability == "terrain_aware_routing"
    assert spec.mechanism == "terrain_aware_routing"
    assert spec.params["grade_weight"] == 0.25
    assert spec.params["n_samples"] == 5


def test_extracts_explicit_terrain_network_cost_renderable_capability():
    c = _client(
        '{"capability": "terrain_network_cost", "spatial_type": "terrain", '
        '"mechanism": "terrain_network_cost", "data_path": "", '
        '"params": {"grade_weight": 1.0, "n_samples": 5, "threshold": 0.01}}'
    )

    spec = extract_gis_spec("terrain-derived edge costs on a road network", c)

    assert spec.capability == "terrain_network_cost"
    assert spec.mechanism == "terrain_network_cost"
    assert spec.params["grade_weight"] == 1.0
    assert spec.params["n_samples"] == 5
    assert spec.params["threshold"] == 0.01
