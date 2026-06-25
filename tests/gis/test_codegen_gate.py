from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.gis._templates import render
from abm_auto.gis._codegen_gate import gis_codegen_gate


def test_gate_passes_clean_raster_code():
    spec = GISModelSpec(spatial_type="raster", mechanism="sir")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_network_code():
    spec = GISModelSpec(spatial_type="network", mechanism="routing_load",
                        data_path="/d/roads.shp")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_flood_code():
    spec = GISModelSpec(spatial_type="network", mechanism="flood_evacuation",
                        capability="flood_evacuation")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_social_spatial_code():
    spec = GISModelSpec(spatial_type="coupled",
                        mechanism="social_spatial_contagion",
                        capability="social_spatial_contagion")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_point_network_risk_code():
    spec = GISModelSpec(spatial_type="point",
                        mechanism="point_network_risk",
                        capability="point_network_risk")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_polygon_point_zoning_code():
    spec = GISModelSpec(spatial_type="polygon",
                        mechanism="polygon_point_zoning",
                        capability="polygon_point_zoning")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_raster_spatial_validation_code():
    spec = GISModelSpec(spatial_type="validation",
                        mechanism="raster_spatial_validation",
                        capability="raster_spatial_validation")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_raster_spatial_calibration_code():
    spec = GISModelSpec(spatial_type="calibration",
                        mechanism="raster_spatial_calibration",
                        capability="raster_spatial_calibration")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_mechanism_threshold_adoption_code():
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="threshold_adoption",
                        capability="mechanism_threshold_adoption")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_mechanism_contagion_code():
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="contagion",
                        capability="mechanism_contagion")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_temporal_flood_code():
    spec = GISModelSpec(spatial_type="temporal",
                        mechanism="temporal_flood_evacuation",
                        capability="temporal_flood_evacuation")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_dynamic_flood_code():
    spec = GISModelSpec(spatial_type="network",
                        mechanism="dynamic_flood_evacuation",
                        capability="dynamic_flood_evacuation")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_passes_clean_dynamic_congestion_code():
    spec = GISModelSpec(spatial_type="network",
                        mechanism="dynamic_congestion_routing",
                        capability="dynamic_congestion_routing")
    ok, reasons = gis_codegen_gate(render(spec), spec)
    assert ok, reasons


def test_gate_fails_on_missing_gate_call():
    spec = GISModelSpec(spatial_type="raster", mechanism="sir")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("spatial_spread_gate", "no_gate")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok and any("spatial_spread_gate" in r for r in reasons)


def test_gate_fails_on_wrong_space_class():
    spec = GISModelSpec(spatial_type="raster", mechanism="sir")
    files = render(spec)
    files["main.py"] += "\nfrom abm_auto.gis._geo_network import GeoNetwork\n"
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok and any("GeoNetwork" in r for r in reasons)


def test_gate_fails_on_forbidden_import():
    spec = GISModelSpec(spatial_type="raster", mechanism="sir")
    files = render(spec)
    files["main.py"] = "import Melodie\n" + files["main.py"]
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok and any("Melodie" in r for r in reasons)


def test_gate_uses_registry_required_tokens():
    spec = GISModelSpec(spatial_type="network", mechanism="routing_load",
                        capability="network_routing_load",
                        data_path="/d/roads.shp")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("run_road_model", "run_other_model")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any("network_routing_load model missing required call: run_road_model" in r
               for r in reasons)


def test_gate_uses_registry_required_tokens_for_flood_template():
    spec = GISModelSpec(spatial_type="network", mechanism="flood_evacuation",
                        capability="flood_evacuation")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("run_flood_evacuation", "run_other")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any("flood_evacuation model missing required call: run_flood_evacuation" in r
               for r in reasons)


def test_gate_uses_registry_required_tokens_for_social_spatial_template():
    spec = GISModelSpec(spatial_type="coupled",
                        mechanism="social_spatial_contagion",
                        capability="social_spatial_contagion")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("social_lift_gate", "other_gate")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "social_spatial_contagion model missing required call: social_lift_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_point_network_risk_template():
    spec = GISModelSpec(spatial_type="point",
                        mechanism="point_network_risk",
                        capability="point_network_risk")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("point_network_risk_gate", "other_gate")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "point_network_risk model missing required call: point_network_risk_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_polygon_point_zoning_template():
    spec = GISModelSpec(spatial_type="polygon",
                        mechanism="polygon_point_zoning",
                        capability="polygon_point_zoning")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("polygon_point_zoning_gate", "other_gate")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "polygon_point_zoning model missing required call: polygon_point_zoning_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_raster_spatial_validation_template():
    spec = GISModelSpec(spatial_type="validation",
                        mechanism="raster_spatial_validation",
                        capability="raster_spatial_validation")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("raster_validation_gate", "other_gate")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "raster_spatial_validation model missing required call: raster_validation_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_raster_spatial_calibration_template():
    spec = GISModelSpec(spatial_type="calibration",
                        mechanism="raster_spatial_calibration",
                        capability="raster_spatial_calibration")
    files = render(spec)
    files["main.py"] = files["main.py"].replace(
        "raster_spatial_calibration_gate",
        "other_gate",
    )
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "raster_spatial_calibration model missing required call: raster_spatial_calibration_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_mechanism_threshold_adoption_template():
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="threshold_adoption",
                        capability="mechanism_threshold_adoption")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("mechanism_space_gate", "other_gate")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "mechanism_threshold_adoption model missing required call: mechanism_space_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_mechanism_contagion_template():
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="contagion",
                        capability="mechanism_contagion")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("mechanism_contagion_gate", "other_gate")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "mechanism_contagion model missing required call: mechanism_contagion_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_temporal_flood_template():
    spec = GISModelSpec(spatial_type="temporal",
                        mechanism="temporal_flood_evacuation",
                        capability="temporal_flood_evacuation")
    files = render(spec)
    files["main.py"] = files["main.py"].replace("temporal_flood_gate", "other_gate")
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "temporal_flood_evacuation model missing required call: temporal_flood_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_dynamic_flood_template():
    spec = GISModelSpec(spatial_type="network",
                        mechanism="dynamic_flood_evacuation",
                        capability="dynamic_flood_evacuation")
    files = render(spec)
    files["main.py"] = files["main.py"].replace(
        "dynamic_flood_reroute_gate",
        "other_gate",
    )
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "dynamic_flood_evacuation model missing required call: dynamic_flood_reroute_gate" in r
        for r in reasons
    )


def test_gate_uses_registry_required_tokens_for_dynamic_congestion_template():
    spec = GISModelSpec(spatial_type="network",
                        mechanism="dynamic_congestion_routing",
                        capability="dynamic_congestion_routing")
    files = render(spec)
    files["main.py"] = files["main.py"].replace(
        "dynamic_congestion_reroute_gate",
        "other_gate",
    )
    ok, reasons = gis_codegen_gate(files, spec)
    assert not ok
    assert any(
        "dynamic_congestion_routing model missing required call: dynamic_congestion_reroute_gate" in r
        for r in reasons
    )
