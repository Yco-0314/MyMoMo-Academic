"""Adapters from GIS spaces to mechanism-library neighbor callables."""
from __future__ import annotations


def raster_cell_neighbors(space, moore: bool = False) -> dict:
    width = space.width
    height = space.height

    def cell_id(col: int, row: int) -> int:
        return row * width + col

    def neighbors_of(i: int) -> list[int]:
        row, col = divmod(int(i), width)
        cells = space.neighbor_cells(col, row, radius=1, moore=moore)
        return sorted(cell_id(nc, nr) for nc, nr in cells)

    return {"n_agents": width * height, "neighbors_of": neighbors_of}


def point_radius_neighbors(space, radius: float) -> dict:
    def neighbors_of(i: int) -> list[int]:
        return space.neighbors_within(int(i), radius=radius)

    return {"n_agents": space.n_points, "neighbors_of": neighbors_of}


def geonetwork_node_neighbors(geonet) -> dict:
    nodes = sorted(geonet.graph.nodes, key=repr)
    node_to_index = {node: idx for idx, node in enumerate(nodes)}

    def neighbors_of(i: int) -> list[int]:
        node = nodes[int(i)]
        return sorted(node_to_index[nbr] for nbr in geonet.graph.neighbors(node))

    return {
        "n_agents": len(nodes),
        "neighbors_of": neighbors_of,
        "index_to_node": nodes,
        "node_to_index": node_to_index,
    }
