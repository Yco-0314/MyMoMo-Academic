import numpy as np
import pytest

from abm_auto.calibration.types import CalibrationResult
from abm_auto.gis._calibration_objective_bridge import (
    RasterSpatialLossObjective,
    base_calibration_objective_bridge_gate,
    make_raster_spatial_loss_objective,
    raster_spatial_loss_observed_stats,
    raster_spatial_loss_targets,
    run_base_abc_raster_spatial_calibration,
)


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)) -> np.ndarray:
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster


def _location_simulator(params):
    return _cluster(int(params["row"]), int(params["col"]))


def test_spatial_loss_targets_and_observed_stats_match_base_contract():
    assert raster_spatial_loss_targets() == ["spatial_loss"]

    observed_stats = raster_spatial_loss_observed_stats()

    assert isinstance(observed_stats, np.ndarray)
    assert observed_stats.shape == (1,)
    assert observed_stats.tolist() == [0.0]


def test_raster_spatial_loss_objective_returns_single_stat_loss_and_records_calls():
    objective = make_raster_spatial_loss_objective(
        _location_simulator,
        _cluster(2, 3),
    )

    matching = objective.simulate(
        {"row": 2.0, "col": 3.0},
        ["spatial_loss"],
    )
    shifted = objective.simulate(
        {"row": 0.0, "col": 0.0},
        ["spatial_loss"],
    )

    assert isinstance(objective, RasterSpatialLossObjective)
    assert matching.shape == (1,)
    assert matching[0] == 0.0
    assert shifted[0] > matching[0]
    assert objective.n_calls == 2
    assert objective.evaluations[0]["params"] == {"row": 2.0, "col": 3.0}
    assert objective.evaluations[0]["loss"] == 0.0
    assert objective.evaluations[0]["metrics"]["jaccard"] == 1.0


def test_raster_spatial_loss_objective_rejects_wrong_targets():
    objective = make_raster_spatial_loss_objective(
        _location_simulator,
        _cluster(2, 3),
    )

    with pytest.raises(ValueError, match="targets must be \\['spatial_loss'\\]"):
        objective.simulate({"row": 2.0, "col": 3.0}, ["wrong"])


def test_base_abc_bridge_returns_calibration_result_and_zero_loss_best_params():
    result = run_base_abc_raster_spatial_calibration(
        _location_simulator,
        _cluster(2, 3),
        {"row": {"min": 0.0, "max": 4.0}, "col": {"min": 0.0, "max": 4.0}},
        max_sims=200,
        seed=42,
    )

    assert result["ok"] is True
    assert result["backend"] == "gis-spatial-loss+abc-rejection"
    assert isinstance(result["calibration_result"], CalibrationResult)
    assert result["calibration_result"].backend == "abc-rejection"
    assert result["targets"] == ["spatial_loss"]
    assert result["observed_stats"].tolist() == [0.0]
    assert result["best_loss"] == 0.0
    assert int(result["best_params"]["row"]) == 2
    assert int(result["best_params"]["col"]) == 3
    assert result["n_simulator_calls"] == 200


def test_base_abc_bridge_restores_numpy_random_state_when_seeded():
    np.random.seed(2026)
    expected_first = float(np.random.random())
    np.random.seed(2026)

    run_base_abc_raster_spatial_calibration(
        _location_simulator,
        _cluster(2, 3),
        {"row": {"min": 0.0, "max": 4.0}, "col": {"min": 0.0, "max": 4.0}},
        max_sims=20,
        seed=42,
    )

    assert float(np.random.random()) == expected_first


def test_base_calibration_objective_bridge_gate_passes_with_boundary_text():
    ok, desc = base_calibration_objective_bridge_gate()

    assert ok, desc
    assert "base ABC consumed GIS spatial loss objective" in desc
    assert "abm_auto/calibration/ was not modified" in desc
    assert "not full BayesianCalibrator.run" in desc
