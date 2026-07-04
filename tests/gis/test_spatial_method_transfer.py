import math

import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._spatial_method_transfer import (
    forman_ricci_edge_scores,
    geonetwork_spatial_curvature_summary,
    raster_spatial_curvature_summary,
    spatial_curvature_summary,
    spatial_method_transfer_gate,
    spatial_method_transfer_report,
)


def _chain_neighbors(i: int) -> list[int]:
    out = []
    if i > 0:
        out.append(i - 1)
    if i < 3:
        out.append(i + 1)
    return out


def _raster_chain() -> RasterSpace:
    return RasterSpace(
        RasterField(
            data=np.zeros((1, 4)),
            transform=Affine.identity(),
            crs="EPSG:3857",
        )
    )


def _geonetwork_chain() -> GeoNetwork:
    return GeoNetwork.from_lines(
        [
            LineString([(0, 0), (1, 0)]),
            LineString([(1, 0), (2, 0)]),
            LineString([(2, 0), (3, 0)]),
        ],
        crs="EPSG:3857",
        snap_tol=1.0,
    )


def test_forman_ricci_edge_scores_chain_signature():
    scores = forman_ricci_edge_scores(4, _chain_neighbors)

    assert scores == {
        (0, 1): 1.0,
        (1, 2): 0.0,
        (2, 3): 1.0,
    }


@pytest.mark.parametrize(
    ("n_nodes", "neighbors_of", "message"),
    [
        (True, _chain_neighbors, "n_nodes must be a positive integer"),
        (0, _chain_neighbors, "n_nodes must be a positive integer"),
        (4, lambda _: [-1], "neighbor ids must be in"),
        (4, lambda _: [4], "neighbor ids must be in"),
        (4, lambda i: [i], "self loops are not supported"),
        (4, lambda _: [True], "neighbor ids must be integers"),
    ],
)
def test_forman_ricci_edge_scores_rejects_invalid_inputs(
    n_nodes,
    neighbors_of,
    message,
):
    with pytest.raises(ValueError, match=message):
        forman_ricci_edge_scores(n_nodes, neighbors_of)


def test_spatial_curvature_summary_reports_min_edge_and_signature():
    summary = spatial_curvature_summary(4, _chain_neighbors)

    assert summary["n_nodes"] == 4
    assert summary["n_edges"] == 3
    assert summary["score_signature"] == [0.0, 1.0, 1.0]
    assert summary["min_score"] == 0.0
    assert summary["max_score"] == 1.0
    assert math.isclose(summary["mean_score"], 2.0 / 3.0)
    assert summary["min_edges"] == [(1, 2)]


def test_raster_spatial_curvature_summary_transfers_chain_signature():
    summary = raster_spatial_curvature_summary(_raster_chain(), moore=False)

    assert summary["space_type"] == "RasterSpace"
    assert summary["n_nodes"] == 4
    assert summary["n_edges"] == 3
    assert summary["score_signature"] == [0.0, 1.0, 1.0]


def test_geonetwork_spatial_curvature_summary_transfers_chain_signature():
    summary = geonetwork_spatial_curvature_summary(_geonetwork_chain())

    assert summary["space_type"] == "GeoNetwork"
    assert summary["n_nodes"] == 4
    assert summary["n_edges"] == 3
    assert summary["score_signature"] == [0.0, 1.0, 1.0]


def test_spatial_method_transfer_report_compares_raster_and_geonetwork():
    report = spatial_method_transfer_report()

    assert report["ok"] is True
    assert report["reason"] == ""
    assert report["raster_summary"]["score_signature"] == [0.0, 1.0, 1.0]
    assert report["geonetwork_summary"]["score_signature"] == [0.0, 1.0, 1.0]
    assert report["signatures_match"] is True
    assert "not full ORC/TDA" in report["boundary_note"]


def test_spatial_method_transfer_gate_passes_with_boundary_text():
    ok, desc = spatial_method_transfer_gate()

    assert ok, desc
    assert "spatial method transfer passed" in desc
    assert "Forman-style" in desc
    assert "RasterSpace" in desc
    assert "GeoNetwork" in desc
    assert "not full ORC/TDA" in desc
    assert "not spatial validation" in desc
