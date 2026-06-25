"""Minimal headless map output: density raster + infected overlay.
No basemap deps (cartopy/contextily) — matplotlib only."""
from __future__ import annotations

from pathlib import Path


def render_map(space, infected, path) -> None:
    import matplotlib
    matplotlib.use("Agg")  # headless
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.imshow(space.field.data, cmap="Greys", origin="upper")
    ys, xs = np.where(infected > 0)
    ax.scatter(xs, ys, s=6, c="red", label="infected")
    ax.set_title(f"raster SIR ({space.crs})")
    ax.legend(loc="upper right")
    fig.savefig(Path(path), dpi=100, bbox_inches="tight")
    plt.close(fig)
