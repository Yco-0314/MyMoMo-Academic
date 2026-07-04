# Observed Raster Fixture Pack

This directory documents how local observed raster clips are described for GIS
spatial validation and calibration.

The committed `test_observed.tif` is a tiny local test fixture. It is not
official GHSL or WorldPop data. It exists only so automated tests can exercise
the manifest, GeoTIFF loading, provenance, and calibration path without network
access or large source tiles.

## Real GHSL/WorldPop Workflow

1. Download an official raster tile outside the test suite.
   - GHSL download page: `https://human-settlement.emergency.copernicus.eu/download.php`
   - WorldPop hub: `https://hub.worldpop.org/`
2. Clip a small city window with `data/fixtures/fetch_clip.py` or
   `abm_auto.gis._fixtures.clip_window`.
3. Copy `manifest.example.json` and set:
   - `raster_path` to the clipped GeoTIFF;
   - `dataset` to the real product name;
   - `source_url` and `source_download_page` to official source pages;
   - `license` to the required attribution text;
   - `threshold`, `param_grid`, and `expected_best_params` for the local gate.
4. Load it with `load_observed_raster_from_manifest(...)` or calibrate with
   `calibrate_observed_raster_from_manifest(...)`.

No runtime helper in this pack downloads remote files, resamples rasters, or
changes CRS. Those operations must be explicit reproducibility steps.
