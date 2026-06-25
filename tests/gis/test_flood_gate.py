import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._temporal import RasterTimeline
from abm_auto.gis._flood_gate import (
    dynamic_flood_reroute_gate,
    flood_gate,
    temporal_flood_gate,
)


def _raster(data):
    return RasterSpace(RasterField(data=np.array(data, dtype=float),
                                   transform=Affine(100, 0, 0, 0, -100, 500), crs="EPSG:3857"))


def _timeline(*frames):
    return RasterTimeline.from_frames([_raster(frame) for frame in frames])


def _node(geonet, x, y):
    return geonet.nearest_node(x, y)


def _detour_net():
    lines = [LineString([(0, 0), (0, 400)]), LineString([(0, 0), (200, 0)]),
             LineString([(200, 0), (200, 400)]), LineString([(200, 400), (0, 400)])]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    return gn, gn.nearest_node(0, 0), gn.nearest_node(0, 400)


def _dynamic_detour_net():
    lines = [
        LineString([(0, 0), (0, 100)]),
        LineString([(0, 100), (0, 200)]),
        LineString([(0, 200), (200, 200)]),
        LineString([(0, 100), (300, 100)]),
        LineString([(300, 100), (300, 200)]),
        LineString([(300, 200), (200, 200)]),
    ]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    return gn, _node(gn, 0, 0), _node(gn, 200, 200)


def test_gate_passes_when_flood_worsens_evacuation():
    gn, agent, safe = _detour_net()
    blob = np.zeros((5, 5)); blob[2, 0] = 5.0
    ok, desc = flood_gate(gn, _raster(blob), [safe], [agent], thresholds=[100, 1])
    assert ok, desc          # detour grows 400 -> 800 as the flood activates


def test_gate_fails_on_no_effect():
    gn, agent, safe = _detour_net()
    dry = np.zeros((5, 5))   # no flood at all
    ok, _ = flood_gate(gn, _raster(dry), [safe], [agent], thresholds=[100, 1])
    assert not ok            # flooding changes nothing -> fail


def test_temporal_gate_passes_when_flood_worsens_then_recedes():
    gn, agent, safe = _detour_net()
    dry = np.zeros((5, 5))
    flooded = np.zeros((5, 5)); flooded[2, 0] = 5.0
    receded = np.zeros((5, 5))
    flood_timeline = RasterTimeline.from_frames([_raster(dry), _raster(flooded), _raster(receded)])

    ok, desc = temporal_flood_gate(gn, flood_timeline, [safe], [agent], threshold=1)

    assert ok, desc
    assert "worse" in desc
    assert "recovered" in desc or "improved" in desc


def test_temporal_gate_rejects_duck_typed_timeline():
    gn, agent, safe = _detour_net()
    flood = _raster(np.zeros((5, 5)))

    class FakeTimeline:
        n_steps = 3

        def at(self, _t):
            return flood

    with pytest.raises((TypeError, ValueError), match="RasterTimeline|timeline"):
        temporal_flood_gate(gn, FakeTimeline(), [safe], [agent], threshold=1)


def test_temporal_gate_fails_on_no_effect_timeline():
    gn, agent, safe = _detour_net()
    dry = np.zeros((5, 5))
    flood_timeline = RasterTimeline.from_frames([_raster(dry), _raster(dry), _raster(dry)])

    ok, desc = temporal_flood_gate(gn, flood_timeline, [safe], [agent], threshold=1)

    assert not ok
    assert "no effect" in desc or "did not worsen" in desc


def test_temporal_gate_fails_when_flood_does_not_recover():
    gn, agent, safe = _detour_net()
    dry = np.zeros((5, 5))
    flooded = np.zeros((5, 5)); flooded[2, 0] = 5.0
    flood_timeline = RasterTimeline.from_frames([_raster(dry), _raster(flooded), _raster(flooded)])

    ok, desc = temporal_flood_gate(gn, flood_timeline, [safe], [agent], threshold=1)

    assert not ok
    assert "did not improve" in desc
    assert "final" in desc


def test_temporal_gate_fails_with_too_few_frames():
    gn, agent, safe = _detour_net()
    dry = np.zeros((5, 5))
    flood_timeline = RasterTimeline.from_frames([_raster(dry), _raster(dry)])

    ok, desc = temporal_flood_gate(gn, flood_timeline, [safe], [agent], threshold=1)

    assert not ok
    assert "at least 3" in desc or "timeline" in desc


def test_dynamic_reroute_gate_passes_when_moving_agent_uses_dry_detour():
    gn, agent, safe = _dynamic_detour_net()
    dry = np.zeros((5, 5))
    flooded_direct = np.zeros((5, 5)); flooded_direct[3, 0] = 5.0
    flood_timeline = _timeline(
        dry,
        flooded_direct,
        flooded_direct,
        flooded_direct,
        flooded_direct,
        flooded_direct,
    )

    ok, desc = dynamic_flood_reroute_gate(gn, flood_timeline, [safe], [agent], threshold=1)

    assert ok, desc
    assert "moving-agent rerouting" in desc
    assert "behavioral impact" in desc
    assert "does not prove" in desc
    assert "real traffic flow" in desc
    assert "emergency evacuation optimality" in desc


def test_dynamic_reroute_gate_fails_when_timeline_has_no_reroute_effect():
    gn, agent, safe = _dynamic_detour_net()
    dry = np.zeros((5, 5))
    flood_timeline = _timeline(dry, dry, dry, dry)

    ok, desc = dynamic_flood_reroute_gate(gn, flood_timeline, [safe], [agent], threshold=1)

    assert not ok
    assert "total_reroutes=0" in desc
    assert "reroute(n_agents=1, arrived=" in desc
    assert "static(n_agents=1, arrived=" in desc


def test_dynamic_reroute_gate_fails_when_reroute_has_no_alternative_or_improvement():
    gn = GeoNetwork.from_lines(
        [
            LineString([(0, 0), (0, 100)]),
            LineString([(0, 100), (0, 200)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )
    agent = _node(gn, 0, 0)
    safe = _node(gn, 0, 200)
    dry = np.zeros((5, 5))
    flooded_direct = np.zeros((5, 5)); flooded_direct[3, 0] = 5.0
    flood_timeline = _timeline(dry, flooded_direct)

    ok, desc = dynamic_flood_reroute_gate(gn, flood_timeline, [safe], [agent], threshold=1)

    assert not ok
    assert "total_reroutes=0" in desc
    assert "reroute(n_agents=1, arrived=0" in desc
    assert "static(n_agents=1, arrived=0" in desc


def test_dynamic_reroute_gate_fails_when_reroutes_do_not_improve_outcome(monkeypatch):
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

    monkeypatch.setattr("abm_auto.gis._flood_gate.run_dynamic_flood_evacuation", fake_run)

    ok, desc = dynamic_flood_reroute_gate(object(), object(), [], [], threshold=1)

    assert not ok
    assert "no outcome improvement" in desc
    assert "total_reroutes=1" in desc


def test_dynamic_reroute_gate_materializes_iterable_inputs_for_both_runs():
    gn, agent, safe = _dynamic_detour_net()
    dry = np.zeros((5, 5))
    flooded_direct = np.zeros((5, 5)); flooded_direct[3, 0] = 5.0
    flood_timeline = _timeline(
        dry,
        flooded_direct,
        flooded_direct,
        flooded_direct,
        flooded_direct,
        flooded_direct,
    )

    ok, desc = dynamic_flood_reroute_gate(
        gn,
        flood_timeline,
        (node for node in [safe]),
        (node for node in [agent]),
        threshold=1,
    )

    assert ok, desc
    assert "n_agents=1" in desc
    assert "static(n_agents=1, arrived=0, stranded=1" in desc
