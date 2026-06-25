import os
import subprocess
import sys
from pathlib import Path

import pytest

from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.gis._templates import render

_REPO_ROOT = str(Path(__file__).resolve().parents[2])


# ── B1: spec validation ─────────────────────────────────────────────────────

def test_spec_rejects_unknown_spatial_type():
    with pytest.raises(ValueError, match="spatial_type"):
        GISModelSpec(spatial_type="hyperbolic", mechanism="sir").validate()


def test_spec_rejects_mechanism_mismatch():
    with pytest.raises(ValueError, match="mechanism"):
        GISModelSpec(spatial_type="raster", mechanism="routing_load").validate()


def test_spec_rejects_unknown_capability():
    with pytest.raises(ValueError, match="unknown capability"):
        GISModelSpec(spatial_type="raster", mechanism="sir",
                     capability="missing_cell").validate()


def test_spec_rejects_capability_mismatch():
    with pytest.raises(ValueError, match="does not match"):
        GISModelSpec(spatial_type="raster", mechanism="sir",
                     capability="network_routing_load").validate()


def test_network_requires_data_path():
    with pytest.raises(ValueError, match="data_path"):
        GISModelSpec(spatial_type="network", mechanism="routing_load").validate()


def test_explicit_flood_evacuation_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="network",
        mechanism="flood_evacuation",
        capability="flood_evacuation",
    ).validate()


def test_explicit_social_spatial_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="coupled",
        mechanism="social_spatial_contagion",
        capability="social_spatial_contagion",
    ).validate()


def test_explicit_point_network_risk_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="point",
        mechanism="point_network_risk",
        capability="point_network_risk",
    ).validate()


def test_explicit_polygon_point_zoning_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="polygon",
        mechanism="polygon_point_zoning",
        capability="polygon_point_zoning",
    ).validate()


def test_explicit_raster_spatial_validation_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="validation",
        mechanism="raster_spatial_validation",
        capability="raster_spatial_validation",
    ).validate()


def test_explicit_raster_spatial_calibration_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="calibration",
        mechanism="raster_spatial_calibration",
        capability="raster_spatial_calibration",
    ).validate()


def test_explicit_mechanism_threshold_adoption_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="mechanism",
        mechanism="threshold_adoption",
        capability="mechanism_threshold_adoption",
    ).validate()


def test_explicit_mechanism_contagion_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="mechanism",
        mechanism="contagion",
        capability="mechanism_contagion",
    ).validate()


def test_explicit_temporal_flood_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="temporal",
        mechanism="temporal_flood_evacuation",
        capability="temporal_flood_evacuation",
    ).validate()


def test_explicit_dynamic_flood_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="network",
        mechanism="dynamic_flood_evacuation",
        capability="dynamic_flood_evacuation",
    ).validate()


def test_explicit_dynamic_congestion_spec_validates_without_data_path():
    GISModelSpec(
        spatial_type="network",
        mechanism="dynamic_congestion_routing",
        capability="dynamic_congestion_routing",
    ).validate()


def test_spec_roundtrip():
    s = GISModelSpec(spatial_type="raster", mechanism="sir",
                     capability="raster_sir", seed=3, params={"steps": 40})
    rt = GISModelSpec.from_dict(s.to_dict())
    assert rt.params["steps"] == 40
    assert rt.capability == "raster_sir"


# ── B2: render -> runnable code -> passes the science gate ───────────────────

def test_render_raster_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="raster", mechanism="sir", seed=1, params={"steps": 60})
    files = render(spec)
    assert "main.py" in files
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    # generate -> execute the model -> the spatial-spread gate must PASS
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout


def test_render_network_emits_valid_structure():
    spec = GISModelSpec(spatial_type="network", mechanism="routing_load",
                        data_path="/data/roads.shp", params={"crs": "EPSG:27700"})
    code = render(spec)["main.py"]
    assert "GeoNetwork" in code and "geo_network_gate" in code
    assert "/data/roads.shp" in code
    # imports only from abm_auto.gis (+ geopandas/networkx), never from Melodie etc.
    assert "from abm_auto.gis" in code and "import Melodie" not in code


def test_render_flood_evacuation_emits_coupled_structure():
    spec = GISModelSpec(spatial_type="network", mechanism="flood_evacuation",
                        capability="flood_evacuation")
    code = render(spec)["main.py"]
    assert "GeoNetwork" in code
    assert "RasterSpace" in code
    assert "run_flood_evacuation" in code
    assert "flood_gate" in code
    assert "run_dynamic_flood_evacuation" not in code
    assert "RasterTimeline" not in code


def test_render_flood_evacuation_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="network", mechanism="flood_evacuation",
                        capability="flood_evacuation")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "more flood -> worse" in out.stdout


def test_render_social_spatial_contagion_emits_coupled_structure():
    spec = GISModelSpec(spatial_type="coupled",
                        mechanism="social_spatial_contagion",
                        capability="social_spatial_contagion")
    code = render(spec)["main.py"]
    assert "networkx" in code
    assert "combined_neighbors" in code
    assert "run_contagion" in code
    assert "social_lift_gate" in code
    assert "RasterTimeline" not in code
    assert "run_dynamic_flood_evacuation" not in code


def test_render_social_spatial_contagion_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="coupled",
                        mechanism="social_spatial_contagion",
                        capability="social_spatial_contagion")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "social lift" in out.stdout


def test_render_point_network_risk_emits_space_zoo_structure():
    spec = GISModelSpec(spatial_type="point",
                        mechanism="point_network_risk",
                        capability="point_network_risk")
    code = render(spec)["main.py"]
    assert "PointSpace" in code
    assert "GeoNetwork" in code
    assert "point_risk_per_edge" in code
    assert "risk_exposure" in code
    assert "point_network_risk_gate" in code
    assert "PolygonSpace" not in code


def test_render_point_network_risk_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="point",
                        mechanism="point_network_risk",
                        capability="point_network_risk")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "point-network risk gate" in out.stdout


def test_render_polygon_point_zoning_emits_space_zoo_structure():
    spec = GISModelSpec(spatial_type="polygon",
                        mechanism="polygon_point_zoning",
                        capability="polygon_point_zoning")
    code = render(spec)["main.py"]
    assert "PointSpace" in code
    assert "PolygonSpace" in code
    assert "assign_points_to_polygons" in code
    assert "polygon_point_zoning_gate" in code
    assert "GeoNetwork" not in code


def test_render_polygon_point_zoning_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="polygon",
                        mechanism="polygon_point_zoning",
                        capability="polygon_point_zoning")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "polygon-point zoning gate" in out.stdout


def test_render_raster_spatial_validation_emits_layer_d_structure():
    spec = GISModelSpec(spatial_type="validation",
                        mechanism="raster_spatial_validation",
                        capability="raster_spatial_validation")
    code = render(spec)["main.py"]
    assert "raster_pattern_metrics" in code
    assert "raster_spatial_loss" in code
    assert "raster_validation_gate" in code
    assert "grid_search_raster_calibration" not in code


def test_render_raster_spatial_validation_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="validation",
                        mechanism="raster_spatial_validation",
                        capability="raster_spatial_validation")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "matches observed raster pattern" in out.stdout


def test_render_raster_spatial_calibration_emits_layer_d_structure():
    spec = GISModelSpec(spatial_type="calibration",
                        mechanism="raster_spatial_calibration",
                        capability="raster_spatial_calibration")
    code = render(spec)["main.py"]
    assert "grid_search_raster_calibration" in code
    assert "raster_spatial_loss" in code
    assert "raster_spatial_calibration_gate" in code
    assert "raster_validation_gate" not in code


def test_render_raster_spatial_calibration_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="calibration",
                        mechanism="raster_spatial_calibration",
                        capability="raster_spatial_calibration")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "spatial calibration selected lower-loss" in out.stdout


def test_render_mechanism_threshold_adoption_emits_mechanism_structure():
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="threshold_adoption",
                        capability="mechanism_threshold_adoption")
    code = render(spec)["main.py"]
    assert "run_threshold_adoption" in code
    assert "mechanism_space_gate" in code
    assert "run_contagion" not in code


def test_render_mechanism_threshold_adoption_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="threshold_adoption",
                        capability="mechanism_threshold_adoption")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "neighbor seam controls threshold adoption" in out.stdout


def test_render_mechanism_contagion_emits_mechanism_structure():
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="contagion",
                        capability="mechanism_contagion")
    code = render(spec)["main.py"]
    assert "run_contagion" in code
    assert "mechanism_contagion_gate" in code
    assert "run_threshold_adoption" not in code
    assert "mechanism_space_gate" not in code


def test_render_mechanism_contagion_uses_spec_seed_not_params_seed():
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="contagion",
                        capability="mechanism_contagion",
                        seed=7,
                        params={"seed": 99})
    code = render(spec)["main.py"]

    assert "SEED = 7" in code
    assert "SEED = 99" not in code
    assert "INITIAL_INFECTED = 0" in code
    assert "seed=SEED" in code
    assert "seeds=(INITIAL_INFECTED,)" in code


def test_render_mechanism_contagion_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="mechanism",
                        mechanism="contagion",
                        capability="mechanism_contagion")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "neighbor seam controls contagion" in out.stdout


def test_render_temporal_flood_evacuation_emits_temporal_structure():
    spec = GISModelSpec(spatial_type="temporal",
                        mechanism="temporal_flood_evacuation",
                        capability="temporal_flood_evacuation")
    code = render(spec)["main.py"]
    assert "RasterTimeline" in code
    assert "RasterSpace" in code
    assert "GeoNetwork" in code
    assert "run_temporal_flood_evacuation" in code
    assert "temporal_flood_gate" in code
    assert "run_dynamic_flood_evacuation" not in code
    assert "dynamic_flood_reroute_gate" not in code


def test_render_temporal_flood_evacuation_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="temporal",
                        mechanism="temporal_flood_evacuation",
                        capability="temporal_flood_evacuation")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "temporal flood state got worse then recovered" in out.stdout


def test_render_dynamic_flood_evacuation_emits_dynamic_structure():
    spec = GISModelSpec(spatial_type="network", mechanism="dynamic_flood_evacuation",
                        capability="dynamic_flood_evacuation")
    code = render(spec)["main.py"]
    assert "RasterTimeline" in code
    assert "RasterSpace" in code
    assert "GeoNetwork" in code
    assert "run_dynamic_flood_evacuation" in code
    assert "dynamic_flood_reroute_gate" in code
    assert "temporal_flood_gate" not in code


def test_render_dynamic_flood_evacuation_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="network", mechanism="dynamic_flood_evacuation",
                        capability="dynamic_flood_evacuation")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "moving-agent rerouting" in out.stdout


def test_render_dynamic_congestion_routing_emits_dynamic_structure():
    spec = GISModelSpec(spatial_type="network",
                        mechanism="dynamic_congestion_routing",
                        capability="dynamic_congestion_routing")
    code = render(spec)["main.py"]
    assert "GeoNetwork" in code
    assert "run_dynamic_congestion_routing" in code
    assert "dynamic_congestion_reroute_gate" in code
    assert "RasterTimeline" not in code
    assert "RasterSpace" not in code
    assert "run_dynamic_flood_evacuation" not in code
    assert "dynamic_flood_reroute_gate" not in code


def test_render_dynamic_congestion_routing_uses_spec_params():
    spec = GISModelSpec(spatial_type="network",
                        mechanism="dynamic_congestion_routing",
                        capability="dynamic_congestion_routing",
                        params={
                            "n_steps": 9,
                            "speed_m_per_tick": 80,
                            "congestion_alpha": 4.5,
                        })
    code = render(spec)["main.py"]

    assert "N_STEPS = 9" in code
    assert "SPEED_M_PER_TICK = 80.0" in code
    assert "CONGESTION_ALPHA = 4.5" in code


def test_render_dynamic_congestion_routing_generates_runnable_model_that_passes_gate(tmp_path):
    spec = GISModelSpec(spatial_type="network",
                        mechanism="dynamic_congestion_routing",
                        capability="dynamic_congestion_routing")
    files = render(spec)
    main = tmp_path / "main.py"
    main.write_text(files["main.py"])
    env = {**os.environ, "PYTHONPATH": _REPO_ROOT}
    out = subprocess.run([sys.executable, str(main)], capture_output=True, text=True,
                         timeout=120, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("PASS"), out.stdout
    assert "moving-agent congestion rerouting" in out.stdout
