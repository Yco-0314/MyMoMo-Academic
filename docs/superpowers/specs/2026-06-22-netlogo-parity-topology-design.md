# NetLogo GIS Parity — Topology / Focal / Coverage — Design Spec

**Status:** Draft. **Date:** 2026-06-22. **Repo:** MyMoMo-GIS-Academic.
**Parent:** [ADR-019](../../decisions/ADR-019-gis-abm-platform-vision.md) — fills
"coupling matrix" layer cells the NetLogo `gis` extension exposes that we lack.

## Why

NetLogo's `gis` extension exposes three capability families we currently don't:

1. **Full DE-9IM vector topology** (`gis:have-relationship?`, `gis:relationship-of`,
   `gis:intersecting`, `gis:contained-by?`, …). We only do point-in-polygon, nearest,
   and sample-along-edge — unlocking line×polygon / polygon×polygon coupling cells
   is the highest-ROI gap, and shapely's STRtree + relate already gives it.
2. **Raster focal operations** (`gis:convolve`, `gis:resample`, sampling-method).
   We only have point sampling and along-edge max.
3. **Areal coverage** (`gis:apply-coverage`): polygon attribute → raster, area-
   weighted. We can group points to polygons but cannot rasterise polygon attrs.

Each gap maps to a registered ADR-019 coupling-matrix cell.

## Hard constraints (unchanged)

1. **Zero-change to `abm_auto/runtime/`, `codegen/`, `calibration/`, `agents/`,
   `pipeline/`.** Additive only.
2. GIS deps stay in `[gis]` extra; lazy import inside `abm_auto/gis/`.
3. Predictions locked before runs; tests pass / fail / skip read from real output.
4. **No conflict with Codex's `codex/real-data-validation-pack-v2*` branches.** This
   work lands on `feat/netlogo-parity-topology` off `main` (14e668a); the Codex
   worktree is not touched.

## Phase 1 (this spec ships) — DE-9IM vector topology

### P1.1 Topology primitives — extend `abm_auto/gis/_coupling.py`

shapely already implements DE-9IM. Add small operators on shapely geometry lists:

```python
def intersects(a, b) -> bool: ...
def contains(a, b) -> bool: ...   # a contains b
def within(a, b) -> bool: ...     # a within b (a inside b)
def touches(a, b) -> bool: ...
def crosses(a, b) -> bool: ...
def overlaps(a, b) -> bool: ...
def relate(a, b) -> str: ...      # DE-9IM matrix string (e.g. "212101212")

def features_intersecting(features, query) -> list[int]:
    """Indices of features whose geometry intersects `query`."""

def features_containing(features, point) -> list[int]: ...
```

`features_intersecting` uses `shapely.STRtree` so it scales (NetLogo's intersect
loops on the JVM are slower than an indexed query). Pure functions; no I/O.

### P1.2 Two new coupling cells (each with its own gate)

| Cell | Layers | Operator | Gate |
|---|---|---|---|
| **Line-on-polygon clip** | polyline layer × polygon layer | `lines_in_polygon(lines, polygon)` (clipped length sum) | `line_polygon_gate`: lines inside polygon → positive length; lines outside → zero |
| **Polygon-polygon overlap** | polygon layer × polygon layer | `polygon_overlap_areas(a_polys, b_polys)` (pairwise intersection area) | `polygon_overlap_gate`: identical input → full self-overlap; disjoint → zero |

Both live in `_coupling.py` (next to existing cross-layer ops) so the existing
"operators-are-the-seam" pattern stays.

### P1.3 Tests (TDD, synthetic geometry; no real data)

- `tests/gis/test_topology.py` — pinpoint each primitive: square containing point,
  intersect of crossing lines, touching squares not overlapping, identical squares
  fully overlapping, STRtree-indexed `features_intersecting` returns the correct
  indices on a 25-feature grid.
- `tests/gis/test_topology_couplings.py` — the two new coupling gates pass on a
  hand-built case and FAIL on a disjoint case.

### P1.4 STATUS update

`docs/reproduce/coupled-seam/STATUS.md` — add the two new adapter rows. Done as a
small commit AFTER tests pass.

## Phase 2 (spec only here — separate plan/commits)

Raster focal operations: `convolve(raster, kernel)` (scipy `ndimage.convolve` or
hand-rolled to keep dep light), `resample(raster, new_transform, method)`,
`raster_sample(raster, geom)` (point/box). Gate: known kernel on a known field
gives the known answer; resample to identity is byte-stable.

## Phase 3 (spec only here)

`apply_coverage(polygons, attr_name, raster_template) -> RasterField`:
area-weighted polygon attribute → raster cells. Gate: covering a single polygon
with constant attribute = constant raster (within tol); two non-overlapping
polygons sum to per-cell weighted average.

## Validation (Phase 1)

```
.venv/bin/python -m pytest tests/gis/test_topology.py tests/gis/test_topology_couplings.py -q
.venv/bin/python -m pytest tests/gis -q
.venv/bin/python engine_oracle.py --science
.venv/bin/python engine_oracle.py --check
.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
git diff --name-only main..HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline   # must be EMPTY
```

## Non-goals

- No registry / codegen template for these cells (deferred — keep this PR focused).
- No real GIS data; synthetic geometry only.
- No edits to Codex's `codex/real-data-validation-pack-v2*` branches.
- No `CoupledModel` extraction.
- Phase 2 (focal) and Phase 3 (coverage) are spec-only here; they ship in
  separate branches once Phase 1 is merged.
