"""Vector (shapefile/GeoJSON) loading via geopandas (lazy, [gis] extra)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from abm_auto.gis import require_gis


@dataclass
class VectorLayer:
    geometries: List[Any]      # shapely geometries
    crs: str
    attributes: List[dict]     # per-feature attribute dicts


def load_vector(path, encoding: str = "utf-8") -> VectorLayer:
    """Load a vector file. `encoding` controls .dbf attribute decoding
    (use 'gbk' for some Chinese shapefiles if 'utf-8' mojibakes)."""
    require_gis()
    import geopandas as gpd
    gdf = gpd.read_file(Path(path), encoding=encoding)
    geoms = list(gdf.geometry)
    attrs = gdf.drop(columns="geometry").to_dict("records")
    return VectorLayer(geometries=geoms, crs=str(gdf.crs), attributes=attrs)
