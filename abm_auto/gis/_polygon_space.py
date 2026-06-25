"""PolygonSpace: stable region IDs over projected polygons."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Iterable

from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.strtree import STRtree


@dataclass(frozen=True)
class PolygonSpace:
    polygons: tuple
    crs: str
    ids: tuple
    _tree: object

    @classmethod
    def from_polygons(
        cls,
        polygons: Iterable[object],
        crs: str,
        ids: Iterable[object] | None = None,
    ) -> "PolygonSpace":
        polygon_tuple = tuple(polygons)
        id_tuple = tuple(range(len(polygon_tuple))) if ids is None else tuple(ids)
        if len(id_tuple) != len(polygon_tuple):
            raise ValueError("PolygonSpace ids length must match polygons length")
        for polygon in polygon_tuple:
            if not isinstance(polygon, (Polygon, MultiPolygon)):
                raise ValueError("PolygonSpace geometries must be Polygon or MultiPolygon")
            if polygon.is_empty:
                raise ValueError("PolygonSpace geometries must not be empty")
        seen_ids = set()
        for polygon_id in id_tuple:
            if polygon_id is None:
                raise ValueError("PolygonSpace ids must not be None")
            try:
                hash(polygon_id)
            except TypeError as exc:
                raise ValueError("PolygonSpace ids must be hashable") from exc
            if polygon_id != polygon_id:
                raise ValueError("PolygonSpace ids must not be NaN")
            if polygon_id in seen_ids:
                raise ValueError("PolygonSpace ids must be unique")
            seen_ids.add(polygon_id)
        return cls(
            polygons=polygon_tuple,
            crs=crs,
            ids=id_tuple,
            _tree=STRtree(polygon_tuple),
        )

    @property
    def n_polygons(self) -> int:
        return len(self.polygons)

    def polygon_id_at(self, index: int) -> object:
        if isinstance(index, bool) or not isinstance(index, Integral):
            raise ValueError("PolygonSpace polygon index must be an integer")
        if index < 0 or index >= len(self.ids):
            raise ValueError(
                f"PolygonSpace polygon index {index} out of range [0, {len(self.ids)})"
            )
        return self.ids[index]

    def _candidate_indices(self, geometry: object) -> list[int]:
        candidates = self._tree.query(geometry)
        return [int(candidate) for candidate in candidates]

    def contains_point(self, x: float, y: float) -> object | None:
        point = Point(float(x), float(y))
        for index in sorted(self._candidate_indices(point)):
            if self.polygons[index].covers(point):
                return self.ids[index]
        return None

    def assign_points(self, point_space: object) -> dict[object, list[int]]:
        assignments: dict[object, list[int]] = {}
        for point_id in range(point_space.n_points):
            x, y = point_space.coord_of(point_id)
            polygon_id = self.contains_point(x, y)
            if polygon_id is not None:
                assignments.setdefault(polygon_id, []).append(point_id)
        return assignments

    def adjacent_regions(self, touches: bool = True) -> set[tuple[object, object]]:
        pairs = set()
        for left_index, left in enumerate(self.polygons):
            for right_index in range(left_index + 1, self.n_polygons):
                right = self.polygons[right_index]
                is_adjacent = left.touches(right) if touches else left.intersects(right)
                if is_adjacent:
                    pairs.add((self.ids[left_index], self.ids[right_index]))
        return pairs
