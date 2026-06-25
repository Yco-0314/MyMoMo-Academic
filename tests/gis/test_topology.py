"""DE-9IM vector topology primitives — pin each predicate on simple geometry."""
from shapely.geometry import LineString, Point, Polygon, box

from abm_auto.gis._coupling import (
    contains,
    crosses,
    features_containing,
    features_intersecting,
    intersects,
    overlaps,
    relate,
    touches,
    within,
)


SQUARE = box(0, 0, 10, 10)


def test_contains_and_within_are_inverses():
    p = Point(5, 5)
    assert contains(SQUARE, p) is True
    assert within(p, SQUARE) is True
    assert contains(p, SQUARE) is False


def test_intersects_includes_touching_and_crossing():
    a = box(0, 0, 5, 5)
    touching = box(5, 0, 10, 5)            # shares an edge
    crossing = box(3, 3, 7, 7)              # overlaps interior
    far = box(20, 20, 30, 30)
    assert intersects(a, touching) is True
    assert intersects(a, crossing) is True
    assert intersects(a, far) is False


def test_touches_distinguishes_boundary_from_interior_overlap():
    a = box(0, 0, 5, 5)
    boundary_share = box(5, 0, 10, 5)
    interior_share = box(3, 3, 7, 7)
    assert touches(a, boundary_share) is True
    assert touches(a, interior_share) is False        # interior overlap, not just touching


def test_crosses_for_lines():
    line1 = LineString([(0, 0), (10, 10)])
    line2 = LineString([(0, 10), (10, 0)])           # diagonals cross at (5, 5)
    parallel = LineString([(0, 1), (10, 11)])
    assert crosses(line1, line2) is True
    assert crosses(line1, parallel) is False


def test_overlaps_requires_same_dimension_interior_overlap():
    a = box(0, 0, 5, 5)
    b = box(3, 3, 7, 7)
    disjoint = box(20, 20, 30, 30)
    inside = box(1, 1, 2, 2)                          # fully within -> NOT 'overlaps' under DE-9IM
    assert overlaps(a, b) is True
    assert overlaps(a, disjoint) is False
    assert overlaps(a, inside) is False               # DE-9IM 'overlaps' excludes containment


def test_relate_returns_9_character_de9im_string():
    s = relate(SQUARE, Point(5, 5))
    assert isinstance(s, str) and len(s) == 9


def test_features_intersecting_uses_strtree_and_refines():
    grid = [box(i, j, i + 1, j + 1) for i in range(5) for j in range(5)]   # 25 unit cells
    query = box(0.5, 0.5, 2.5, 2.5)
    hits = features_intersecting(grid, query)
    # query touches a 4x4 swath of cells (cells at (0..2, 0..2)) — STRtree bbox query may
    # over-return; the refined check must return exactly the truly-intersecting ones.
    expected = {i * 5 + j for i in range(3) for j in range(3)}
    assert set(hits) == expected


def test_features_intersecting_empty_returns_empty():
    assert features_intersecting([], box(0, 0, 1, 1)) == []


def test_features_containing_filters_to_polygons_that_contain_point():
    grid = [box(i, j, i + 1, j + 1) for i in range(3) for j in range(3)]
    hits = features_containing(grid, Point(1.5, 1.5))
    assert len(hits) == 1
    assert grid[hits[0]].contains(Point(1.5, 1.5))
