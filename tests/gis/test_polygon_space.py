import pytest
from shapely.geometry import LineString, Polygon

from abm_auto.gis._point_space import PointSpace
from abm_auto.gis._polygon_space import PolygonSpace


def _regions():
    west = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    east = Polygon([(10, 0), (20, 0), (20, 10), (10, 10)])
    return [west, east]


def test_contains_point_returns_explicit_polygon_id_or_none():
    ps = PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=["west", "east"])

    assert ps.n_polygons == 2
    assert ps.polygon_id_at(0) == "west"
    assert ps.contains_point(5, 5) == "west"
    assert ps.contains_point(15, 5) == "east"
    assert ps.contains_point(50, 50) is None


def test_rejects_duplicate_polygon_ids():
    with pytest.raises(ValueError, match="unique"):
        PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=["same", "same"])


def test_rejects_unhashable_polygon_ids():
    with pytest.raises(ValueError, match="hashable"):
        PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=[["west"], ["east"]])


def test_rejects_none_polygon_id():
    with pytest.raises(ValueError, match="None"):
        PolygonSpace.from_polygons([_regions()[0]], crs="EPSG:3857", ids=[None])


def test_rejects_nan_polygon_id():
    with pytest.raises(ValueError, match="ids"):
        PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=[float("nan"), "east"])


def test_rejects_duplicate_nan_polygon_ids():
    with pytest.raises(ValueError, match="ids"):
        PolygonSpace.from_polygons(
            _regions(), crs="EPSG:3857", ids=[float("nan"), float("nan")]
        )


def test_rejects_non_polygon_geometry():
    line = LineString([(0, 0), (10, 10)])

    with pytest.raises(ValueError, match="Polygon"):
        PolygonSpace.from_polygons([line], crs="EPSG:3857", ids=["line"])


def test_rejects_empty_polygon_geometry():
    with pytest.raises(ValueError, match="empty"):
        PolygonSpace.from_polygons([Polygon()], crs="EPSG:3857", ids=["empty"])


def test_polygon_id_at_rejects_negative_or_out_of_range_index():
    ps = PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=["west", "east"])

    with pytest.raises(ValueError, match="index"):
        ps.polygon_id_at(-1)
    with pytest.raises(ValueError, match="index"):
        ps.polygon_id_at(2)


@pytest.mark.parametrize("index", [0.0, "0", True])
def test_polygon_id_at_rejects_non_integral_or_bool_index(index):
    ps = PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=["west", "east"])

    with pytest.raises(ValueError, match="index"):
        ps.polygon_id_at(index)


def test_shared_boundary_chooses_lower_index_polygon_id():
    ps = PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=["west", "east"])

    assert ps.contains_point(10, 5) == "west"


def test_assign_points_groups_points_and_omits_outside():
    polygons = PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=["west", "east"])
    points = PointSpace.from_coords([(5, 5), (15, 5), (50, 50)], crs="EPSG:3857")

    assert polygons.assign_points(points) == {"west": [0], "east": [1]}


def test_adjacent_regions_reports_touching_polygons():
    ps = PolygonSpace.from_polygons(_regions(), crs="EPSG:3857", ids=["west", "east"])

    assert ps.adjacent_regions() == {("west", "east")}


def test_overlapping_polygons_choose_lowest_index():
    a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    b = Polygon([(5, 0), (15, 0), (15, 10), (5, 10)])
    ps = PolygonSpace.from_polygons([a, b], crs="EPSG:3857", ids=["first", "second"])

    assert ps.contains_point(7, 5) == "first"
