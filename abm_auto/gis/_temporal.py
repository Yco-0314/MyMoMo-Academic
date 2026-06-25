"""Temporal adapters for GIS raster spaces."""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Iterable

from abm_auto.gis._raster_space import RasterSpace


def _validate_raster_timeline_frames(frames: Iterable[RasterSpace]) -> tuple[RasterSpace, ...]:
    frame_tuple = tuple(frames)
    if not frame_tuple:
        raise ValueError("RasterTimeline requires at least one frame; got empty sequence")

    for frame in frame_tuple:
        if not isinstance(frame, RasterSpace):
            raise ValueError("RasterTimeline frames must be RasterSpace instances")

    first = frame_tuple[0]
    for frame in frame_tuple[1:]:
        if frame.crs != first.crs:
            raise ValueError("RasterTimeline frames must share the same CRS")
        if frame.width != first.width or frame.height != first.height:
            raise ValueError("RasterTimeline frames must share the same shape/dimensions")
        if frame.field.transform != first.field.transform:
            raise ValueError("RasterTimeline frames must share the same transform")
    return frame_tuple


@dataclass(frozen=True, init=False)
class RasterTimeline:
    """Ordered immutable sequence of georeferenced raster frames."""

    _frames: tuple[RasterSpace, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise TypeError("RasterTimeline must be constructed with RasterTimeline.from_frames()")

    @classmethod
    def from_frames(cls, frames: Iterable[RasterSpace]) -> "RasterTimeline":
        frame_tuple = _validate_raster_timeline_frames(frames)

        timeline = cls.__new__(cls)
        object.__setattr__(timeline, "_frames", frame_tuple)
        return timeline

    @property
    def n_steps(self) -> int:
        return len(self._frames)

    @property
    def crs(self) -> str:
        return self._frames[0].crs

    @property
    def width(self) -> int:
        return self._frames[0].width

    @property
    def height(self) -> int:
        return self._frames[0].height

    def at(self, t: int) -> RasterSpace:
        if isinstance(t, bool) or not isinstance(t, Integral):
            raise ValueError("time index must be an integer")
        if t < 0 or t >= self.n_steps:
            raise ValueError("time index out of range")
        return self._frames[int(t)]
