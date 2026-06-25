import numpy as np
import pytest

from abm_auto.gis._point_space import PointSpace


def test_point_space_keeps_stable_ids_and_coordinates():
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    assert ps.crs == "EPSG:3857"
    assert ps.n_points == 3
    assert ps.coord_of(0) == (0.0, 0.0)
    assert ps.coord_of(1) == (3.0, 4.0)
    assert ps.coord_of(2) == (10.0, 0.0)


def test_point_space_defensively_copies_input_coordinates():
    coords = np.array([(0, 0), (3, 4), (10, 0)], dtype=float)
    ps = PointSpace.from_coords(coords, crs="EPSG:3857")

    coords[0] = (99, 99)

    assert ps.coord_of(0) == (0.0, 0.0)


def test_point_space_exposed_coordinates_do_not_mutate_internal_spatial_index():
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    exposed = ps.coords
    exposed.setflags(write=True)
    exposed[0] = (1000, 1000)

    assert ps.coord_of(0) == (0.0, 0.0)
    assert ps.nearest(0, 0) == 0


def test_nearest_returns_stable_integer_id():
    ps = PointSpace.from_coords([(0, 0), (10, 0), (20, 0)], crs="EPSG:3857")

    assert ps.nearest(11, 1) == 1
    assert ps.nearest(-2, 0) == 0


def test_neighbors_within_radius_excludes_self_by_default():
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0), (30, 0)], crs="EPSG:3857")

    assert ps.neighbors_within(0, radius=5.0) == [1]
    assert ps.neighbors_within(0, radius=5.0, include_self=True) == [0, 1]


@pytest.mark.parametrize("point_id", [-1, 3])
def test_coord_of_rejects_invalid_point_ids(point_id):
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    with pytest.raises(ValueError, match="point_id"):
        ps.coord_of(point_id)


@pytest.mark.parametrize("point_id", [-1, 3])
def test_neighbors_within_rejects_invalid_point_ids(point_id):
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    with pytest.raises(ValueError, match="point_id"):
        ps.neighbors_within(point_id, radius=1.0)


@pytest.mark.parametrize("point_id", [0.5, "0"])
def test_coord_of_rejects_non_integer_point_ids(point_id):
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    with pytest.raises(ValueError, match="point_id"):
        ps.coord_of(point_id)


@pytest.mark.parametrize("point_id", [True, False])
def test_coord_of_rejects_bool_point_ids(point_id):
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    with pytest.raises(ValueError, match="point_id"):
        ps.coord_of(point_id)


@pytest.mark.parametrize("point_id", [0.5, "0"])
def test_neighbors_within_rejects_non_integer_point_ids(point_id):
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    with pytest.raises(ValueError, match="point_id"):
        ps.neighbors_within(point_id, radius=1.0)


@pytest.mark.parametrize("point_id", [True, False])
def test_neighbors_within_rejects_bool_point_ids(point_id):
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    with pytest.raises(ValueError, match="point_id"):
        ps.neighbors_within(point_id, radius=1.0)


def test_neighbors_within_rejects_negative_radius():
    ps = PointSpace.from_coords([(0, 0), (3, 4), (10, 0)], crs="EPSG:3857")

    with pytest.raises(ValueError, match="radius"):
        ps.neighbors_within(0, radius=-1.0)


def test_invalid_point_shape_is_rejected():
    with pytest.raises(ValueError, match="Nx2"):
        PointSpace.from_coords([(0, 0, 1)], crs="EPSG:3857")


def test_ragged_point_shape_is_rejected_with_nx2_message():
    with pytest.raises(ValueError, match="Nx2"):
        PointSpace.from_coords([(0, 0), (1, 2, 3)], crs="EPSG:3857")


@pytest.mark.parametrize(
    "coords",
    [
        np.empty((0, 3)),
        np.empty((1, 0)),
        [()],
    ],
)
def test_malformed_empty_point_shapes_are_rejected(coords):
    with pytest.raises(ValueError, match="Nx2"):
        PointSpace.from_coords(coords, crs="EPSG:3857")
