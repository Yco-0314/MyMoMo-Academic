"""GeoTIFF loading. rasterio is imported lazily (optional [gis] extra)."""
from __future__ import annotations

from pathlib import Path

from abm_auto.gis import require_gis
from abm_auto.gis._raster_space import RasterField


def load_raster(path, band: int = 1) -> RasterField:
    """Read a single band of a GeoTIFF into a RasterField (data + georeferencing)."""
    require_gis()
    import rasterio
    with rasterio.open(Path(path)) as src:
        data = src.read(band).astype("float64")
        return RasterField(
            data=data,
            transform=src.transform,
            crs=str(src.crs),
            nodata=src.nodata,
        )
