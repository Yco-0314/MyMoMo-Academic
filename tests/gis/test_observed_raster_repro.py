import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.crs import CRS

from abm_auto.gis._observed_raster_repro import (
    calibrate_observed_raster_from_manifest,
    load_observed_raster_from_manifest,
    load_observed_raster_manifest,
    observed_raster_repro_gate,
)


FIXTURE_DIR = Path("data/fixtures/observed-raster")
TEST_MANIFEST = FIXTURE_DIR / "test_manifest.json"


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)) -> np.ndarray:
    # ponytail: dtype is float32 ON PURPOSE here (the repro path pins float32
    # reproduction — see astype/dtype="float32" below). The sibling test files use
    # a float64 _cluster; do NOT consolidate them into one shared float64 helper or
    # this test's byte-level reproduction guarantee changes.
    raster = np.zeros(shape, dtype="float32")
    raster[top:top + size, left:left + size] = 1.0
    return raster


def _write_tiff(path: Path, data: np.ndarray | None = None) -> None:
    arr = _cluster(2, 3) if data is None else data.astype("float32")
    transform = Affine(100.0, 0, 1000.0, 0, -100.0, 5000.0)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=arr.shape[0],
        width=arr.shape[1],
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(3857),
        transform=transform,
        nodata=0.0,
    ) as dst:
        dst.write(arr, 1)


def _write_manifest(path: Path, **overrides) -> dict:
    manifest = {
        "raster_path": "observed.tif",
        "dataset": "local-test-observed-raster",
        "source_url": "local://tests/gis/observed-raster",
        "license": "local test fixture; not official GHSL or WorldPop data",
        "threshold": 0.5,
        "param_grid": {"row": [0.0, 2.0], "col": [0.0, 3.0]},
        "expected_best_params": {"row": 2.0, "col": 3.0},
        "description": "tiny local GeoTIFF used to test manifest plumbing",
    }
    manifest.update(overrides)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def test_load_observed_raster_manifest_resolves_relative_raster_path(tmp_path):
    _write_tiff(tmp_path / "observed.tif")
    _write_manifest(tmp_path / "manifest.json")

    manifest = load_observed_raster_manifest(tmp_path / "manifest.json")

    assert manifest["raster_path"] == str((tmp_path / "observed.tif").resolve())
    assert manifest["dataset"] == "local-test-observed-raster"
    assert manifest["source_url"] == "local://tests/gis/observed-raster"
    assert manifest["license"].startswith("local test fixture")
    assert manifest["threshold"] == 0.5
    assert manifest["param_grid"] == {"row": [0.0, 2.0], "col": [0.0, 3.0]}
    assert manifest["expected_best_params"] == {"row": 2.0, "col": 3.0}


def test_load_observed_raster_manifest_keeps_absolute_raster_path(tmp_path):
    raster_path = tmp_path / "absolute.tif"
    _write_tiff(raster_path)
    _write_manifest(tmp_path / "manifest.json", raster_path=str(raster_path))

    manifest = load_observed_raster_manifest(tmp_path / "manifest.json")

    assert manifest["raster_path"] == str(raster_path.resolve())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("raster_path", "", "raster_path must be a non-empty string"),
        ("dataset", "", "dataset must be a non-empty string"),
        ("source_url", "", "source_url must be a non-empty string"),
        ("license", "", "license must be a non-empty string"),
        ("threshold", "0.5", "threshold must be a finite number"),
        ("threshold", True, "threshold must be a finite number"),
        ("param_grid", {}, "param_grid must be a non-empty dict"),
        ("expected_best_params", {}, "expected_best_params must be a non-empty dict"),
    ],
)
def test_load_observed_raster_manifest_rejects_malformed_fields(
    tmp_path,
    field,
    value,
    message,
):
    _write_tiff(tmp_path / "observed.tif")
    _write_manifest(tmp_path / "manifest.json", **{field: value})

    with pytest.raises(ValueError, match=message):
        load_observed_raster_manifest(tmp_path / "manifest.json")


def test_load_observed_raster_manifest_rejects_missing_local_raster(tmp_path):
    _write_manifest(tmp_path / "manifest.json", raster_path="missing.tif")

    with pytest.raises(ValueError, match="raster_path does not exist"):
        load_observed_raster_manifest(tmp_path / "manifest.json")


def test_load_observed_raster_from_manifest_uses_manifest_provenance(tmp_path):
    _write_tiff(tmp_path / "observed.tif")
    _write_manifest(
        tmp_path / "manifest.json",
        dataset="ghsl-style-local-clip",
        source_url="https://example.test/source",
    )

    observed = load_observed_raster_from_manifest(tmp_path / "manifest.json")

    assert observed.data.shape == (6, 6)
    assert observed.data[2, 3] == 1.0
    assert observed.dataset == "ghsl-style-local-clip"
    assert observed.source == "ghsl-style-local-clip: https://example.test/source"
    assert "3857" in observed.crs


def test_calibrate_observed_raster_from_manifest_uses_grid_and_metadata(tmp_path):
    _write_tiff(tmp_path / "observed.tif")
    _write_manifest(
        tmp_path / "manifest.json",
        dataset="ghsl-style-local-clip",
        source_url="https://example.test/source",
    )

    def simulator(params):
        return _cluster(int(params["row"]), int(params["col"]))

    result = calibrate_observed_raster_from_manifest(
        simulator,
        tmp_path / "manifest.json",
    )

    assert result["ok"] is True
    assert result["best_params"] == {"row": 2.0, "col": 3.0}
    assert result["best_loss"] == 0.0
    assert result["manifest_dataset"] == "ghsl-style-local-clip"
    assert result["manifest_source_url"] == "https://example.test/source"
    assert result["manifest_license"].startswith("local test fixture")


def test_observed_raster_repro_gate_passes_with_local_fixture_boundary():
    ok, desc = observed_raster_repro_gate(TEST_MANIFEST)

    assert ok, desc
    assert "observed-raster repro pack selected expected parameters" in desc
    assert "not remote data download" in desc
    assert "not Bayesian" in desc
    assert "not official GHSL or WorldPop pixels" in desc
