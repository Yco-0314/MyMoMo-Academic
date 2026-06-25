import numpy as np
import pytest

from abm_auto.gis._spatial_calibration import (
    evaluate_raster_params,
    grid_search_raster_calibration,
    raster_spatial_calibration_gate,
)


def _cluster(top: int, left: int, size: int = 2, shape=(6, 6)) -> np.ndarray:
    raster = np.zeros(shape, dtype=float)
    raster[top:top + size, left:left + size] = 1.0
    return raster


def _location_simulator(params):
    return _cluster(int(params["row"]), int(params["col"]))


def test_evaluate_raster_params_returns_loss_metrics_and_copied_params():
    observed = _cluster(2, 3)
    params = {"row": 2.0, "col": 3.0}

    result = evaluate_raster_params(_location_simulator, observed, params)
    params["row"] = 0.0

    assert result["params"] == {"row": 2.0, "col": 3.0}
    assert result["params"] is not params
    assert result["loss"] == 0.0
    assert result["metrics"]["jaccard"] == 1.0
    assert np.array_equal(result["simulated"], observed)


def test_simulator_receives_defensive_params_copy():
    observed = _cluster(2, 3)
    original = {"row": 2.0, "col": 3.0}
    seen = []

    def simulator(params):
        seen.append(params)
        params["row"] = 0.0
        return _cluster(2, 3)

    result = evaluate_raster_params(simulator, observed, original)

    assert original == {"row": 2.0, "col": 3.0}
    assert seen[0] is not original
    assert result["params"] == {"row": 2.0, "col": 3.0}


def test_grid_search_finds_known_best_params_and_keeps_evaluation_order():
    observed = _cluster(2, 3)

    result = grid_search_raster_calibration(
        _location_simulator,
        observed,
        {"row": [0.0, 2.0], "col": [0.0, 3.0]},
    )

    assert result["ok"] is True
    assert result["backend"] == "gis-raster-grid-search"
    assert result["best_params"] == {"row": 2.0, "col": 3.0}
    assert result["best_loss"] == 0.0
    assert result["best_metrics"]["jaccard"] == 1.0
    assert result["n_evaluations"] == 4
    assert result["reason"] == ""
    assert [e["rank"] for e in result["evaluations"]] == [0, 1, 2, 3]
    assert [e["params"] for e in result["evaluations"]] == [
        {"row": 0.0, "col": 0.0},
        {"row": 0.0, "col": 3.0},
        {"row": 2.0, "col": 0.0},
        {"row": 2.0, "col": 3.0},
    ]
    assert all("metrics" in e for e in result["evaluations"])
    assert all("simulated" in e for e in result["evaluations"])


def test_grid_search_ties_keep_first_candidate():
    observed = _cluster(1, 1)

    def simulator(_params):
        return observed.copy()

    result = grid_search_raster_calibration(
        simulator,
        observed,
        {"alpha": [1.0, 2.0]},
    )

    assert result["best_params"] == {"alpha": 1.0}
    assert result["best_loss"] == 0.0
    assert [e["loss"] for e in result["evaluations"]] == [0.0, 0.0]


def test_raster_spatial_calibration_gate_passes_for_synthetic_recovery():
    ok, desc = raster_spatial_calibration_gate()

    assert ok, desc
    assert "spatial calibration selected lower-loss raster parameters" in desc
    assert "not Bayesian" in desc


def test_no_effect_grid_search_has_no_improvement():
    observed = _cluster(2, 2)

    def simulator(_params):
        return _cluster(0, 0)

    result = grid_search_raster_calibration(
        simulator,
        observed,
        {"alpha": [1.0, 2.0]},
    )

    losses = [evaluation["loss"] for evaluation in result["evaluations"]]
    assert result["best_params"] == {"alpha": 1.0}
    assert losses[0] == losses[1]
    assert not any(loss > result["best_loss"] for loss in losses)


def test_grid_search_best_metrics_do_not_alias_winning_evaluation_metrics():
    observed = _cluster(2, 3)

    result = grid_search_raster_calibration(
        _location_simulator,
        observed,
        {"row": [0.0, 2.0], "col": [0.0, 3.0]},
    )

    winning_rank = next(
        e["rank"] for e in result["evaluations"] if e["params"] == result["best_params"]
    )
    result["evaluations"][winning_rank]["metrics"]["jaccard"] = -1.0

    assert result["best_metrics"]["jaccard"] == 1.0


@pytest.mark.parametrize(
    ("param_grid", "message"),
    [
        ({}, "param_grid must be a non-empty dict"),
        ({"": [1.0]}, "parameter names must be non-empty strings"),
        ({"alpha": []}, "parameter grid for alpha must be non-empty"),
        ({"alpha": [True]}, "alpha must be a finite number"),
        ({"alpha": ["1"]}, "alpha must be a finite number"),
        ({"alpha": [float("nan")]}, "alpha must be a finite number"),
        ({"alpha": [float("inf")]}, "alpha must be a finite number"),
    ],
)
def test_grid_search_rejects_invalid_param_grid(param_grid, message):
    with pytest.raises(ValueError, match=message):
        grid_search_raster_calibration(
            lambda _params: _cluster(1, 1),
            _cluster(1, 1),
            param_grid,
        )


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ({}, "params must be a non-empty dict"),
        ({"": 1.0}, "parameter names must be non-empty strings"),
        ({"alpha": True}, "alpha must be a finite number"),
        ({"alpha": "1"}, "alpha must be a finite number"),
        ({"alpha": float("nan")}, "alpha must be a finite number"),
        ({"alpha": float("inf")}, "alpha must be a finite number"),
    ],
)
def test_evaluate_rejects_invalid_params(params, message):
    with pytest.raises(ValueError, match=message):
        evaluate_raster_params(lambda _params: _cluster(1, 1), _cluster(1, 1), params)


@pytest.mark.parametrize("threshold", [True, "0.5", float("nan"), float("inf")])
def test_evaluate_rejects_invalid_threshold(threshold):
    with pytest.raises(ValueError, match="threshold must be a finite number"):
        evaluate_raster_params(
            lambda _params: _cluster(1, 1),
            _cluster(1, 1),
            {"alpha": 1.0},
            threshold=threshold,
        )


@pytest.mark.parametrize("threshold", [True, "0.5", float("nan"), float("inf")])
def test_grid_search_rejects_invalid_threshold(threshold):
    with pytest.raises(ValueError, match="threshold must be a finite number"):
        grid_search_raster_calibration(
            lambda _params: _cluster(1, 1),
            _cluster(1, 1),
            {"alpha": [1.0]},
            threshold=threshold,
        )


def test_evaluate_rejects_wrong_shape_simulator_output():
    with pytest.raises(ValueError, match="same shape"):
        evaluate_raster_params(
            lambda _params: np.zeros((4, 4)),
            np.zeros((6, 6)),
            {"alpha": 1.0},
        )


def test_evaluate_rejects_non_2d_simulator_output():
    with pytest.raises(ValueError, match="2-D"):
        evaluate_raster_params(
            lambda _params: np.zeros((2, 2, 2)),
            np.zeros((2, 2)),
            {"alpha": 1.0},
        )
