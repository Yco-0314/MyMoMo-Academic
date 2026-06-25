import math

import numpy as np
import pytest

from abm_auto.gis._spatial_validation import (
    raster_pattern_metrics,
    raster_spatial_loss,
    raster_validation_gate,
)


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)) -> np.ndarray:
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster


def test_identical_clustered_rasters_have_perfect_metrics_and_zero_loss():
    observed = _cluster(2, 2)
    simulated = observed.copy()

    metrics = raster_pattern_metrics(simulated, observed)

    assert metrics["simulated_total"] == 4
    assert metrics["observed_total"] == 4
    assert metrics["intersection"] == 4
    assert metrics["union"] == 4
    assert metrics["jaccard"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["centroid_distance_cells"] == 0.0
    assert metrics["morans_i_abs_error"] == 0.0
    assert metrics["raster_diagonal_cells"] == pytest.approx(math.hypot(5, 5))
    assert raster_spatial_loss(metrics) == 0.0


def test_shifted_clusters_have_lower_overlap_and_centroid_distance():
    observed = _cluster(2, 2)
    simulated = _cluster(2, 3)

    metrics = raster_pattern_metrics(simulated, observed)

    assert metrics["intersection"] == 2
    assert metrics["union"] == 6
    assert metrics["jaccard"] == pytest.approx(1.0 / 3.0)
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["centroid_distance_cells"] == 1.0
    assert raster_spatial_loss(metrics) > 0.0


def test_empty_simulated_pattern_has_infinite_centroid_distance_and_finite_loss():
    observed = _cluster(2, 2)
    simulated = np.zeros_like(observed)

    metrics = raster_pattern_metrics(simulated, observed)

    assert metrics["simulated_total"] == 0
    assert metrics["observed_total"] == 4
    assert metrics["jaccard"] == 0.0
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert math.isinf(metrics["centroid_distance_cells"])
    assert math.isfinite(raster_spatial_loss(metrics))


def test_both_empty_rasters_have_zero_centroid_distance_and_zero_loss():
    observed = np.zeros((6, 6), dtype=float)
    simulated = np.zeros_like(observed)

    metrics = raster_pattern_metrics(simulated, observed)

    assert metrics["jaccard"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["centroid_distance_cells"] == 0.0
    assert raster_spatial_loss(metrics) == 0.0


def test_raster_pattern_metrics_rejects_shape_mismatch():
    with pytest.raises(ValueError, match="same shape"):
        raster_pattern_metrics(np.zeros((3, 3)), np.zeros((3, 4)))


def test_raster_pattern_metrics_rejects_non_2d_rasters():
    with pytest.raises(ValueError, match="2-D"):
        raster_pattern_metrics(np.zeros((2, 2, 2)), np.zeros((2, 2, 2)))


def test_raster_validation_gate_passes_for_matching_cluster():
    observed = _cluster(2, 2)
    simulated = observed.copy()

    ok, desc = raster_validation_gate(simulated, observed)

    assert ok, desc
    assert "matches observed raster pattern" in desc


def test_raster_validation_gate_fails_empty_observed_signal():
    observed = np.zeros((6, 6), dtype=float)
    simulated = _cluster(2, 2)

    ok, desc = raster_validation_gate(simulated, observed)

    assert not ok
    assert "observed raster has no positive cells" in desc


def test_raster_validation_gate_fails_empty_simulated_signal():
    observed = _cluster(2, 2)
    simulated = np.zeros_like(observed)

    ok, desc = raster_validation_gate(simulated, observed)

    assert not ok
    assert "simulated raster has no positive cells" in desc


def test_raster_validation_gate_fails_low_overlap():
    observed = _cluster(0, 0, shape=(8, 8))
    simulated = _cluster(5, 5, shape=(8, 8))

    ok, desc = raster_validation_gate(simulated, observed)

    assert not ok
    assert "jaccard" in desc


def test_raster_validation_gate_fails_far_centroid_when_overlap_threshold_relaxed():
    observed = _cluster(0, 0, shape=(8, 8))
    simulated = _cluster(5, 5, shape=(8, 8))

    ok, desc = raster_validation_gate(
        simulated,
        observed,
        min_jaccard=0.0,
        max_centroid_distance_cells=2.0,
    )

    assert not ok
    assert "centroid" in desc


def test_raster_validation_gate_rejects_non_finite_thresholds():
    observed = _cluster(2, 2)
    simulated = observed.copy()

    with pytest.raises(ValueError, match="min_jaccard"):
        raster_validation_gate(simulated, observed, min_jaccard=float("nan"))

    with pytest.raises(ValueError, match="max_centroid_distance_cells"):
        raster_validation_gate(
            simulated,
            observed,
            max_centroid_distance_cells=float("nan"),
        )


def test_raster_validation_gate_allows_exact_jaccard_threshold():
    observed = _cluster(2, 2)
    simulated = _cluster(2, 3)

    ok, desc = raster_validation_gate(
        simulated,
        observed,
        min_jaccard=1.0 / 3.0,
        max_centroid_distance_cells=2.0,
    )

    assert ok, desc


def test_raster_validation_gate_allows_exact_centroid_threshold():
    observed = _cluster(2, 2)
    simulated = _cluster(2, 3)

    ok, desc = raster_validation_gate(
        simulated,
        observed,
        min_jaccard=0.0,
        max_centroid_distance_cells=1.0,
    )

    assert ok, desc
