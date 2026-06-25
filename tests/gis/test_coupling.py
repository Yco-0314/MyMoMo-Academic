import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString, Polygon

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._point_space import PointSpace
from abm_auto.gis._polygon_space import PolygonSpace
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._coupling import (
    assign_points_to_polygons,
    flood_depth_per_edge,
    point_risk_per_edge,
    sample_raster_at_points,
)


def _flood():
    # 5x5 raster over world [0,500]x[0,500], 100 m cells; a flood band at row 2
    # (world y in [200,300]) with depth 5.0, dry elsewhere.
    data = np.zeros((5, 5))
    data[2, :] = 5.0
    transform = Affine(100, 0, 0, 0, -100, 500)
    return RasterSpace(RasterField(data=data, transform=transform, crs="EPSG:3857"))


def test_edge_crossing_flood_band_gets_band_depth():
    # L1 crosses the band (vertical through y=250); L2 is away (y=0).
    lines = [LineString([(250, 0), (250, 400)]), LineString([(0, 0), (400, 0)])]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    depths = flood_depth_per_edge(gn, _flood())

    a, b = gn.nearest_node(250, 0), gn.nearest_node(250, 400)
    c, d = gn.nearest_node(0, 0), gn.nearest_node(400, 0)
    assert depths[tuple(sorted((a, b)))] == 5.0   # crosses the flood band
    assert depths[tuple(sorted((c, d)))] == 0.0   # dry


def test_out_of_bounds_is_dry():
    lines = [LineString([(900, 900), (1000, 1000)])]   # entirely outside the raster
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    depths = flood_depth_per_edge(gn, _flood())
    assert all(v == 0.0 for v in depths.values())


def test_sample_raster_at_points_reads_known_cells_and_oob_is_zero():
    data = np.array([[1.0, 2.0, 3.0],
                     [4.0, 5.0, 6.0]])
    raster = RasterSpace(RasterField(data=data,
                                     transform=Affine(10, 0, 0, 0, -10, 20),
                                     crs="EPSG:3857"))
    points = PointSpace.from_coords([
        (5, 15),
        (25, 5),
        (500, 500),
    ], crs="EPSG:3857")

    values = sample_raster_at_points(raster, points)

    assert values == {0: 1.0, 1: 6.0, 2: 0.0}


def test_point_risk_per_edge_counts_only_near_points():
    lines = [
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (100, 100)]),
    ]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    points = PointSpace.from_coords([(50, 5), (1000, 1000)], crs="EPSG:3857")

    risk = point_risk_per_edge(gn, points, radius=10.0)

    a = gn.nearest_node(0, 0)
    b = gn.nearest_node(100, 0)
    assert risk[tuple(sorted((a, b)))] == 1
    assert sum(risk.values()) == 1


def test_point_risk_per_edge_rejects_negative_radius():
    lines = [LineString([(0, 0), (100, 0)])]
    gn = GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=1.0)
    points = PointSpace.from_coords([(50, 5)], crs="EPSG:3857")

    with pytest.raises(ValueError, match="radius"):
        point_risk_per_edge(gn, points, radius=-1.0)


def test_assign_points_to_polygons_is_stable_with_explicit_ids():
    west = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    east = Polygon([(10, 0), (20, 0), (20, 10), (10, 10)])
    points = PointSpace.from_coords([(5, 5), (15, 5), (50, 50)], crs="EPSG:3857")
    normal = PolygonSpace.from_polygons(
        [west, east],
        crs="EPSG:3857",
        ids=["west", "east"],
    )
    swapped = PolygonSpace.from_polygons(
        [east, west],
        crs="EPSG:3857",
        ids=["east", "west"],
    )
    expected = {"west": [0], "east": [1]}

    assert assign_points_to_polygons(points, normal) == expected
    assert assign_points_to_polygons(points, swapped) == expected
