"""Observed raster bridge for GIS spatial validation and calibration.

This module is the small real-data adapter between local observed rasters and
the existing deterministic raster validation/calibration functions. It does not
download, reproject, resample, or import the base calibration package.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from abm_auto.gis._io import load_raster
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._spatial_calibration import grid_search_raster_calibration
from abm_auto.gis._spatial_validation import (
    raster_pattern_metrics,
    raster_spatial_loss,
    raster_validation_gate,
)


def _non_empty_label(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _observed_array_copy(data: Any) -> np.ndarray:
    arr = np.asarray(data, dtype=float)
    if arr.ndim != 2:
        raise ValueError("observed data must be a 2-D raster")
    return arr.copy()


def _raster_data(raster: Any) -> np.ndarray:
    if isinstance(raster, ObservedRasterTarget):
        return raster.data
    if isinstance(raster, RasterSpace):
        return np.asarray(raster.field.data, dtype=float)
    if isinstance(raster, RasterField):
        return np.asarray(raster.data, dtype=float)
    return np.asarray(raster, dtype=float)


@dataclass(frozen=True)
class ObservedRasterTarget:
    """Observed raster with provenance for validation/calibration outputs."""

    data: np.ndarray
    transform: Any
    crs: str
    source: str
    dataset: str = "observed-raster"
    nodata: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _observed_array_copy(self.data))
        object.__setattr__(self, "source", _non_empty_label("source", self.source))
        object.__setattr__(
            self,
            "dataset",
            _non_empty_label("dataset", self.dataset),
        )
        object.__setattr__(self, "crs", str(self.crs))

    @property
    def shape(self) -> tuple[int, int]:
        return self.data.shape

    @property
    def height(self) -> int:
        return int(self.data.shape[0])

    @property
    def width(self) -> int:
        return int(self.data.shape[1])

    def provenance(self) -> dict:
        return {
            "source": self.source,
            "dataset": self.dataset,
            "shape": self.shape,
            "crs": str(self.crs),
        }


def observed_raster_from_array(
    data: Any,
    *,
    transform: Any,
    crs: str,
    source: str,
    dataset: str = "observed-raster",
    nodata: float | None = None,
) -> ObservedRasterTarget:
    """Build an observed raster target from an in-memory array."""
    return ObservedRasterTarget(
        data=data,
        transform=transform,
        crs=crs,
        source=source,
        dataset=dataset,
        nodata=nodata,
    )


def observed_raster_from_field(
    field: RasterField,
    *,
    source: str,
    dataset: str = "observed-raster",
) -> ObservedRasterTarget:
    """Wrap a RasterField as an observed target."""
    if not isinstance(field, RasterField):
        raise ValueError("field must be a RasterField")
    return observed_raster_from_array(
        field.data,
        transform=field.transform,
        crs=field.crs,
        source=source,
        dataset=dataset,
        nodata=field.nodata,
    )


def observed_raster_from_space(
    space: RasterSpace,
    *,
    source: str,
    dataset: str = "observed-raster",
) -> ObservedRasterTarget:
    """Wrap a RasterSpace as an observed target."""
    if not isinstance(space, RasterSpace):
        raise ValueError("space must be a RasterSpace")
    return observed_raster_from_field(
        space.field,
        source=source,
        dataset=dataset,
    )


def load_observed_raster(
    path,
    band: int = 1,
    *,
    source: str | None = None,
    dataset: str = "observed-raster",
) -> ObservedRasterTarget:
    """Load a local observed GeoTIFF and attach source metadata."""
    field = load_raster(path, band=band)
    source_label = str(Path(path)) if source is None else source
    return observed_raster_from_field(
        field,
        source=source_label,
        dataset=dataset,
    )


def _observed_metadata(observed: ObservedRasterTarget) -> dict:
    return {
        "observed_source": observed.source,
        "observed_dataset": observed.dataset,
        "observed_shape": observed.shape,
        "observed_crs": str(observed.crs),
    }


def validate_observed_raster(
    simulated: Any,
    observed: ObservedRasterTarget,
    threshold: float = 0.5,
    min_jaccard: float = 0.5,
    max_centroid_distance_cells: float = 2.0,
) -> dict:
    """Validate a simulated raster against a provenance-bearing observed target."""
    if not isinstance(observed, ObservedRasterTarget):
        raise ValueError("observed must be an ObservedRasterTarget")
    simulated_data = _raster_data(simulated)
    metrics = raster_pattern_metrics(
        simulated_data,
        observed.data,
        threshold=threshold,
    )
    loss = raster_spatial_loss(metrics)
    ok, description = raster_validation_gate(
        simulated_data,
        observed.data,
        threshold=threshold,
        min_jaccard=min_jaccard,
        max_centroid_distance_cells=max_centroid_distance_cells,
    )
    return {
        "ok": bool(ok),
        "description": description,
        "loss": float(loss),
        "metrics": metrics,
        **_observed_metadata(observed),
    }


def calibrate_observed_raster(
    simulator,
    observed: ObservedRasterTarget,
    param_grid: dict[str, list[float]],
    threshold: float = 0.5,
) -> dict:
    """Run deterministic raster calibration against a real observed target."""
    if not isinstance(observed, ObservedRasterTarget):
        raise ValueError("observed must be an ObservedRasterTarget")
    result = dict(
        grid_search_raster_calibration(
            simulator,
            observed.data,
            param_grid,
            threshold=threshold,
        )
    )
    result.update(_observed_metadata(observed))
    return result


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)) -> np.ndarray:
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster


def observed_raster_bridge_gate() -> tuple[bool, str]:
    """Gate proving observed-raster provenance reaches calibration results."""
    observed = observed_raster_from_array(
        _cluster(2, 3),
        transform=None,
        crs="EPSG:3857",
        source="GHSL/WorldPop style local observed raster clip",
        dataset="observed-built-up-mask",
    )

    def simulator(params: dict[str, float]):
        return _cluster(int(params["row"]), int(params["col"]))

    result = calibrate_observed_raster(
        simulator,
        observed,
        {"row": [0.0, 2.0], "col": [0.0, 3.0]},
    )
    losses = [evaluation["loss"] for evaluation in result["evaluations"]]
    has_improvement = any(loss > result["best_loss"] for loss in losses)

    if result["best_params"] != {"row": 2.0, "col": 3.0}:
        return False, f"observed-raster bridge chose {result['best_params']}"
    if not has_improvement:
        return False, "observed-raster bridge produced no lower-loss improvement"
    if result["observed_source"] != observed.source:
        return False, "observed-raster bridge lost source provenance"

    return (
        True,
        "observed-raster bridge selected lower-loss parameters "
        f"(source={result['observed_source']}, "
        f"best_loss={result['best_loss']:.6f}); "
        "this is local observed-raster validation/calibration plumbing, "
        "not remote data download and not Bayesian posterior inference",
    )
