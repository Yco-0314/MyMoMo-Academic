import numpy as np
import pytest
import rasterio
from affine import Affine
from rasterio.crs import CRS

from abm_auto.gis._observed_raster_bridge import (
    calibrate_observed_raster,
    load_observed_raster,
    observed_raster_bridge_gate,
    observed_raster_from_array,
    observed_raster_from_field,
    observed_raster_from_space,
    validate_observed_raster,
)
from abm_auto.gis._raster_space import RasterField, RasterSpace


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)) -> np.ndarray:
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster


def _write_tiff(path):
    data = np.arange(12, dtype="float32").reshape(3, 4)
    transform = Affine(100.0, 0, 1000.0, 0, -100.0, 5000.0)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=3,
        width=4,
        count=1,
        dtype="float32",
        crs=CRS.from_epsg(3857),
        transform=transform,
        nodata=-1.0,
    ) as dst:
        dst.write(data, 1)


def test_load_observed_raster_reads_geotiff_and_preserves_provenance(tmp_path):
    path = tmp_path / "observed.tif"
    _write_tiff(path)

    observed = load_observed_raster(
        path,
        source="GHSL clipped fixture",
        dataset="ghsl-built-up",
    )

    assert observed.data.shape == (3, 4)
    assert observed.data[2, 3] == 11.0
    assert observed.shape == (3, 4)
    assert observed.width == 4
    assert observed.height == 3
    assert "3857" in str(observed.crs)
    assert observed.transform.a == 100.0
    assert observed.nodata == -1.0
    assert observed.source == "GHSL clipped fixture"
    assert observed.dataset == "ghsl-built-up"
    assert observed.provenance() == {
        "source": "GHSL clipped fixture",
        "dataset": "ghsl-built-up",
        "shape": (3, 4),
        "crs": str(observed.crs),
    }


def test_load_observed_raster_defaults_source_to_path(tmp_path):
    path = tmp_path / "observed.tif"
    _write_tiff(path)

    observed = load_observed_raster(path)

    assert observed.source == str(path)
    assert observed.dataset == "observed-raster"


def test_observed_raster_from_space_takes_defensive_copy():
    data = _cluster(2, 2)
    field = RasterField(
        data=data,
        transform=Affine.identity(),
        crs="EPSG:3857",
        nodata=0.0,
    )
    space = RasterSpace(field)

    observed = observed_raster_from_space(
        space,
        source="WorldPop clipped fixture",
        dataset="worldpop-population",
    )
    data[2, 2] = 0.0

    assert observed.data[2, 2] == 1.0
    assert observed.source == "WorldPop clipped fixture"
    assert observed.dataset == "worldpop-population"
    assert observed.nodata == 0.0


def test_observed_raster_from_field_preserves_georef():
    field = RasterField(
        data=_cluster(1, 1),
        transform=Affine(30.0, 0, 10.0, 0, -30.0, 100.0),
        crs="EPSG:32650",
        nodata=-9999.0,
    )

    observed = observed_raster_from_field(
        field,
        source="local observed raster",
        dataset="built-up-mask",
    )

    assert observed.data.sum() == 4.0
    assert observed.transform.a == 30.0
    assert observed.crs == "EPSG:32650"
    assert observed.nodata == -9999.0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"source": ""}, "source must be a non-empty string"),
        ({"source": "   "}, "source must be a non-empty string"),
        ({"dataset": ""}, "dataset must be a non-empty string"),
        ({"dataset": "   "}, "dataset must be a non-empty string"),
    ],
)
def test_observed_raster_rejects_blank_provenance_labels(kwargs, message):
    args = {
        "data": _cluster(1, 1),
        "transform": Affine.identity(),
        "crs": "EPSG:3857",
        "source": "source",
        "dataset": "dataset",
    }
    args.update(kwargs)

    with pytest.raises(ValueError, match=message):
        observed_raster_from_array(**args)


def test_observed_raster_rejects_non_2d_data():
    with pytest.raises(ValueError, match="observed data must be a 2-D raster"):
        observed_raster_from_array(
            np.zeros((2, 2, 2)),
            transform=Affine.identity(),
            crs="EPSG:3857",
            source="source",
        )


def test_validate_observed_raster_returns_metrics_loss_gate_and_provenance():
    observed = observed_raster_from_array(
        _cluster(2, 2),
        transform=Affine.identity(),
        crs="EPSG:3857",
        source="GHSL city clip",
        dataset="ghsl-built-up",
    )

    result = validate_observed_raster(_cluster(2, 2), observed)

    assert result["ok"] is True
    assert result["loss"] == 0.0
    assert result["metrics"]["jaccard"] == 1.0
    assert result["observed_source"] == "GHSL city clip"
    assert result["observed_dataset"] == "ghsl-built-up"
    assert result["observed_shape"] == (6, 6)
    assert "matches observed raster pattern" in result["description"]


def test_validate_observed_raster_accepts_simulated_raster_space():
    data = _cluster(2, 2)
    field = RasterField(data=data, transform=Affine.identity(), crs="EPSG:3857")
    simulated = RasterSpace(field)
    observed = observed_raster_from_array(
        data,
        transform=Affine.identity(),
        crs="EPSG:3857",
        source="WorldPop city clip",
    )

    result = validate_observed_raster(simulated, observed)

    assert result["ok"] is True
    assert result["metrics"]["intersection"] == 4


def test_validate_observed_raster_shape_mismatch_uses_existing_metric_error():
    observed = observed_raster_from_array(
        np.zeros((6, 6)),
        transform=Affine.identity(),
        crs="EPSG:3857",
        source="GHSL city clip",
    )

    with pytest.raises(ValueError, match="same shape"):
        validate_observed_raster(np.zeros((4, 4)), observed)


def test_calibrate_observed_raster_selects_lower_loss_params_and_metadata():
    observed = observed_raster_from_array(
        _cluster(2, 3),
        transform=Affine.identity(),
        crs="EPSG:3857",
        source="GHSL clipped fixture",
        dataset="ghsl-built-up",
    )

    def simulator(params):
        return _cluster(int(params["row"]), int(params["col"]))

    result = calibrate_observed_raster(
        simulator,
        observed,
        {"row": [0.0, 2.0], "col": [0.0, 3.0]},
    )

    assert result["ok"] is True
    assert result["best_params"] == {"row": 2.0, "col": 3.0}
    assert result["best_loss"] == 0.0
    assert result["observed_source"] == "GHSL clipped fixture"
    assert result["observed_dataset"] == "ghsl-built-up"
    assert result["observed_shape"] == (6, 6)
    assert result["observed_crs"] == "EPSG:3857"


def test_observed_raster_bridge_gate_passes_with_real_data_caveat():
    ok, desc = observed_raster_bridge_gate()

    assert ok, desc
    assert "observed-raster bridge selected lower-loss parameters" in desc
    assert "not remote data download" in desc
    assert "not Bayesian" in desc
