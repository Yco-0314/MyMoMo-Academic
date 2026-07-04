from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path

import pytest
from shapely.geometry import LineString

from abm_auto.gis._coupling import (
    terrain_aware_routing_gate,
    terrain_aware_shortest_path,
)
from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.terrain_bridge import load_terrain_bridge_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "docs/reproduce/terrain-bridge/example-manifest.json"


def _manifest_with_heightfield(tmp_path, text: str) -> dict:
    (tmp_path / "terrain.asc").write_text(text, encoding="utf-8")
    manifest = deepcopy(load_terrain_bridge_manifest(MANIFEST_PATH))
    manifest["terrain_source"]["path"] = "terrain.asc"
    manifest["terrain_source"]["sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    manifest["coordinate_frame"]["grid_shape"] = [3, 3]
    manifest["coordinate_frame"]["extent"] = [0.0, 0.0, 3.0, 3.0]
    return manifest


def _two_route_network() -> GeoNetwork:
    return GeoNetwork.from_lines(
        [
            LineString([(0.25, 0.25), (1.5, 1.5)]),
            LineString([(1.5, 1.5), (2.75, 2.75)]),
            LineString([(0.25, 0.25), (0.25, 2.75)]),
            LineString([(0.25, 2.75), (2.75, 2.75)]),
        ],
        crs="EPSG:3857",
        snap_tol=0.01,
    )


def _node(geonet: GeoNetwork, x: float, y: float):
    return geonet.nearest_node(x, y)


def test_terrain_aware_shortest_path_chooses_longer_flat_detour(tmp_path):
    geonet = _two_route_network()
    manifest = _manifest_with_heightfield(
        tmp_path,
        "0 0 0\n"
        "0 10 0\n"
        "0 0 0\n",
    )
    start = _node(geonet, 0.25, 0.25)
    center = _node(geonet, 1.5, 1.5)
    detour = _node(geonet, 0.25, 2.75)
    finish = _node(geonet, 2.75, 2.75)

    result = terrain_aware_shortest_path(
        geonet,
        manifest,
        start,
        finish,
        repo=tmp_path,
        n_samples=5,
        grade_weight=0.25,
    )

    assert result["length_path"] == [start, center, finish]
    assert result["terrain_path"] == [start, detour, finish]
    assert result["changed_path"] is True
    assert result["length_path_length_m"] < result["terrain_path_length_m"]
    assert result["terrain_path_cost"] < result["length_path_terrain_cost"]
    assert result["edge_costs"]


def test_terrain_aware_shortest_path_requires_existing_nodes(tmp_path):
    geonet = _two_route_network()
    manifest = _manifest_with_heightfield(tmp_path, "0 0 0\n0 0 0\n0 0 0\n")
    start = _node(geonet, 0.25, 0.25)

    with pytest.raises(ValueError, match="source node is not in GeoNetwork"):
        terrain_aware_shortest_path(geonet, manifest, "missing", start, repo=tmp_path)

    with pytest.raises(ValueError, match="target node is not in GeoNetwork"):
        terrain_aware_shortest_path(geonet, manifest, start, "missing", repo=tmp_path)


def test_terrain_aware_shortest_path_requires_distinct_source_and_target(tmp_path):
    geonet = _two_route_network()
    manifest = _manifest_with_heightfield(tmp_path, "0 0 0\n0 0 0\n0 0 0\n")
    start = _node(geonet, 0.25, 0.25)

    with pytest.raises(ValueError, match="source and target must be distinct"):
        terrain_aware_shortest_path(geonet, manifest, start, start, repo=tmp_path)


def test_terrain_aware_routing_gate_passes_when_terrain_changes_route_choice(tmp_path):
    geonet = _two_route_network()
    manifest = _manifest_with_heightfield(
        tmp_path,
        "0 0 0\n"
        "0 10 0\n"
        "0 0 0\n",
    )
    ok, message = terrain_aware_routing_gate(
        geonet,
        manifest,
        _node(geonet, 0.25, 0.25),
        _node(geonet, 2.75, 2.75),
        repo=tmp_path,
        n_samples=5,
        grade_weight=0.25,
    )

    assert ok is True
    assert "terrain changes shortest-path routing" in message
    assert "not traffic flow, vehicle dynamics, or 3D terrain physics" in message


def test_terrain_aware_routing_gate_fails_when_terrain_weight_has_no_effect(tmp_path):
    geonet = _two_route_network()
    manifest = _manifest_with_heightfield(
        tmp_path,
        "0 0 0\n"
        "0 10 0\n"
        "0 0 0\n",
    )
    ok, message = terrain_aware_routing_gate(
        geonet,
        manifest,
        _node(geonet, 0.25, 0.25),
        _node(geonet, 2.75, 2.75),
        repo=tmp_path,
        n_samples=5,
        grade_weight=0.0,
    )

    assert ok is False
    assert "terrain did not change shortest-path routing" in message
