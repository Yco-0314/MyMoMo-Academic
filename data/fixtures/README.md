# GIS fixtures

## ghsl_city.tif (default raster-SIR fixture)

- **Source:** GHSL GHS-POP (Global Human Settlement Layer, population), European
  Commission JRC — https://ghsl.jrc.ec.europa.eu/
- **License:** free reuse with attribution (© European Union, GHSL).
- **CRS:** World Mollweide (ESRI:54009), metres, equal-area; population per cell.
- **How to (re)generate:** download a GHS-POP tile, then
  `python data/fixtures/fetch_clip.py` (edit the window for a different city).
  **Any global city is a window swap; no city is hardcoded.**
- **Committed:** only the small clip is committed — never the full tile.

> Not yet generated: run `fetch_clip.py` against a downloaded GHS-POP tile to
> produce `ghsl_city.tif`. Until then, the end-to-end test (Task 9) skips.

### Future (vector phase) — real road network

A real road-network shapefile set (`路网*`, China) is registered as the
VectorSpace-widening fixture. **Before use, verify its CRS:** the `.prj` declares
WGS-84, but Chinese road data is frequently GCJ-02 mislabelled as WGS-84 (a
~50–500 m offset) — confirm against a known-true basemap first. See the GIS spec
"Regional datum / CRS handling" widening item.
