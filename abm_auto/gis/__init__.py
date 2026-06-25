"""ABM Auto — GIS mode (additive, import-isolated).

GIS libraries (rasterio/pyproj) are an optional extra: ``pip install abm-auto[gis]``.
They are imported lazily inside the GIS modules; importing this package never
pulls them in, so the base (non-GIS) install stays light.
"""
from __future__ import annotations

try:
    import rasterio  # noqa: F401
    import pyproj  # noqa: F401
    _HAS_GIS = True
except Exception:
    _HAS_GIS = False


def require_gis() -> None:
    """Raise a clear, actionable error if the GIS extra is not installed."""
    if not _HAS_GIS:
        raise ImportError(
            "GIS mode needs the optional GIS dependencies. "
            "Install them with:  pip install abm-auto[gis]"
        )
