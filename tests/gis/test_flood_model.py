import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._temporal import RasterTimeline
from abm_auto.gis._flood_model import run_flood_evacuation, run_temporal_flood_evacuation


def _raster(data):
    return RasterSpace(RasterField(data=np.array(data, dtype=float),
                                   transform=Affine(100, 0, 0, 0, -100, 500),
                                   crs="EPSG:3857"))


def test_full_cut_strands_the_agent():
    gn = GeoNetwork.from_lines([LineString([(0, 0), (0, 400)])], crs="EPSG:3857", snap_tol=1.0)
    agent = gn.nearest_node(0, 0)
    safe = gn.nearest_node(0, 400)
    band = np.zeros((5, 5)); band[2, :] = 5.0   # full-width flood band
    flood = _raster(band)

    dry = run_flood_evacuation(gn, flood, threshold=100, safe_nodes=[safe], agent_nodes=[agent])
    wet = run_flood_evacuation(gn, flood, threshold=1, safe_nodes=[safe], agent_nodes=[agent])
    assert dry["stranded"] == 0 and dry["reached"] == 1
    assert wet["stranded"] == 1 and wet["n_flooded_edges"] >= 1


def test_partial_flood_forces_longer_detour():
    lines = [
        LineString([(0, 0), (0, 400)]),       # direct (x=0), crosses the flood blob
        LineString([(0, 0), (200, 0)]),
        LineString([(200, 0), (200, 400)]),   # detour (x=200), dry
        LineString([(200, 400), (0, 400)]),
    ]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    agent = gn.nearest_node(0, 0)
    safe = gn.nearest_node(0, 400)
    blob = np.zeros((5, 5)); blob[2, 0] = 5.0   # flood only near x=0, y~250
    flood = _raster(blob)

    dry = run_flood_evacuation(gn, flood, threshold=100, safe_nodes=[safe], agent_nodes=[agent])
    wet = run_flood_evacuation(gn, flood, threshold=1, safe_nodes=[safe], agent_nodes=[agent])
    assert dry["mean_detour_m"] == 400.0          # direct route
    assert wet["stranded"] == 0                   # detour exists
    assert wet["mean_detour_m"] > dry["mean_detour_m"]   # forced around the flood (800)


def test_temporal_flood_evacuation_reports_worst_and_recovery():
    lines = [
        LineString([(0, 0), (0, 400)]),
        LineString([(0, 0), (200, 0)]),
        LineString([(200, 0), (200, 400)]),
        LineString([(200, 400), (0, 400)]),
    ]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    agent = gn.nearest_node(0, 0)
    safe = gn.nearest_node(0, 400)
    agent_nodes = [agent]

    dry = np.zeros((5, 5))
    flooded = np.zeros((5, 5)); flooded[2, 0] = 5.0
    receded = np.zeros((5, 5))
    flood_timeline = RasterTimeline.from_frames([_raster(dry), _raster(flooded), _raster(receded)])

    result = run_temporal_flood_evacuation(
        gn,
        flood_timeline,
        threshold=1,
        safe_nodes=[safe],
        agent_nodes=agent_nodes,
    )

    assert [step["t"] for step in result["steps"]] == [0, 1, 2]
    assert result["n_steps"] == 3
    assert result["steps"][0]["mean_detour_m"] == 400.0
    assert result["steps"][1]["mean_detour_m"] >= 800.0
    assert result["steps"][2]["mean_detour_m"] == 400.0
    assert result["max_mean_detour_m"] == result["steps"][1]["mean_detour_m"]
    assert result["max_flooded_edges"] > 0
    assert result["worst_t"] == 1
    assert result["recovered"] is True
    assert agent_nodes == [agent]


def test_temporal_flood_evacuation_rejects_duck_typed_timeline():
    gn = GeoNetwork.from_lines([LineString([(0, 0), (0, 400)])], crs="EPSG:3857", snap_tol=1.0)
    agent = gn.nearest_node(0, 0)
    safe = gn.nearest_node(0, 400)
    flood = _raster(np.zeros((5, 5)))

    class FakeTimeline:
        n_steps = 3

        def at(self, _t):
            return flood

    with pytest.raises((TypeError, ValueError), match="RasterTimeline|timeline"):
        run_temporal_flood_evacuation(
            gn,
            FakeTimeline(),
            threshold=1,
            safe_nodes=[safe],
            agent_nodes=[agent],
        )


def test_temporal_flood_evacuation_revalidates_forged_timeline_frames():
    gn = GeoNetwork.from_lines([LineString([(0, 0), (0, 400)])], crs="EPSG:3857", snap_tol=1.0)
    agent = gn.nearest_node(0, 0)
    safe = gn.nearest_node(0, 400)
    dry = _raster(np.zeros((5, 5)))
    mismatched = RasterSpace(RasterField(data=np.zeros((3, 3), dtype=float),
                                         transform=Affine(100, 0, 0, 0, -100, 500),
                                         crs="EPSG:4326"))
    forged = RasterTimeline.__new__(RasterTimeline)
    object.__setattr__(forged, "_frames", (dry, mismatched))

    with pytest.raises(ValueError, match="CRS|shape|dimensions|transform|RasterTimeline"):
        run_temporal_flood_evacuation(
            gn,
            forged,
            threshold=1,
            safe_nodes=[safe],
            agent_nodes=[agent],
        )
