import math

from abm_auto.gis._crs import reproject, wgs84_to_gcj02, gcj02_to_wgs84


def test_reproject_wgs84_to_webmercator():
    x, y = reproject(0.0, 0.0, "EPSG:4326", "EPSG:3857")
    assert abs(x) < 1e-6 and abs(y) < 1e-6


def test_gcj02_offset_is_hundreds_of_metres_in_china():
    lon, lat = 116.3974, 39.9093  # Beijing
    glon, glat = wgs84_to_gcj02(lon, lat)
    dm = math.hypot((glon - lon) * 85000, (glat - lat) * 111000)  # ~metres
    assert 100 < dm < 1000
    assert wgs84_to_gcj02(-0.1, 51.5) == (-0.1, 51.5)  # out of china: identity


def test_gcj02_roundtrip_recovers_wgs84():
    lon, lat = 116.3974, 39.9093
    glon, glat = wgs84_to_gcj02(lon, lat)
    wlon, wlat = gcj02_to_wgs84(glon, glat)
    assert abs(wlon - lon) < 1e-5 and abs(wlat - lat) < 1e-5
