# Candidate #10 — Real Ba-Catchment Data Acquisition List

Concrete inputs needed to run the [real-DEM reproduction](../../superpowers/specs/2026-06-24-anshuka-real-dem-design.md).
Study area: **Ba town + floodplain, Viti Levu, Fiji** (the Anshuka 2026 Ba River EWS site),
≈ **17.53°S, 177.67°E**, on the Ba River, NW Viti Levu.

> Note: Fiji geodata is genuine **WGS-84** — the China GCJ-02/BD-09 path does NOT apply here. The
> `looks_like_gcj02_mislabeled` verifier should find **no** offset; that assertion is part of the gate.

## 1. Elevation — SRTM DEM (the load-bearing input)

- **Dataset:** SRTM 1 Arc-Second Global (SRTMGL1, **30 m**), or Copernicus DEM GLO-30 (30 m, more recent) as alternative.
- **Tile:** **`S18E177`** — SRTM 1°×1° tiles are named by SW corner; S18E177 covers lat **17°S–18°S**,
  lon **177°E–178°E**, which contains Ba (17.53°S, 177.67°E).
- **Sources (pick one):**
  - **OpenTopography** — `https://portal.opentopography.org/` (API: `globaldem?demtype=SRTMGL1`), no login, easiest, **public domain** (NASA/USGS). Recommended.
  - **NASA EarthData** — SRTMGL1 v003 (`https://search.earthdata.nasa.gov/`), free login required.
  - **USGS EarthExplorer** — `https://earthexplorer.usgs.gov/` (SRTM 1 Arc-Second Global).
- **License:** public domain (U.S. Government / NASA/USGS). No attribution required (attribution courteous).
- **Processing:** clip to the study-area bbox (below), reproject to **UTM 60S (EPSG:32760)**, resample to
  **~100×100 cells** (≈ paper's 10,000-cell geometry; each cell ≈ 150–200 m → ~15–20 km extent, matching
  Ba town + immediate floodplain). Store the clipped GeoTIFF + its sha256 in the run record.

## 2. Roads / buildings / shelters — OpenStreetMap

- **Source:** Geofabrik Fiji extract — `https://download.geofabrik.de/australia-oceania/fiji-latest.osm.pbf`.
- **License:** **ODbL** (OpenStreetMap) — attribution required: "© OpenStreetMap contributors". Record in FINDINGS.
- **Clip bbox** (study area; lon/lat WGS-84): **lon [177.60, 177.78], lat [-17.62, -17.48]** (Ba town +
  floodplain; refine to the catchment once the DEM is inspected). Tool: `osmium extract -b 177.60,-17.62,177.78,-17.48 fiji-latest.osm.pbf -o ba.osm.pbf`.
- **Layers to extract:**
  - **Roads** (`highway=*`) → `GeoNetwork` for shortest-path evacuation routing.
  - **Buildings** (`building=*`) → agent start cells (where the n=100 humans begin).
  - **River** (`waterway=river` / `natural=water`, the **Ba River**) → flood source / low cells (cross-check vs DEM).
  - **Shelters / evacuation centres** → target cells: `amenity=shelter`, and Fiji evacuation centres are
    typically **schools / community halls / churches** on higher ground (`amenity=school|community_centre|place_of_worship`).
    Select those on higher DEM cells. The paper's shelters are the high-ground safe destinations.

## 3. Optional cross-check (not required for #10, strengthens FINDINGS)

- **Ba River catchment boundary** / historical flood extent (2009/2012 Ba floods) for visual validation
  of the bathtub inundation footprint — e.g. Fiji government / PacGeo (`https://pacgeo.org/`), or the
  paper's own figures. Used only to sanity-check that the simulated flood covers the real floodplain.

## 4. What the user needs to provide / run (environment-dependent)

1. Download the SRTM tile **S18E177** (OpenTopography) and the **Geofabrik Fiji** OSM extract.
2. `uv sync --extra gis` (rasterio/pyproj/geopandas/shapely) — already installs cleanly in this repo.
3. Place inputs under `data/anshuka_ba/` (gitignored — large binaries are not committed; their **sha256
   + provenance** are recorded in FINDINGS for reproducibility).
4. Run the validation block in the [design spec](../../superpowers/specs/2026-06-24-anshuka-real-dem-design.md).

## Acquisition checklist

- [ ] SRTM `S18E177` GeoTIFF downloaded (source + date noted)
- [ ] Geofabrik `fiji-latest.osm.pbf` downloaded (date noted — OSM changes)
- [ ] OSM clipped to the Ba bbox; roads/buildings/shelters/river extracted
- [ ] DEM reprojected to EPSG:32760, clipped, resampled to ~100×100
- [ ] input sha256 + licenses (SRTM public-domain, OSM ODbL) recorded for the L3 bundle
