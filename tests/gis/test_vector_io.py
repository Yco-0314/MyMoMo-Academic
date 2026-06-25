import geopandas as gpd
from shapely.geometry import LineString

from abm_auto.gis._vector_io import load_vector


def test_load_vector_reads_lines_crs_attrs(tmp_path):
    gdf = gpd.GeoDataFrame(
        {"road": ["a", "b"]},
        geometry=[LineString([(0, 0), (1, 0)]), LineString([(1, 0), (1, 1)])],
        crs="EPSG:3857",
    )
    p = tmp_path / "roads.shp"
    gdf.to_file(p)
    layer = load_vector(p)
    assert len(layer.geometries) == 2
    assert "3857" in str(layer.crs)
    assert layer.attributes[0]["road"] == "a"
    assert layer.geometries[0].length == 1.0
