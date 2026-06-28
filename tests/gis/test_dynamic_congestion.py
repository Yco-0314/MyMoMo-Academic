import pytest
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._platform import DataCollector, StagedGISModel
from abm_auto.gis._dynamic_congestion import (
    CongestionModel,
    _congested_edge_costs,
    _edge_key,
    run_dynamic_congestion_routing,
)


def _node(geonet, x, y):
    return geonet.nearest_node(x, y)


def test_two_tick_single_edge_arrival_history():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 200)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 200)

    result = run_dynamic_congestion_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        n_steps=2,
        speed_m_per_tick=100,
    )

    assert result["n_steps"] == 2
    assert result["n_agents"] == 1
    assert result["steps"][0]["moving"] == 1
    assert result["steps"][0]["arrived"] == 0
    assert result["steps"][1]["arrived"] == 1
    assert result["mean_arrival_t"] == 1
    assert result["agents"][0]["arrived"] is True
    assert result["agents"][0]["arrival_t"] == 1


def test_speed_does_not_carry_across_edge_boundaries():
    single_edge = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 200)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    split_edges = GeoNetwork.from_lines(
        [
            LineString([(0, 0), (0, 100)]),
            LineString([(0, 100), (0, 200)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )

    single = run_dynamic_congestion_routing(
        single_edge,
        safe_nodes=[_node(single_edge, 0, 200)],
        agent_nodes=[_node(single_edge, 0, 0)],
        n_steps=2,
        speed_m_per_tick=200,
    )
    split = run_dynamic_congestion_routing(
        split_edges,
        safe_nodes=[_node(split_edges, 0, 200)],
        agent_nodes=[_node(split_edges, 0, 0)],
        n_steps=2,
        speed_m_per_tick=200,
    )

    assert single["agents"][0]["arrival_t"] == 0
    assert split["agents"][0]["arrival_t"] == 1
    assert split["mean_arrival_t"] == 1


def test_missing_or_unreachable_safe_nodes_end_not_arrived():
    geonet = GeoNetwork.from_lines(
        [
            LineString([(0, 0), (0, 100)]),
            LineString([(300, 0), (300, 100)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    disconnected_safe = _node(geonet, 300, 100)

    no_safe = run_dynamic_congestion_routing(
        geonet,
        safe_nodes=[],
        agent_nodes=[start],
        n_steps=1,
    )
    unreachable = run_dynamic_congestion_routing(
        geonet,
        safe_nodes=[disconnected_safe],
        agent_nodes=[start],
        n_steps=1,
    )

    assert no_safe["agents"][0]["stranded_reason"] == "not_arrived"
    assert unreachable["agents"][0]["stranded_reason"] == "not_arrived"
    assert no_safe["stranded"] == 1
    assert unreachable["stranded"] == 1


def test_rejects_invalid_runtime_parameters():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 100)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 100)

    with pytest.raises(ValueError, match="speed_m_per_tick"):
        run_dynamic_congestion_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            speed_m_per_tick=0,
        )
    with pytest.raises(ValueError, match="n_steps"):
        run_dynamic_congestion_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            n_steps=0,
        )
    with pytest.raises(ValueError, match="n_steps"):
        run_dynamic_congestion_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            n_steps=True,
        )
    with pytest.raises(ValueError, match="congestion_alpha"):
        run_dynamic_congestion_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            congestion_alpha=-0.1,
        )


def test_rejects_non_finite_runtime_parameters():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 100)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 100)

    with pytest.raises(ValueError, match="speed_m_per_tick"):
        run_dynamic_congestion_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            speed_m_per_tick=float("nan"),
        )
    with pytest.raises(ValueError, match="speed_m_per_tick"):
        run_dynamic_congestion_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            speed_m_per_tick=float("inf"),
        )
    with pytest.raises(ValueError, match="congestion_alpha"):
        run_dynamic_congestion_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            congestion_alpha=float("nan"),
        )
    with pytest.raises(ValueError, match="congestion_alpha"):
        run_dynamic_congestion_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            congestion_alpha=float("inf"),
        )


def test_public_agent_state_excludes_internal_planning_flag():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 100)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 100)

    result = run_dynamic_congestion_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        n_steps=1,
        speed_m_per_tick=100,
    )

    assert "planned_once" not in result["agents"][0]


def test_production_adapter_uses_platform_stages_and_reporter(monkeypatch):
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 100)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 100)
    calls = []

    def spy_do(self, method_name, *args, **kwargs):
        calls.append(method_name)
        for agent in self.ordered():
            getattr(agent, method_name)(*args, **kwargs)

    monkeypatch.setattr("abm_auto.gis._platform.AgentSet.do", spy_do, raising=False)

    model = CongestionModel(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        speed_m_per_tick=50,
        congestion_alpha=1.0,
        reroute=True,
    )
    assert isinstance(model.reporter, DataCollector)
    assert isinstance(model, StagedGISModel)
    assert model.stages == ("plan_or_arrive", "enter_next_edge", "move_along_edge")

    model.step()

    assert calls == ["plan_or_arrive", "enter_next_edge", "move_along_edge"]
    assert model.reporter.records == model.summaries
    assert model.summaries[0]["t"] == 0


def test_result_max_edge_load_is_derived_from_collected_series():
    # Two agents share the single edge for a tick, so the collected per-tick
    # `max_edge_load` series peaks at 2; the run summary's `max_edge_load` is the
    # peak of that collected series (it flows through the RunReporter seam, it is
    # not tracked as separate model state).
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 300)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 300)

    model = CongestionModel(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start, start],
        speed_m_per_tick=100,
        congestion_alpha=0.0,
        reroute=True,
    )
    for _ in range(4):
        model.step()
    result = model.result(4)

    assert not hasattr(model, "max_edge_load")          # no separate tracked state
    assert result["steps"] is model.reporter.records    # steps block IS the series
    assert result["max_edge_load"] == max(
        model.reporter.series("max_edge_load")
    )
    assert result["max_edge_load"] == 2


def _diamond_network():
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (200, 0)]),
            LineString([(200, 0), (300, 0)]),
            LineString([(0, 0), (100, -100)]),
            LineString([(100, -100), (200, -100)]),
            LineString([(200, -100), (300, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def test_previous_edge_load_increases_congested_cost():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 100)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 100)
    key = _edge_key(start, safe)

    costs = _congested_edge_costs(
        geonet.graph,
        previous_loads={key: 3},
        congestion_alpha=1.5,
    )

    assert costs[key] == pytest.approx(100 * (1 + 1.5 * 2))


def test_reroute_enabled_agents_can_switch_to_lower_congested_cost_detour():
    geonet = _diamond_network()
    leader = _node(geonet, 100, 0)
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 300, 0)

    rerouted = run_dynamic_congestion_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[leader, leader, start],
        n_steps=8,
        speed_m_per_tick=100,
        congestion_alpha=3.0,
        reroute=True,
    )
    static = run_dynamic_congestion_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[leader, leader, start],
        n_steps=8,
        speed_m_per_tick=100,
        congestion_alpha=3.0,
        reroute=False,
    )

    assert rerouted["total_reroutes"] > 0
    assert any(step["reroutes_this_step"] > 0 for step in rerouted["steps"])
    assert rerouted["arrived"] > static["arrived"]
    assert rerouted["stranded"] < static["stranded"]
    assert static["mean_arrival_t"] is None
    assert static["total_reroutes"] == 0


def test_equal_cost_routes_are_stable_across_line_insertion_order():
    top_path = [
        LineString([(0, 0), (100, 100)]),
        LineString([(100, 100), (200, 0)]),
    ]
    bottom_path = [
        LineString([(0, 0), (100, -100)]),
        LineString([(100, -100), (200, 0)]),
    ]

    first = GeoNetwork.from_lines(top_path + bottom_path, crs="EPSG:3857", snap_tol=1.0)
    second = GeoNetwork.from_lines(bottom_path + top_path, crs="EPSG:3857", snap_tol=1.0)

    first_result = run_dynamic_congestion_routing(
        first,
        safe_nodes=[_node(first, 200, 0)],
        agent_nodes=[_node(first, 0, 0)],
        n_steps=1,
        speed_m_per_tick=1,
    )
    second_result = run_dynamic_congestion_routing(
        second,
        safe_nodes=[_node(second, 200, 0)],
        agent_nodes=[_node(second, 0, 0)],
        n_steps=1,
        speed_m_per_tick=1,
    )

    assert first_result["agents"][0]["edge"] == second_result["agents"][0]["edge"]
    assert first_result["agents"][0]["route"] == second_result["agents"][0]["route"]
