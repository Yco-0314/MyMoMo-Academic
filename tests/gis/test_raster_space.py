import numpy as np
from affine import Affine

from abm_auto.gis._raster_space import RasterField, RasterSpace


def _field():
    # 3 rows x 4 cols, 100m pixels, origin at (1000, 5000) in a projected CRS (metres)
    data = np.arange(12, dtype=float).reshape(3, 4)
    transform = Affine(100.0, 0, 1000.0, 0, -100.0, 5000.0)
    return RasterField(data=data, transform=transform, crs="EPSG:3857", nodata=-1.0)


def test_dimensions_match_array():
    sp = RasterSpace(_field())
    assert sp.width == 4 and sp.height == 3


def test_cell_to_world_uses_pixel_centre():
    sp = RasterSpace(_field())
    x, y = sp.cell_to_world(0, 0)
    assert (round(x), round(y)) == (1050, 4950)


def test_world_to_cell_roundtrips():
    sp = RasterSpace(_field())
    for col, row in [(0, 0), (3, 2), (2, 1)]:
        x, y = sp.cell_to_world(col, row)
        assert sp.world_to_cell(x, y) == (col, row)


def test_value_at_reads_field():
    sp = RasterSpace(_field())
    assert sp.value_at(0, 0) == 0.0
    assert sp.value_at(3, 2) == 11.0


def test_neighbor_cells_delegates_to_grid():
    sp = RasterSpace(_field())
    nb = sp.neighbor_cells(1, 1)
    assert (0, 0) in nb and (2, 2) in nb and (1, 1) not in nb
