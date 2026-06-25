"""Fixture helpers: clip a small window out of a large source GeoTIFF.

Reusable clip logic lives here (importable); ``data/fixtures/fetch_clip.py`` is a
thin runner that points it at a downloaded GHSL tile."""
from __future__ import annotations

from pathlib import Path

from abm_auto.gis import require_gis


def clip_window(src_path, out_path, col_off, row_off, width, height) -> None:
    """Write a width×height window of ``src_path`` to ``out_path``, preserving
    CRS and a correctly-shifted affine transform."""
    require_gis()
    import rasterio
    from rasterio.windows import Window
    with rasterio.open(src_path) as src:
        win = Window(col_off, row_off, width, height)
        data = src.read(1, window=win)
        profile = src.profile.copy()
        profile.update(width=width, height=height,
                       transform=src.window_transform(win))
        with rasterio.open(Path(out_path), "w", **profile) as dst:
            dst.write(data, 1)
