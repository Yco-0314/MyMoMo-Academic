import pytest


def test_geopandas_available_under_gis_extra():
    gpd = pytest.importorskip("geopandas")
    pytest.importorskip("shapely")
    assert hasattr(gpd, "read_file")
    from shapely.geometry import LineString
    assert LineString([(0, 0), (1, 1)]).length > 0
