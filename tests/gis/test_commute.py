"""Mechanism test: flexitime (spreading departures) must reduce peak congestion,
hence lower mean commute time and total CO2. (The reproduction's core claim P1.)"""
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._commute import flexitime_experiment


def _bottleneck_net():
    # a chain 0-1-2-...-6 (100 m edges): every commuter shares the middle edges
    pts = [(i * 100.0, 0.0) for i in range(7)]
    lines = [LineString([pts[i], pts[i + 1]]) for i in range(6)]
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)


def test_flexitime_lowers_mean_time_and_co2():
    gn = _bottleneck_net()
    nodes = list(gn.graph.nodes)
    a = gn.nearest_node(0, 0)
    z = gn.nearest_node(600, 0)
    od = [(a, z)] * 120   # 120 commuters all crossing the same corridor

    res = flexitime_experiment(gn, od, spreads=[0.0, 0.5, 1.0], n_slots=12, seed=1)
    no_flex, full_flex = res[0], res[-1]

    # spreading departures cuts congestion -> lower mean time and total CO2
    assert full_flex["mean_time"] < no_flex["mean_time"], res
    assert full_flex["total_co2"] < no_flex["total_co2"], res


def test_monotone_diminishing_returns():
    gn = _bottleneck_net()
    a, z = gn.nearest_node(0, 0), gn.nearest_node(600, 0)
    od = [(a, z)] * 120
    res = flexitime_experiment(gn, od, spreads=[0.0, 0.25, 0.5, 0.75, 1.0], seed=1)
    times = [r["mean_time"] for r in res]
    # non-increasing as flexitime increases
    assert all(times[i] >= times[i + 1] - 1e-9 for i in range(len(times) - 1)), times
