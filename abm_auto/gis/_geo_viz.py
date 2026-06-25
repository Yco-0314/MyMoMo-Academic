"""Headless network map: roads at real coords, edge load as line width/colour."""
from __future__ import annotations

from pathlib import Path


def render_network(geonet, edge_load, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    g = geonet.graph
    maxload = max(edge_load.values()) or 1
    fig, ax = plt.subplots(figsize=(5, 5))
    for u, v in g.edges:
        x = [g.nodes[u]["x"], g.nodes[v]["x"]]
        y = [g.nodes[u]["y"], g.nodes[v]["y"]]
        load = edge_load.get(tuple(sorted((u, v))), 0)
        ax.plot(x, y, color="crimson", linewidth=0.5 + 4.0 * load / maxload,
                solid_capstyle="round", alpha=0.8)
    ax.set_aspect("equal")
    ax.set_title(f"road network load ({geonet.crs})")
    fig.savefig(Path(path), dpi=100, bbox_inches="tight")
    plt.close(fig)
