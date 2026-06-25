"""Golden-master regression baseline for the refactor sweep.

Pins the EXACT current output of the behavior-sensitive GIS modules slated for
refactor — the dynamic routing models (#1 _routing_common extraction) and the STRtree
coupling operators (#2) — so any drift is caught immediately.

Discipline:
- A behavior-PRESERVING refactor (extract a shared helper) MUST keep this test green
  with the golden unchanged.
- A behavior-CHANGING fix (e.g. converging reroute logic) re-captures the golden in the
  SAME commit; the golden file's git diff is then the exact, reviewable record of what
  changed. Re-capture (self-contained):
  `python tests/gis/test_golden_regression.py > tests/gis/golden/routing_coupling.golden.json`.

Floats are rounded to 6 dp to guard against last-bit platform noise while still catching
real drift.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from affine import Affine
from shapely.geometry import LineString, Point, box

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._temporal import RasterTimeline
from abm_auto.gis._point_space import PointSpace
from abm_auto.gis._dynamic_congestion import run_dynamic_congestion_routing
from abm_auto.gis._dynamic_flood import run_dynamic_flood_evacuation
from abm_auto.gis._coupling import (
    point_risk_per_edge, polygon_overlap_areas,
    features_intersecting, features_containing,
)

_GOLDEN = json.loads(
    (Path(__file__).parent / "golden" / "routing_coupling.golden.json").read_text(encoding="utf-8")
)


def _norm(o, nd=6):
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {(k if isinstance(k, str) else str(k)): _norm(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_norm(v, nd) for v in o]
    return o


def _net():
    # diamond: direct (0,0)->(0,200) [200m] vs detour via (100,0)->(100,200) [400m]
    return GeoNetwork.from_lines([
        LineString([(0, 0), (0, 200)]),
        LineString([(0, 0), (100, 0)]),
        LineString([(100, 0), (100, 200)]),
        LineString([(100, 200), (0, 200)]),
    ], crs="EPSG:3857", snap_tol=1.0)


def _raster(d):
    return RasterSpace(RasterField(
        data=np.array(d, dtype=float),
        transform=Affine(100, 0, 0, 0, -100, 500), crs="EPSG:3857"))


def _build() -> dict:
    out = {}

    net = _net()
    start = net.nearest_node(0, 0); safe = net.nearest_node(0, 200)
    out["congestion"] = _norm(run_dynamic_congestion_routing(
        net, safe_nodes=[safe], agent_nodes=[start] * 5,
        n_steps=8, speed_m_per_tick=100.0, congestion_alpha=2.0, reroute=True))

    net2 = _net()
    s2 = net2.nearest_node(0, 0); g2 = net2.nearest_node(0, 200)
    dry = np.zeros((5, 5)); wet = np.zeros((5, 5)); wet[:, 0] = 5.0
    tl = RasterTimeline.from_frames([_raster(dry), _raster(wet), _raster(wet)])
    out["flood"] = _norm(run_dynamic_flood_evacuation(
        net2, tl, threshold=1.0, safe_nodes=[g2], agent_nodes=[s2] * 3,
        speed_m_per_tick=100.0, n_samples=8, reroute=True))

    net3 = _net()
    pts = PointSpace.from_coords([(5, 50), (5, 150), (95, 100), (50, 200)], crs="EPSG:3857")
    out["point_risk"] = _norm({str(k): v for k, v in point_risk_per_edge(net3, pts, radius=10.0).items()})

    a_polys = [box(0, 0, 10, 10), box(20, 20, 30, 30)]
    b_polys = [box(5, 5, 15, 15), box(100, 100, 110, 110)]
    out["polygon_overlap"] = _norm({str(k): v for k, v in polygon_overlap_areas(a_polys, b_polys).items()})

    feats = [box(0, 0, 10, 10), box(20, 20, 30, 30), box(5, 5, 25, 25)]
    out["features_intersecting"] = sorted(features_intersecting(feats, box(8, 8, 12, 12)))
    out["features_containing"] = sorted(features_containing(feats, Point(7, 7)))
    return out


def test_routing_and_coupling_golden():
    """Behavior baseline for #1 routing + #2 STRtree refactors. If this fails after a
    refactor that was supposed to be behavior-preserving, the refactor changed behavior —
    revert or fix. If the change was intentional, re-capture the golden in the same commit."""
    actual = json.loads(json.dumps(_build(), sort_keys=True, default=str))
    assert actual == _GOLDEN, (
        "GIS routing/coupling behavior drifted from the golden baseline. "
        "If this drift is INTENTIONAL, re-capture tests/gis/golden/routing_coupling.golden.json "
        "in the same commit so the diff documents the change."
    )


if __name__ == "__main__":
    # Self-contained re-capture: prints the golden JSON for the current behavior.
    #   python tests/gis/test_golden_regression.py > tests/gis/golden/routing_coupling.golden.json
    print(json.dumps(_build(), sort_keys=True, default=str))
