"""GIS intent detection — the gateway to the autonomous GIS path.

Classifies a plain-language story as GIS (real geographic space) or not, and if so
which spatial type. The routing rule (from the GIS mode spec): GIS activates only
on an explicit-or-inferred geographic signal; the safe default is the non-GIS path.

This is the deterministic, offline core (keyword/heuristic). The LLM detector
(Phase -1) can refine it, but the routing logic and signals are testable here
without any API call.

Key discipline: a GIS story needs a real GEOGRAPHIC marker (shapefile, GeoTIFF, a
real place, lat/lon, a road network, land use, …). An abstract grid (Schelling) or
abstract network (random graph) is NOT GIS.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

# Geographic markers — at least one is required for a story to be GIS.
_GEO_MARKERS = [
    "gis", "geographic", "geospatial", "shapefile", "geotiff", "geojson",
    "raster", "lat/lon", "latitude", "longitude", "coordinate", "crs", "epsg",
    "real city", "real-world", "land use", "land-use", "population density",
    "road network", "street network", "administrative", "census",
    "openstreetmap", "osm", "satellite", "elevation",
]

# Spatial-type signals (used to classify, once it IS gis).
_TYPE_SIGNALS = {
    "raster": ["raster", "geotiff", "land use", "land-use", "population density",
               "elevation", "grid of cells", "density field", "satellite"],
    "network": ["road network", "street network", "roads", "traffic", "commut",
                "transport", "highway", "rail", "street"],
    "point": ["address", "point of interest", "poi", "facilities", "stations",
              "locations at", "events at", "lat/lon points"],
    "vector": ["polygon", "administrative", "region", "boundary", "boundaries",
               "census tract", "district", "zone", "parcel"],
}


@dataclass
class GisIntent:
    is_gis: bool
    spatial_type: str = "none"        # none | raster | network | point | vector | unknown
    confidence: float = 0.0
    signals: List[str] = field(default_factory=list)


def _hits(text: str, terms) -> List[str]:
    return [t for t in terms if t in text]


def detect_gis_intent(story: str) -> GisIntent:
    text = story.lower()
    geo = _hits(text, _GEO_MARKERS)
    if not geo:
        return GisIntent(is_gis=False, spatial_type="none", confidence=0.0, signals=[])

    # classify spatial type by strongest signal group
    scores = {t: len(_hits(text, terms)) for t, terms in _TYPE_SIGNALS.items()}
    best_type = max(scores, key=scores.get)
    if scores[best_type] == 0:
        spatial_type = "unknown"          # GIS, but type unclear -> caller may clarify
    else:
        spatial_type = best_type

    # confidence grows with the number of distinct geographic + type signals
    n = len(set(geo)) + scores.get(spatial_type, 0)
    confidence = min(0.95, 0.5 + 0.1 * n)
    return GisIntent(is_gis=True, spatial_type=spatial_type,
                     confidence=round(confidence, 2), signals=sorted(set(geo)))


def needs_spatial_clarification(intent: GisIntent, threshold: float = 0.6) -> bool:
    """GIS detected but the spatial type is unclear or low-confidence -> ask."""
    return intent.is_gis and (intent.spatial_type == "unknown"
                              or intent.confidence < threshold)
