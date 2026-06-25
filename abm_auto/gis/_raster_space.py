"""RasterSpace: a georeferenced discrete grid.

Agents live in CELL coordinates (col, row) — same neighbour logic as the
runtime Grid. The affine transform maps cell <-> world coordinates for data
I/O and map output only. The space is CRS-agnostic: it carries the dataset's
real CRS and never assumes one.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np

from abm_auto.runtime._grid import Grid  # composition; runtime is NOT modified


@dataclass
class RasterField:
    data: np.ndarray            # shape (rows, cols)
    transform: Any              # affine.Affine: (col,row) -> (x,y) world
    crs: str                    # e.g. "ESRI:54009"
    nodata: Optional[float] = None


class RasterSpace:
    """Georeferenced grid. Wraps a runtime Grid for cell topology; owns the
    affine transform / CRS / nodata that the plain Grid lacks."""

    def __init__(self, field: RasterField, wrap: bool = False) -> None:
        self.field = field
        rows, cols = field.data.shape
        self._grid = Grid()
        self._grid.setup_params(width=cols, height=rows, wrap=wrap)

    @property
    def width(self) -> int:
        return self._grid.width

    @property
    def height(self) -> int:
        return self._grid.height

    @property
    def crs(self) -> str:
        return self.field.crs

    # ── cell <-> world (pixel-centre convention) ──────────────────────────
    def cell_to_world(self, col: int, row: int) -> Tuple[float, float]:
        return self.field.transform * (col + 0.5, row + 0.5)

    def world_to_cell(self, x: float, y: float) -> Tuple[int, int]:
        inv = ~self.field.transform
        fcol, frow = inv * (x, y)
        return int(np.floor(fcol)), int(np.floor(frow))

    # ── field access ──────────────────────────────────────────────────────
    def value_at(self, col: int, row: int) -> float:
        """Raster value at (col, row). UNCHECKED — the caller must bounds-check
        (0 <= col < width, 0 <= row < height) first; an out-of-bounds index raises
        IndexError. Deliberately unchecked to avoid per-sample cost on hot sampling
        loops (flood_depth_per_edge / sample_raster_at_points pre-check, then call)."""
        return float(self.field.data[row, col])

    def is_nodata(self, col: int, row: int) -> bool:
        nd = self.field.nodata
        return nd is not None and self.value_at(col, row) == nd

    # ── neighbours (delegate to the runtime Grid) ─────────────────────────
    def neighbor_cells(self, col: int, row: int, radius: int = 1, moore: bool = True):
        return self._grid._get_neighbor_positions(col, row, radius, moore, True)
