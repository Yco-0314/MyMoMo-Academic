"""PointSpace: stable point IDs over projected coordinates."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Iterable, Tuple

import numpy as np
from scipy.spatial import cKDTree


@dataclass(frozen=True)
class PointSpace:
    _coords: np.ndarray
    crs: str
    _tree: cKDTree

    @classmethod
    def from_coords(cls, coords: Iterable[Tuple[float, float]], crs: str) -> "PointSpace":
        shape_error = "PointSpace coordinates must be an Nx2 array"
        try:
            if isinstance(coords, np.ndarray):
                arr = np.asarray(coords, dtype=float)
            else:
                coord_list = list(coords)
                if not coord_list:
                    arr = np.empty((0, 2), dtype=float)
                else:
                    arr = np.asarray(coord_list, dtype=float)
        except (TypeError, ValueError):
            raise ValueError(shape_error) from None
        if arr.ndim != 2 or arr.shape[1] != 2:
            raise ValueError(shape_error)
        arr = arr.copy()
        arr.setflags(write=False)
        return cls(_coords=arr, crs=crs, _tree=cKDTree(arr))

    @property
    def coords(self) -> np.ndarray:
        return self._coords.copy()

    @property
    def n_points(self) -> int:
        return int(self._coords.shape[0])

    def _validate_point_id(self, point_id: int) -> None:
        if isinstance(point_id, bool) or not isinstance(point_id, Integral):
            raise ValueError(f"point_id must be in [0, {self.n_points})")
        if not 0 <= point_id < self.n_points:
            raise ValueError(f"point_id must be in [0, {self.n_points})")

    def coord_of(self, point_id: int) -> Tuple[float, float]:
        self._validate_point_id(point_id)
        x, y = self._coords[point_id]
        return float(x), float(y)

    def nearest(self, x: float, y: float) -> int:
        if self.n_points == 0:
            raise ValueError("Cannot query nearest point in an empty PointSpace")
        _, point_id = self._tree.query((float(x), float(y)))
        return int(point_id)

    def neighbors_within(
        self,
        point_id: int,
        radius: float,
        include_self: bool = False,
    ) -> list[int]:
        self._validate_point_id(point_id)
        if radius < 0:
            raise ValueError("radius must be non-negative")
        neighbors = self._tree.query_ball_point(self._coords[point_id], r=float(radius))
        if not include_self:
            neighbors = [neighbor for neighbor in neighbors if neighbor != point_id]
        return sorted(int(neighbor) for neighbor in neighbors)
