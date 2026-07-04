from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from shapely.geometry import LineString

from abm_auto.gis._coupling import (
    terrain_cost_per_edge,
    terrain_elevation_delta_per_edge,
    terrain_grade_proxy_per_edge,
    terrain_network_coupling_gate,
)
from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.terrain_bridge import load_terrain_bridge_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "docs/reproduce/terrain-bridge/example-manifest.json"


def _manifest() -> dict:
    return load_terrain_bridge_manifest(MANIFEST_PATH)


def _mixed_network() -> GeoNetwork:
    lines = [
        LineString([(0.25, 0.25), (0.75, 0.25)]),
        LineString([(0.25, 0.25), (2.75, 2.75)]),
    ]
    return GeoNetwork.from_lines(lines, crs="EPSG:3857", snap_tol=0.01)


def _edge_key(geonet: GeoNetwork, a: tuple[float, float], b: tuple[float, float]) -> tuple:
    u = geonet.nearest_node(*a)
    v = geonet.nearest_node(*b)
    return tuple(sorted((u, v), key=repr))


def test_terrain_elevation_delta_samples_edge_heightfield():
    geonet = _mixed_network()

    deltas = terrain_elevation_delta_per_edge(
        geonet,
        _manifest(),
        repo=REPO_ROOT,
        n_samples=5,
    )

    flat_edge = _edge_key(geonet, (0.25, 0.25), (0.75, 0.25))
    uphill_edge = _edge_key(geonet, (0.25, 0.25), (2.75, 2.75))
    assert deltas[flat_edge] == 0.0
    assert deltas[uphill_edge] == 4.0


def test_grade_proxy_is_zero_for_flat_edge_and_positive_for_uphill_edge():
    geonet = _mixed_network()

    grades = terrain_grade_proxy_per_edge(geonet, _manifest(), repo=REPO_ROOT, n_samples=5)

    flat_edge = _edge_key(geonet, (0.25, 0.25), (0.75, 0.25))
    uphill_edge = _edge_key(geonet, (0.25, 0.25), (2.75, 2.75))
    assert grades[flat_edge] == 0.0
    assert grades[uphill_edge] == pytest.approx(4.0 / geonet.graph.edges[uphill_edge]["length"])


def test_terrain_cost_preserves_flat_length_and_penalizes_uphill_edges():
    geonet = _mixed_network()

    costs = terrain_cost_per_edge(
        geonet,
        _manifest(),
        repo=REPO_ROOT,
        n_samples=5,
        grade_weight=2.0,
    )

    flat_edge = _edge_key(geonet, (0.25, 0.25), (0.75, 0.25))
    uphill_edge = _edge_key(geonet, (0.25, 0.25), (2.75, 2.75))
    assert costs[flat_edge] == pytest.approx(geonet.graph.edges[flat_edge]["length"])
    assert costs[uphill_edge] > geonet.graph.edges[uphill_edge]["length"]


def test_crs_mismatch_fails():
    geonet = _mixed_network()
    manifest = _manifest()
    manifest["coordinate_frame"]["crs"] = "EPSG:4326"

    with pytest.raises(ValueError, match="terrain CRS must match GeoNetwork CRS"):
        terrain_elevation_delta_per_edge(geonet, manifest, repo=REPO_ROOT)


def test_missing_extent_fails():
    geonet = _mixed_network()
    manifest = _manifest()
    del manifest["coordinate_frame"]["extent"]

    with pytest.raises(ValueError, match="coordinate_frame.extent is required"):
        terrain_elevation_delta_per_edge(geonet, manifest, repo=REPO_ROOT)


def test_dem_raster_manifest_fails_until_raster_interop_phase():
    geonet = _mixed_network()
    manifest = _manifest()
    manifest["terrain_source"]["kind"] = "dem_raster"

    with pytest.raises(ValueError, match="terrain network coupling supports ascii_heightfield only"):
        terrain_elevation_delta_per_edge(geonet, manifest, repo=REPO_ROOT)


def test_invalid_sampling_and_weight_fail():
    geonet = _mixed_network()

    with pytest.raises(ValueError, match="n_samples must be an integer >= 2"):
        terrain_elevation_delta_per_edge(geonet, _manifest(), repo=REPO_ROOT, n_samples=True)
    with pytest.raises(ValueError, match="n_samples must be an integer >= 2"):
        terrain_elevation_delta_per_edge(geonet, _manifest(), repo=REPO_ROOT, n_samples=1)
    with pytest.raises(ValueError, match="grade_weight must be non-negative"):
        terrain_cost_per_edge(geonet, _manifest(), repo=REPO_ROOT, grade_weight=-0.1)


def test_out_of_extent_edge_fails():
    manifest = deepcopy(_manifest())
    geonet = GeoNetwork.from_lines(
        [LineString([(10.0, 10.0), (11.0, 11.0)])],
        crs="EPSG:3857",
        snap_tol=0.01,
    )

    with pytest.raises(ValueError, match="terrain sample is outside extent"):
        terrain_elevation_delta_per_edge(geonet, manifest, repo=REPO_ROOT)


def test_terrain_network_coupling_gate_passes_on_mixed_flat_and_uphill_network():
    ok, message = terrain_network_coupling_gate(
        _mixed_network(),
        _manifest(),
        repo=REPO_ROOT,
        threshold=0.01,
    )

    assert ok is True
    assert "terrain changes network edge cost" in message
    assert "not a 3D renderer or physical traffic model" in message


def test_terrain_network_coupling_gate_fails_on_flat_terrain(tmp_path):
    (tmp_path / "flat.asc").write_text("1 1 1\n1 1 1\n1 1 1\n", encoding="utf-8")
    manifest = _manifest()
    manifest["terrain_source"]["path"] = "flat.asc"
    manifest["terrain_source"]["sha256"] = (
        "b0e1f800f8131e14205af4f90b65680d9c72e78543ae5ec0632ff5da8e305e2c"
    )

    ok, message = terrain_network_coupling_gate(
        _mixed_network(),
        manifest,
        repo=tmp_path,
        threshold=0.01,
    )

    assert ok is False
    assert "no terrain grade above threshold" in message
