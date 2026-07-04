from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from abm_auto.terrain_bridge import (
    load_terrain_bridge_manifest,
    terrain_bridge_gate,
    terrain_metrics_gate,
    summarize_terrain_bridge_manifest,
    validate_terrain_bridge_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "docs/reproduce/terrain-bridge/example-manifest.json"


def _manifest() -> dict:
    return load_terrain_bridge_manifest(MANIFEST_PATH)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_dem_raster(path: Path) -> np.ndarray:
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    data = np.array(
        [
            [1.0, 2.0, 3.0],
            [2.0, 3.0, 5.0],
        ],
        dtype="float32",
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:3857",
        transform=from_origin(0, 2, 1, 1),
    ) as dst:
        dst.write(data, 1)
    return data


def _dem_manifest(tmp_path: Path) -> dict:
    dem_path = tmp_path / "dem.tif"
    _write_dem_raster(dem_path)
    manifest = _manifest()
    manifest["terrain_source"]["kind"] = "dem_raster"
    manifest["terrain_source"]["path"] = "dem.tif"
    manifest["terrain_source"]["sha256"] = _sha256(dem_path)
    manifest["terrain_source"]["provenance"] = "Temporary synthetic GeoTIFF DEM for tests."
    manifest["coordinate_frame"]["grid_shape"] = [2, 3]
    return manifest


def test_committed_manifest_validates_and_gate_passes():
    manifest = _manifest()

    validation = validate_terrain_bridge_manifest(manifest, repo=REPO_ROOT)
    ok, message = terrain_bridge_gate(manifest, repo=REPO_ROOT)

    assert validation["ok"] is True
    assert validation["manifest_id"] == "terrain-bridge-seed"
    assert validation["consumer_count"] == 4
    assert ok is True
    assert message.startswith("Terrain bridge manifest gate passed")
    assert "not a 3D renderer" in message
    assert "not a physical simulation certificate" in message


def test_checksum_mismatch_fails():
    manifest = _manifest()
    manifest["terrain_source"]["sha256"] = "0" * 64

    validation = validate_terrain_bridge_manifest(manifest, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "terrain_source.sha256 does not match file" in validation["issues"]


def test_source_path_must_be_repo_relative_and_existing():
    absolute_manifest = _manifest()
    absolute_manifest["terrain_source"]["path"] = str(
        REPO_ROOT / "docs/reproduce/terrain-bridge/example-heightfield.asc"
    )

    absolute_validation = validate_terrain_bridge_manifest(
        absolute_manifest,
        repo=REPO_ROOT,
    )

    assert absolute_validation["ok"] is False
    assert "terrain_source.path must be repo-relative" in absolute_validation["issues"]

    missing_manifest = _manifest()
    missing_manifest["terrain_source"]["path"] = "docs/reproduce/terrain-bridge/missing.asc"

    missing_validation = validate_terrain_bridge_manifest(missing_manifest, repo=REPO_ROOT)

    assert missing_validation["ok"] is False
    assert "terrain_source.path does not exist" in missing_validation["issues"]


def test_invalid_grid_shape_fails():
    manifest = _manifest()
    manifest["coordinate_frame"]["grid_shape"] = [3, 0]

    validation = validate_terrain_bridge_manifest(manifest, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "coordinate_frame.grid_shape must be [rows, cols] positive integers" in validation["issues"]


def test_ascii_heightfield_shape_mismatch_fails():
    manifest = _manifest()
    manifest["coordinate_frame"]["grid_shape"] = [2, 3]

    validation = validate_terrain_bridge_manifest(manifest, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "terrain_source ASCII shape 3x3 does not match declared 2x3" in validation["issues"]


def test_unknown_source_kind_fails():
    manifest = _manifest()
    manifest["terrain_source"]["kind"] = "point_cloud"

    validation = validate_terrain_bridge_manifest(manifest, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "terrain_source.kind must be one of" in validation["issues"][0]


def test_unknown_consumer_domain_fails():
    manifest = _manifest()
    manifest["consumers"][0]["domain"] = "game_engine"

    validation = validate_terrain_bridge_manifest(manifest, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "consumers[0].domain must be one of" in validation["issues"][0]


def test_missing_required_boundary_rule_fails():
    manifest = _manifest()
    del manifest["boundary_rules"]["no_physical_solver_claim"]

    validation = validate_terrain_bridge_manifest(manifest, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "boundary_rules.no_physical_solver_claim is required" in validation["issues"]


def test_weak_boundary_note_fails():
    manifest = _manifest()
    manifest["boundary_note"] = "Terrain exchange contract."

    validation = validate_terrain_bridge_manifest(manifest, repo=REPO_ROOT)
    ok, message = terrain_bridge_gate(manifest, repo=REPO_ROOT)

    assert validation["ok"] is False
    assert "boundary_note must say this is not a 3D renderer" in validation["issues"]
    assert "boundary_note must say this is not a physical simulation certificate" in validation["issues"]
    assert ok is False
    assert message.startswith("Terrain bridge manifest gate failed")


def test_committed_heightfield_summary_metrics_are_deterministic():
    summary = summarize_terrain_bridge_manifest(_manifest(), repo=REPO_ROOT)

    assert summary["ok"] is True
    assert summary["manifest_id"] == "terrain-bridge-seed"
    assert summary["source_kind"] == "ascii_heightfield"
    assert summary["rows"] == 3
    assert summary["cols"] == 3
    assert summary["min_elevation"] == 1.0
    assert summary["max_elevation"] == 5.0
    assert summary["mean_elevation"] == 3.0
    assert summary["relief"] == 4.0
    assert summary["max_neighbor_delta"] == 1.0
    assert "not a 3D renderer" in summary["boundary_note"]


def test_terrain_metrics_gate_passes_with_boundary_text():
    ok, message = terrain_metrics_gate(_manifest(), repo=REPO_ROOT)

    assert ok is True
    assert message.startswith("Terrain metrics gate passed")
    assert "not a 3D renderer" in message
    assert "not a physical simulation certificate" in message


def test_flat_heightfield_fails_metrics_gate(tmp_path):
    (tmp_path / "flat.asc").write_text("1 1\n1 1\n", encoding="utf-8")
    manifest = _manifest()
    manifest["terrain_source"]["path"] = "flat.asc"
    manifest["terrain_source"]["sha256"] = (
        "f5c5e583808c61ef64c7c606dbd9f107efadadc78ef231dae68662e333a2d573"
    )
    manifest["coordinate_frame"]["grid_shape"] = [2, 2]

    summary = summarize_terrain_bridge_manifest(manifest, repo=tmp_path)
    ok, message = terrain_metrics_gate(manifest, repo=tmp_path)

    assert summary["ok"] is True
    assert summary["relief"] == 0.0
    assert ok is False
    assert "terrain relief must be positive" in message


def test_dem_raster_metrics_pass_for_local_geotiff(tmp_path):
    manifest = _dem_manifest(tmp_path)

    summary = summarize_terrain_bridge_manifest(manifest, repo=tmp_path)
    ok, message = terrain_metrics_gate(manifest, repo=tmp_path)

    assert summary["ok"] is True
    assert summary["manifest_id"] == "terrain-bridge-seed"
    assert summary["source_kind"] == "dem_raster"
    assert summary["rows"] == 2
    assert summary["cols"] == 3
    assert summary["min_elevation"] == 1.0
    assert summary["max_elevation"] == 5.0
    assert summary["mean_elevation"] == pytest.approx(16.0 / 6.0)
    assert summary["relief"] == 4.0
    assert summary["max_neighbor_delta"] == 2.0
    assert ok is True
    assert message.startswith("Terrain metrics gate passed")
    assert "not a 3D renderer" in message


def test_dem_raster_metrics_fail_on_declared_shape_mismatch(tmp_path):
    manifest = _dem_manifest(tmp_path)
    manifest["coordinate_frame"]["grid_shape"] = [3, 3]

    summary = summarize_terrain_bridge_manifest(manifest, repo=tmp_path)

    assert summary["ok"] is False
    assert "terrain_source DEM raster shape 2x3 does not match declared 3x3" in summary["issues"]


def test_malformed_ascii_metrics_fail_with_readable_issue(tmp_path):
    (tmp_path / "bad.asc").write_text("1 nope\n", encoding="utf-8")
    manifest = _manifest()
    manifest["terrain_source"]["path"] = "bad.asc"
    manifest["terrain_source"]["sha256"] = (
        "dc029477effc1cb4dc60e2c45ea2c70aa60a88494f8ef6fb1329d1e590f0d5c8"
    )
    manifest["coordinate_frame"]["grid_shape"] = [1, 2]

    summary = summarize_terrain_bridge_manifest(manifest, repo=tmp_path)

    assert summary["ok"] is False
    assert "terrain_source ASCII row 1 contains a non-numeric value" in summary["issues"]
