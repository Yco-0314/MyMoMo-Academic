from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._incident_gate import dynamic_incident_reroute_gate


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


def test_dynamic_incident_reroute_gate_passes_on_synthetic_case():
    geonet = _incident_detour_network()
    start = _node(geonet, 0, 0)
    bottleneck = _node(geonet, 100, 0)
    safe = _node(geonet, 200, 0)

    ok, desc = dynamic_incident_reroute_gate(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents=[{"t": 1, "edge": (bottleneck, safe), "closed": True}],
        n_steps=6,
        speed_m_per_tick=100,
    )

    assert ok, desc
    assert "moving-agent incident rerouting changes deterministic outcomes" in desc
    assert "does not prove real traffic flow or optimal incident management" in desc
    assert "total_reroutes=1" in desc


def test_dynamic_incident_reroute_gate_fails_without_incident_effect():
    geonet = _incident_detour_network()
    start = _node(geonet, 0, 0)
    safe = _node(geonet, 200, 0)

    ok, desc = dynamic_incident_reroute_gate(
        geonet,
        safe_nodes=[safe],
        agent_nodes=[start],
        incidents=[],
        n_steps=6,
        speed_m_per_tick=100,
    )

    assert not ok
    assert "no successful incident reroute" in desc
    assert "total_reroutes=0" in desc
    assert "reroute(n_agents=1, arrived=" in desc
    assert "static(n_agents=1, arrived=" in desc


def test_dynamic_incident_reroute_gate_fails_when_reroutes_do_not_improve_outcome(
    monkeypatch,
):
    def fake_run(*_args, reroute=True, **_kwargs):
        if reroute:
            return {
                "n_agents": 1,
                "arrived": 0,
                "stranded": 1,
                "mean_arrival_t": None,
                "total_reroutes": 1,
            }
        return {
            "n_agents": 1,
            "arrived": 0,
            "stranded": 1,
            "mean_arrival_t": None,
            "total_reroutes": 0,
        }

    monkeypatch.setattr(
        "abm_auto.gis._incident_gate.run_dynamic_incident_routing",
        fake_run,
    )

    ok, desc = dynamic_incident_reroute_gate(
        object(),
        safe_nodes=[],
        agent_nodes=[],
        incidents=[],
    )

    assert not ok
    assert "no outcome improvement" in desc
    assert "total_reroutes=1" in desc
    assert "reroute(n_agents=1, arrived=0, stranded=1" in desc
    assert "static(n_agents=1, arrived=0, stranded=1" in desc
