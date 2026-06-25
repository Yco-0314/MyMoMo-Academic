import numpy as np
import pytest
from affine import Affine

from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._temporal import RasterTimeline


def _frame(
    value=0.0,
    *,
    shape=(2, 3),
    crs="EPSG:3857",
    transform=Affine(10.0, 0, 100.0, 0, -10.0, 200.0),
):
    data = np.full(shape, value, dtype=float)
    field = RasterField(data=data, transform=transform, crs=crs, nodata=-1.0)
    return RasterSpace(field)


def test_from_frames_preserves_order_identity_and_dimensions():
    first = _frame(1.0)
    second = _frame(2.0)
    frames = [first, second]

    timeline = RasterTimeline.from_frames(frames)
    frames.reverse()

    assert timeline.n_steps == 2
    assert timeline.crs == "EPSG:3857"
    assert timeline.width == 3
    assert timeline.height == 2
    assert timeline.at(0) is first
    assert timeline.at(1) is second


def test_from_frames_rejects_empty_sequence():
    with pytest.raises(ValueError, match="empty|at least one"):
        RasterTimeline.from_frames([])


def test_direct_construction_is_not_allowed():
    with pytest.raises(TypeError):
        RasterTimeline(())


def test_unvalidated_helper_construction_path_is_not_exposed():
    assert not hasattr(RasterTimeline, "_from_validated_frames")


def test_from_frames_rejects_non_raster_space_frames():
    with pytest.raises(ValueError, match="RasterSpace"):
        RasterTimeline.from_frames([_frame(), object()])


def test_from_frames_rejects_inconsistent_crs():
    with pytest.raises(ValueError, match="CRS"):
        RasterTimeline.from_frames([_frame(), _frame(crs="EPSG:4326")])


def test_from_frames_rejects_inconsistent_dimensions():
    with pytest.raises(ValueError, match="shape|dimensions"):
        RasterTimeline.from_frames([_frame(), _frame(shape=(3, 3))])


def test_from_frames_rejects_inconsistent_transform():
    shifted = Affine(10.0, 0, 110.0, 0, -10.0, 200.0)

    with pytest.raises(ValueError, match="transform"):
        RasterTimeline.from_frames([_frame(), _frame(transform=shifted)])


@pytest.mark.parametrize("index", [True, 1.0, "1", -1, 2])
def test_at_rejects_invalid_time_indexes(index):
    timeline = RasterTimeline.from_frames([_frame(1.0), _frame(2.0)])

    with pytest.raises(ValueError, match="time|index"):
        timeline.at(index)
