# Terrain Bridge Manifest Status

Phase 1 adds a public terrain/DEM bridge contract for the later 3D and
physical-space architecture lane.

The seed fixture is a tiny committed ASCII heightfield with a SHA-256 checksum.
The manifest declares coordinate units, vertical units, vertical datum,
consumers, boundary rules, and verification metadata.

Boundary: this is not a 3D renderer, not a mesh generator, not a physical
terrain solver, and not a physical simulation certificate. The committed
heightfield is synthetic and does not claim real-world terrain accuracy.

Phase 2 adds deterministic derived metrics for the committed ASCII heightfield:
rows, columns, min/max/mean elevation, relief, and maximum horizontal/vertical
neighbor delta. This proves the bridge can be consumed computationally, but it
still does not render terrain, build meshes, run hydrology or physics, or
validate real-world terrain accuracy.

Phase 3 adds local GeoTIFF DEM metrics for manifests with
`terrain_source.kind == "dem_raster"`. The metrics path lazily reads band 1 via
`rasterio`, checks the declared `coordinate_frame.grid_shape`, ignores masked
nodata cells, and reports the same deterministic rows/cols/min/max/mean/relief
and neighbor-delta metrics used by ASCII heightfields. This is the first real
terrain-data ingestion bridge, but it remains local-file only: no remote DEM
download, no reprojection, no resampling, no terrain rendering, no mesh
generation, no hydrology/physics, and no real-world accuracy certificate.
