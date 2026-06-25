import networkx as nx
import numpy as np
from affine import Affine

from abm_auto.gis._geo_network import GeoNetwork
from abm_auto.gis._mechanism_adapters import (
    geonetwork_node_neighbors,
    point_radius_neighbors,
    raster_cell_neighbors,
)
from abm_auto.gis._point_space import PointSpace
from abm_auto.gis._raster_space import RasterField, RasterSpace


def test_raster_cell_neighbors_maps_cell_ids_to_rook_neighbors():
    data = np.zeros((2, 3))
    sp = RasterSpace(RasterField(data=data, transform=Affine.identity(), crs="EPSG:3857"))

    adapted = raster_cell_neighbors(sp, moore=False)

    assert adapted["n_agents"] == 6
    assert adapted["neighbors_of"](0) == [1, 3]
    assert adapted["neighbors_of"](4) == [1, 3, 5]


def test_point_radius_neighbors_uses_point_space_ids():
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    adapted = point_radius_neighbors(ps, radius=5.0)

    assert adapted["n_agents"] == 3
    assert adapted["neighbors_of"](0) == [1]
    assert adapted["neighbors_of"](2) == []


def test_geonetwork_node_neighbors_uses_deterministic_node_indices():
    g = nx.Graph()
    g.add_edge(("b", 2), ("a", 1), length=1.0)
    g.add_edge(("a", 1), ("c", 3), length=1.0)
    geonet = GeoNetwork(g, crs="EPSG:3857")

    adapted = geonetwork_node_neighbors(geonet)

    assert adapted["n_agents"] == 3
    assert adapted["index_to_node"] == [("a", 1), ("b", 2), ("c", 3)]
    a_idx = adapted["node_to_index"][("a", 1)]
    assert adapted["neighbors_of"](a_idx) == [
        adapted["node_to_index"][("b", 2)],
        adapted["node_to_index"][("c", 3)],
    ]
