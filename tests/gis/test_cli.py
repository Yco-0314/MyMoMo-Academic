"""Tests for the `abm-auto gis ...` CLI sub-app (CLI parity for GIS mode)."""
from __future__ import annotations

import json

from typer.testing import CliRunner

from abm_auto.cli import app
from abm_auto.gis._cli import gis_app

runner = CliRunner()


def test_gis_subapp_mounted_on_main_cli():
    # The guarded mount in cli.py exposes `abm-auto gis ...`.
    result = runner.invoke(app, ["gis", "capabilities"])
    assert result.exit_code == 0, result.stdout
    assert "raster_sir" in result.stdout


def test_capabilities_lists_params_from_schema():
    result = runner.invoke(gis_app, ["capabilities"])
    assert result.exit_code == 0
    assert "raster_sir" in result.stdout
    assert "params:" in result.stdout
    assert "steps:int" in result.stdout  # the declarative param schema surfaces


def test_render_writes_main_py(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "spatial_type": "raster", "mechanism": "sir",
        "capability": "raster_sir", "params": {"steps": 5},
    }))
    out = tmp_path / "main.py"
    result = runner.invoke(gis_app, ["render", str(spec), "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    assert out.exists() and out.read_text().strip()


def test_render_rejects_unknown_param(tmp_path):
    # The #2 param schema rejects unknown params at validate() time → render fails.
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "spatial_type": "raster", "mechanism": "sir",
        "capability": "raster_sir", "params": {"stteps": 5},
    }))
    result = runner.invoke(gis_app, ["render", str(spec)])
    assert result.exit_code != 0


def test_run_spec_end_to_end(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({
        "spatial_type": "raster", "mechanism": "sir",
        "capability": "raster_sir", "params": {"steps": 3}, "seed": 0,
    }))
    out = tmp_path / "out"
    result = runner.invoke(gis_app, ["run", str(spec), "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    assert (out / "main.py").exists()
