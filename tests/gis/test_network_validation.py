import math

import pytest

from abm_auto.gis._network_validation import (
    ObservedNetworkTarget,
    evaluate_network_params,
    grid_search_network_calibration,
    network_edge_loss,
    network_edge_metrics,
    network_observed_validation_gate,
    network_validation_gate,
    observed_network_from_mapping,
)


def test_observed_network_target_normalizes_undirected_edge_keys_and_provenance():
    observed = observed_network_from_mapping(
        {("B", "A"): 10, ("A", "C"): 2},
        source="local traffic count fixture",
        dataset="test-counts",
        metric="edge_load",
    )

    assert isinstance(observed, ObservedNetworkTarget)
    assert observed.edge_values == {("A", "B"): 10.0, ("A", "C"): 2.0}
    assert observed.provenance() == {
        "source": "local traffic count fixture",
        "dataset": "test-counts",
        "metric": "edge_load",
        "n_edges": 2,
    }


def test_observed_network_target_normalizes_tuple_node_ids_stably():
    observed = observed_network_from_mapping(
        {((1, 0), (0, 0)): 5},
        source="source",
        dataset="dataset",
    )

    assert observed.edge_values == {((0, 0), (1, 0)): 5.0}


def test_observed_network_target_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="edge_values must be a non-empty mapping"):
        observed_network_from_mapping({}, source="source", dataset="dataset")
    with pytest.raises(ValueError, match="source must be a non-empty string"):
        observed_network_from_mapping({("A", "B"): 1}, source="", dataset="dataset")
    with pytest.raises(ValueError, match="edge value must be a finite number"):
        observed_network_from_mapping({("A", "B"): float("nan")}, source="source", dataset="dataset")
    with pytest.raises(ValueError, match="edge keys must contain exactly two nodes"):
        observed_network_from_mapping({("A", "B", "C"): 1}, source="source", dataset="dataset")


def test_network_edge_metrics_perfect_match_has_zero_loss():
    observed = observed_network_from_mapping(
        {("A", "B"): 10, ("B", "C"): 3},
        source="source",
        dataset="dataset",
    )
    simulated = {("B", "A"): 10, ("C", "B"): 3, ("A", "C"): 99}

    metrics = network_edge_metrics(simulated, observed)

    assert metrics["observed_total"] == 2
    assert metrics["matched_edges"] == 2
    assert metrics["missing_edges"] == []
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["relative_rmse"] == 0.0
    assert metrics["bias"] == 0.0
    assert metrics["top_edge_match"] is True
    assert network_edge_loss(metrics) == 0.0


def test_network_edge_metrics_shifted_values_have_positive_error():
    observed = observed_network_from_mapping(
        {("A", "B"): 10, ("B", "C"): 2},
        source="source",
        dataset="dataset",
    )
    simulated = {("A", "B"): 7, ("B", "C"): 5}

    metrics = network_edge_metrics(simulated, observed)

    assert metrics["mae"] == 3.0
    assert metrics["rmse"] == 3.0
    assert metrics["relative_rmse"] == pytest.approx(3.0 / 6.0)
    assert metrics["bias"] == 0.0
    assert network_edge_loss(metrics) > 0.0


def test_network_edge_metrics_reports_missing_observed_edges():
    observed = observed_network_from_mapping(
        {("A", "B"): 10, ("B", "C"): 2},
        source="source",
        dataset="dataset",
    )

    metrics = network_edge_metrics({("A", "B"): 10}, observed)

    assert metrics["observed_total"] == 2
    assert metrics["matched_edges"] == 1
    assert metrics["missing_edges"] == [("B", "C")]
    assert math.isfinite(network_edge_loss(metrics))


def test_network_validation_gate_passes_matching_edge_values():
    observed = observed_network_from_mapping(
        {("A", "B"): 10, ("B", "C"): 3},
        source="source",
        dataset="dataset",
    )

    ok, desc = network_validation_gate({("A", "B"): 10, ("B", "C"): 3}, observed)

    assert ok, desc
    assert "network edge values match observed target" in desc


def test_network_validation_gate_fails_missing_observed_edges():
    observed = observed_network_from_mapping(
        {("A", "B"): 10, ("B", "C"): 3},
        source="source",
        dataset="dataset",
    )

    ok, desc = network_validation_gate({("A", "B"): 10}, observed)

    assert not ok
    assert "missing observed edges" in desc


def test_evaluate_network_params_returns_loss_metrics_and_copied_params():
    observed = observed_network_from_mapping(
        {("A", "B"): 10, ("B", "C"): 2},
        source="source",
        dataset="dataset",
    )
    params = {"main": 10.0, "side": 2.0}

    result = evaluate_network_params(
        lambda p: {("A", "B"): p["main"], ("B", "C"): p["side"]},
        observed,
        params,
    )
    params["main"] = 0.0

    assert result["params"] == {"main": 10.0, "side": 2.0}
    assert result["loss"] == 0.0
    assert result["metrics"]["rmse"] == 0.0
    assert result["simulated_edge_values"] == {("A", "B"): 10.0, ("B", "C"): 2.0}


def test_grid_search_network_calibration_selects_lower_loss_params():
    observed = observed_network_from_mapping(
        {("A", "B"): 10, ("B", "C"): 2},
        source="source",
        dataset="dataset",
    )

    def simulator(params):
        return {("A", "B"): params["main"], ("B", "C"): params["side"]}

    result = grid_search_network_calibration(
        simulator,
        observed,
        {"main": [5.0, 10.0], "side": [2.0, 8.0]},
    )

    assert result["ok"] is True
    assert result["best_params"] == {"main": 10.0, "side": 2.0}
    assert result["best_loss"] == 0.0
    assert result["n_evaluations"] == 4
    assert [e["rank"] for e in result["evaluations"]] == [0, 1, 2, 3]


def test_network_observed_validation_gate_passes_with_boundary_text():
    ok, desc = network_observed_validation_gate()

    assert ok, desc
    assert "network observed validation selected lower-loss edge parameters" in desc
    assert "not traffic-count ingestion" in desc
    assert "not traffic-flow calibration" in desc
