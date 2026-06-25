"""GIS intent detection: geographic stories route to the GIS path + a spatial
type; abstract spatial models do NOT (the safe default)."""
from abm_auto.gis._intent import detect_gis_intent, needs_spatial_clarification


def test_raster_story_detected():
    i = detect_gis_intent("Simulate an epidemic on the population density raster of a city (GeoTIFF).")
    assert i.is_gis and i.spatial_type == "raster" and i.confidence > 0.6


def test_road_network_story_detected():
    i = detect_gis_intent("Model commuter traffic on the Aberdeen road network loaded from a shapefile.")
    assert i.is_gis and i.spatial_type == "network"


def test_vector_region_story_detected():
    i = detect_gis_intent("Agents in administrative regions (census districts, polygon boundaries) from GIS data.")
    assert i.is_gis and i.spatial_type == "vector"


def test_abstract_grid_is_NOT_gis():
    # Schelling on an abstract grid has no geographic marker -> non-GIS path
    i = detect_gis_intent("Schelling segregation: agents on a grid move when unhappy with neighbours.")
    assert i.is_gis is False and i.spatial_type == "none"


def test_abstract_network_is_NOT_gis():
    i = detect_gis_intent("Opinion dynamics on a random small-world network of agents.")
    assert i.is_gis is False


def test_gis_without_type_asks_for_clarification():
    i = detect_gis_intent("Build a GIS model using real-world geographic coordinate data.")
    assert i.is_gis is True
    assert needs_spatial_clarification(i)   # type unclear -> clarify
