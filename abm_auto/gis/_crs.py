"""CRS reprojection (pyproj) + the China GCJ-02/BD-09 datum transform.

GCJ-02 ("Mars coordinates") is a legally-mandated nonlinear offset applied to
public maps in mainland China. PROJ/pyproj do NOT implement it (it is not a
published transform), so it lives here. Algorithm is the long-published
Krasovsky-ellipsoid formulation.
"""
from __future__ import annotations

import math
import statistics

from abm_auto.gis import require_gis

_A = 6378245.0                       # Krasovsky 1940 semi-major axis
_EE = 0.00669342162296594323         # eccentricity squared


def reproject(xs, ys, src_crs, dst_crs):
    """Reproject coordinate(s) from src_crs to dst_crs via pyproj (always_xy)."""
    require_gis()
    from pyproj import Transformer
    t = Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    return t.transform(xs, ys)


def _out_of_china(lon, lat):
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _tf_lat(x, y):
    ret = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20 * math.sin(6 * x * math.pi) + 20 * math.sin(2 * x * math.pi)) * 2 / 3
    ret += (20 * math.sin(y * math.pi) + 40 * math.sin(y / 3 * math.pi)) * 2 / 3
    ret += (160 * math.sin(y / 12 * math.pi) + 320 * math.sin(y * math.pi / 30)) * 2 / 3
    return ret


def _tf_lon(x, y):
    ret = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20 * math.sin(6 * x * math.pi) + 20 * math.sin(2 * x * math.pi)) * 2 / 3
    ret += (20 * math.sin(x * math.pi) + 40 * math.sin(x / 3 * math.pi)) * 2 / 3
    ret += (150 * math.sin(x / 12 * math.pi) + 300 * math.sin(x / 30 * math.pi)) * 2 / 3
    return ret


def wgs84_to_gcj02(lon, lat):
    if _out_of_china(lon, lat):
        return lon, lat
    dlat = _tf_lat(lon - 105.0, lat - 35.0)
    dlon = _tf_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - _EE * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrtmagic) * math.pi)
    dlon = (dlon * 180.0) / (_A / sqrtmagic * math.cos(radlat) * math.pi)
    return lon + dlon, lat + dlat


def gcj02_to_wgs84(lon, lat):
    """Iterative inverse of wgs84_to_gcj02 (converges in a few steps)."""
    if _out_of_china(lon, lat):
        return lon, lat
    wlon, wlat = lon, lat
    for _ in range(4):
        clon, clat = wgs84_to_gcj02(wlon, wlat)
        wlon += lon - clon
        wlat += lat - clat
    return wlon, wlat


def median_offset_m(pts_a, pts_b):
    """Median metric distance (m) between paired lon/lat points (rough, via
    degrees->metres at each latitude)."""
    offs = []
    for (lon1, lat1), (lon2, lat2) in zip(pts_a, pts_b):
        dlat_m = (lat1 - lat2) * 111320.0
        dlon_m = (lon1 - lon2) * 111320.0 * math.cos(math.radians(lat1))
        offs.append(math.hypot(dlat_m, dlon_m))
    return statistics.median(offs) if offs else 0.0


def looks_like_gcj02_mislabeled(declared_pts, reference_true_wgs84):
    """A layer DECLARES WGS-84; check whether its coordinates are actually GCJ-02.

    If treating the declared points as GCJ-02 and converting to WGS-84 collapses
    a large offset (vs a known-true reference) to near zero, it was mislabeled."""
    raw = median_offset_m(declared_pts, reference_true_wgs84)
    corrected = [gcj02_to_wgs84(lon, lat) for lon, lat in declared_pts]
    corr = median_offset_m(corrected, reference_true_wgs84)
    suspected = raw > 50.0 and corr < raw * 0.5
    return suspected, {"raw_offset_m": raw, "corrected_offset_m": corr}
