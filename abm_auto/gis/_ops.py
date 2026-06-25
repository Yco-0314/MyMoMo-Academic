"""Spatial operations: metric distance (via the affine) and Moran's I."""
from __future__ import annotations

from typing import Tuple

import numpy as np


def metric_distance(space, cell_a: Tuple[int, int], cell_b: Tuple[int, int]) -> float:
    """Euclidean distance between two cells in the CRS's linear units (metres
    for a projected CRS)."""
    xa, ya = space.cell_to_world(*cell_a)
    xb, yb = space.cell_to_world(*cell_b)
    return float(np.hypot(xa - xb, ya - yb))


def morans_i(field: np.ndarray) -> float:
    """Global Moran's I with rook contiguity (4-neighbour) weights.
    Returns autocorrelation in roughly [-1, 1]; >0 = clustered."""
    z = field.astype(float) - field.mean()
    rows, cols = field.shape
    num = 0.0
    w = 0.0
    for r in range(rows):
        for c in range(cols):
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < rows and 0 <= cc < cols:
                    num += z[r, c] * z[rr, cc]
                    w += 1.0
    denom = (z ** 2).sum()
    if denom == 0 or w == 0:
        return 0.0
    n = rows * cols
    return (n / w) * (num / denom)
