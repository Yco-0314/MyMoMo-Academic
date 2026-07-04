import pytest
from shapely.geometry import LineString

from abm_auto.gis._dynamic_incident import (
    IncidentRoutingModel,
    run_dynamic_incident_routing,
)
from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._platform import DataCollector, StagedGISModel


_MISSING = object()


def _node(geonet, x, y):
    return geonet.nearest_node(x, y)


def _incident_detour_network():
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (200, 0)]),
            LineString([(0, 0), (0, 100)]),
            LineString([(0, 100), (200, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def _linear_incident_network():
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (100, 0)]),
            LineString([(100, 0), (200, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def _edge_key(u, v):
    return tuple(sorted((u, v), key=repr))


def test_two_tick_single_edge_arrival_history():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 200)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 200)

    result = run_dynamic_incident_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents=[],
        n_steps=2,
        speed_m_per_tick=100,
    )

    assert result["n_steps"] == 2
    assert result["n_agents"] == 1
    assert result["steps"][0]["moving"] == 1
    assert result["steps"][0]["arrived"] == 0
    assert result["steps"][0]["closed_edges"] == []
    assert result["steps"][1]["arrived"] == 1
    assert result["mean_arrival_t"] == 1
    assert result["max_closed_edges"] == 0
    assert result["agents"][0]["arrived"] is True
    assert result["agents"][0]["arrival_t"] == 1


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

    no_safe = run_dynamic_incident_routing(
        geonet,
        safe_nodes=[],
        agent_nodes=[start],
        incidents=[],
        n_steps=1,
    )
    unreachable = run_dynamic_incident_routing(
        geonet,
        safe_nodes=[disconnected_safe],
        agent_nodes=[start],
        incidents=[],
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
        run_dynamic_incident_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            incidents=[],
            speed_m_per_tick=0,
        )
    with pytest.raises(ValueError, match="speed_m_per_tick"):
        run_dynamic_incident_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            incidents=[],
            speed_m_per_tick=float("nan"),
        )
    with pytest.raises(ValueError, match="n_steps"):
        run_dynamic_incident_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            incidents=[],
            n_steps=0,
        )
    with pytest.raises(ValueError, match="n_steps"):
        run_dynamic_incident_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            incidents=[],
            n_steps=True,
        )


def test_node_reroute_takes_open_detour_while_static_route_waits():
    geonet = _incident_detour_network()
    start = _node(geonet, 0, 0)
    bottleneck = _node(geonet, 100, 0)
    safe = _node(geonet, 200, 0)
    closed_edge = _edge_key(bottleneck, safe)
    incident = {"t": 1, "edge": (bottleneck, safe), "closed": True}

    rerouted = run_dynamic_incident_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents=[incident],
        n_steps=8,
        speed_m_per_tick=100,
        reroute=True,
    )
    static = run_dynamic_incident_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents=[incident],
        n_steps=8,
        speed_m_per_tick=100,
        reroute=False,
    )

    assert rerouted["arrived"] == 1
    assert rerouted["stranded"] == 0
    assert rerouted["steps"][1]["closed_edges"] == [closed_edge]
    assert rerouted["steps"][1]["n_closed_edges"] == 1
    assert rerouted["steps"][1]["reroutes_this_step"] == 1
    assert rerouted["total_reroutes"] > 0
    assert rerouted["agents"][0]["arrival_t"] == 5
    assert rerouted["agents"][0]["route"] == []
    assert static["arrived"] == 0
    assert static["stranded"] == 1
    assert static["steps"][1]["waiting"] == 1
    assert static["steps"][-1]["waiting"] == 1
    assert static["agents"][0]["stranded_reason"] == "not_arrived"
    assert static["total_reroutes"] == 0


def test_failed_reroute_without_alternative_does_not_increment_counts():
    geonet = _linear_incident_network()
    start = _node(geonet, 0, 0)
    bottleneck = _node(geonet, 100, 0)
    safe = _node(geonet, 200, 0)

    result = run_dynamic_incident_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents=[{"t": 1, "edge": (bottleneck, safe), "closed": True}],
        n_steps=4,
        speed_m_per_tick=100,
        reroute=True,
    )

    assert result["arrived"] == 0
    assert result["stranded"] == 1
    assert result["total_reroutes"] == 0
    assert result["agents"][0]["reroutes"] == 0
    assert [step["reroutes_this_step"] for step in result["steps"]] == [0, 0, 0, 0]


def test_static_stale_route_waits_for_closed_edge_then_enters_after_reopen():
    geonet = _linear_incident_network()
    start = _node(geonet, 0, 0)
    bottleneck = _node(geonet, 100, 0)
    safe = _node(geonet, 200, 0)
    incident_edge = (bottleneck, safe)

    result = run_dynamic_incident_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents=[
            {"t": 1, "edge": incident_edge, "closed": True},
            {"t": 3, "edge": incident_edge, "closed": False},
        ],
        n_steps=4,
        speed_m_per_tick=100,
        reroute=False,
    )

    assert result["steps"][1]["waiting"] == 1
    assert result["steps"][1]["n_closed_edges"] == 1
    assert result["steps"][2]["waiting"] == 1
    assert result["steps"][2]["n_closed_edges"] == 1
    assert result["steps"][3]["n_closed_edges"] == 0
    assert result["steps"][3]["arrived"] == 1
    assert result["arrived"] == 1
    assert result["stranded"] == 0
    assert result["agents"][0]["arrival_t"] == 3


def test_agent_on_edge_becomes_stranded_when_edge_closes():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 200)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 200)

    result = run_dynamic_incident_routing(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents=[{"t": 1, "edge": (start, safe), "closed": True}],
        n_steps=2,
        speed_m_per_tick=75,
    )

    assert result["arrived"] == 0
    assert result["stranded"] == 1
    assert result["agents"][0]["stranded_reason"] == "incident_on_edge"
    assert result["steps"][0]["moving"] == 1
    assert result["steps"][1]["stranded"] == 1


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

    model = IncidentRoutingModel(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents={},
        speed_m_per_tick=50,
        reroute=True,
    )
    assert isinstance(model.reporter, DataCollector)
    assert isinstance(model, StagedGISModel)
    assert model.stages == (
        "strand_if_closed_on_edge",
        "plan_or_enter",
        "move_along_edge",
    )

    model.step()

    assert calls == ["strand_if_closed_on_edge", "plan_or_enter", "move_along_edge"]
    assert model.summaries == model.reporter.records
    assert model.summaries[0]["t"] == 0


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

    first_result = run_dynamic_incident_routing(
        first,
        safe_nodes=[_node(first, 200, 0)],
        agent_nodes=[_node(first, 0, 0)],
        incidents=[],
        n_steps=1,
        speed_m_per_tick=1,
    )
    second_result = run_dynamic_incident_routing(
        second,
        safe_nodes=[_node(second, 200, 0)],
        agent_nodes=[_node(second, 0, 0)],
        incidents=[],
        n_steps=1,
        speed_m_per_tick=1,
    )

    assert first_result["agents"][0]["edge"] == second_result["agents"][0]["edge"]
    assert first_result["agents"][0]["route"] == second_result["agents"][0]["route"]


def test_rejects_invalid_incident_events():
    geonet = GeoNetwork.from_lines(
        [LineString([(0, 0), (0, 100)])],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 0, 100)

    def run_with(event=_MISSING, incidents=_MISSING):
        if incidents is _MISSING:
            incidents = [event]
        return run_dynamic_incident_routing(
            geonet,
            safe_nodes=[safe],
            agent_nodes=[start],
            incidents=incidents,
            n_steps=1,
        )

    with pytest.raises(ValueError, match="incident.*mapping"):
        run_with(incidents=None)
    with pytest.raises(ValueError, match="incident event.*mapping"):
        run_with(("not", "a", "mapping"))
    with pytest.raises(ValueError, match="incident event t"):
        run_with({"edge": (start, safe), "closed": True})
    with pytest.raises(ValueError, match="incident event t"):
        run_with({"t": True, "edge": (start, safe), "closed": True})
    with pytest.raises(ValueError, match="incident event t"):
        run_with({"t": 1.5, "edge": (start, safe), "closed": True})
    with pytest.raises(ValueError, match="incident event t"):
        run_with({"t": -1, "edge": (start, safe), "closed": True})
    with pytest.raises(ValueError, match="edge"):
        run_with({"t": 0, "closed": True})
    with pytest.raises(ValueError, match="edge"):
        run_with({"t": 0, "edge": (start,), "closed": True})
    with pytest.raises(ValueError, match="edge"):
        run_with({"t": 0, "edge": (start, safe, start), "closed": True})
    with pytest.raises(ValueError, match="edge"):
        run_with({"t": 0, "edge": (start, "missing-node"), "closed": True})
    with pytest.raises(ValueError, match="edge"):
        run_with({"t": 0, "edge": 3, "closed": True})
    with pytest.raises(ValueError, match="closed"):
        run_with({"t": 0, "edge": (start, safe)})
    with pytest.raises(ValueError, match="closed"):
        run_with({"t": 0, "edge": (start, safe), "closed": 1})
