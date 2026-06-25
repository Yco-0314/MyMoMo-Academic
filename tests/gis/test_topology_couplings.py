"""New coupling cells: line × polygon clip + polygon × polygon overlap.

Each test pair must PASS on real inputs AND FAIL on the trivial misuse — the
anti-fabrication discipline: a gate that always passes is no gate at all.
"""
from shapely.geometry import LineString, box

from abm_auto.gis._coupling import (
    line_polygon_gate,
    lines_in_polygon,
    polygon_overlap_areas,
    polygon_overlap_gate,
)


# ── line × polygon ──────────────────────────────────────────────────────────

POLY = box(0, 0, 10, 10)


def test_lines_in_polygon_clips_to_inside_length():
    fully_in = LineString([(2, 2), (8, 2)])              # length 6, all inside
    fully_out = LineString([(20, 0), (30, 0)])            # length 10, none inside
    crossing = LineString([(-5, 5), (5, 5)])              # length 10, half inside (x=0..5)
    assert lines_in_polygon([fully_in], POLY) == 6.0
    assert lines_in_polygon([fully_out], POLY) == 0.0
    assert lines_in_polygon([crossing], POLY) == 5.0


def test_line_polygon_gate_passes_when_inside_positive_and_outside_zero():
    inside = [LineString([(1, 1), (1, 9)])]               # length 8 inside
    outside = [LineString([(20, 0), (30, 0)])]            # entirely outside
    ok, desc = line_polygon_gate(inside, outside, POLY)
    assert ok, desc
    assert "inside=8" in desc


def test_line_polygon_gate_fails_when_inside_has_no_contribution():
    # swapped roles — "inside" arg is actually outside the polygon
    not_inside = [LineString([(20, 0), (30, 0)])]
    truly_outside = [LineString([(40, 0), (50, 0)])]
    ok, desc = line_polygon_gate(not_inside, truly_outside, POLY)
    assert not ok
    assert "non-positive" in desc


def test_line_polygon_gate_fails_when_supposedly_outside_actually_crosses():
    inside = [LineString([(1, 1), (1, 9)])]
    leaks_in = [LineString([(-5, 5), (5, 5)])]            # crosses into POLY
    ok, desc = line_polygon_gate(inside, leaks_in, POLY)
    assert not ok
    assert "non-zero" in desc


# ── polygon × polygon ───────────────────────────────────────────────────────


def _two_squares():
    return [box(0, 0, 10, 10), box(20, 0, 30, 10)]


def test_polygon_overlap_areas_self_overlap_is_full_self_area():
    polys = _two_squares()
    out = polygon_overlap_areas(polys, polys)
    # diagonal {(0,0), (1,1)} fully self-overlaps; off-diagonal is disjoint
    assert out[(0, 0)] == 100.0
    assert out[(1, 1)] == 100.0
    assert (0, 1) not in out and (1, 0) not in out


def test_polygon_overlap_areas_partial_overlap_is_intersection_area():
    a = [box(0, 0, 10, 10)]
    b = [box(5, 5, 15, 15)]                                # 5x5 overlap = 25
    out = polygon_overlap_areas(a, b)
    assert out == {(0, 0): 25.0}


def test_polygon_overlap_areas_empty_layers_return_empty():
    assert polygon_overlap_areas([], _two_squares()) == {}
    assert polygon_overlap_areas(_two_squares(), []) == {}


def test_polygon_overlap_gate_passes_on_real_layers():
    a = _two_squares()
    b = [box(5, 5, 15, 15)]                                # overlaps a[0] only
    ok, desc = polygon_overlap_gate(a, b)
    assert ok, desc
    assert "self=2 pairs" in desc and "a×b=1 pairs" in desc


def test_polygon_overlap_gate_fails_when_self_overlap_empty():
    # an empty layer can't self-overlap -> gate must fail (no rubber stamp)
    ok, desc = polygon_overlap_gate([], [])
    assert not ok
    assert "self-overlap empty" in desc
