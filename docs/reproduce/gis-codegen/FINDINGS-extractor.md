# GIS codegen B4 (story -> GISModelSpec) — FINDINGS

**Run:** 2026-06-17, real DeepSeek (`deepseek-chat`), AFTER locking expectations
([PREDICTIONS-extractor-locked.md](PREDICTIONS-extractor-locked.md)).

## Result vs locked expectations

| Story | Intent | Extracted spec | vs locked | Full loop |
|---|---|---|---|---|
| S1 epidemic on density **raster** | GIS, raster ✅ | `raster` / `sir` ✅ | **MATCH** | **generated model ran → spatial gate PASS** (corr=0.44, Moran's I=0.64) |
| S2 commuters on a **road network** shapefile | GIS, network ✅ | `network` / `routing_load`, `/tmp/roads.shp` ✅ | **MATCH** | fidelity gate PASS (run needs the real shapefile) |
| S3 opinion dynamics on a **random small-world network** | not GIS ✅ | (not sent to extractor) | **MATCH** | stays on the non-GIS path |

**All three matched the locked expectations.**

## What this demonstrates

The **end-to-end autonomous loop works**: a plain sentence → intent axis (GIS?) →
real LLM extraction → typed GISModelSpec → deterministic template → fidelity gate →
**a runnable GIS model whose science gate passes** (S1). The non-GIS story is
correctly left on the normal path (S3) — the routing default holds.

## Honest notes

- The LLM is **non-deterministic**; this run matched, but extraction is not
  guaranteed every time. The `GISModelSpec.validate()` + the fidelity gate are the
  deterministic guards that catch a bad extraction before it runs.
- Only **raster + network** templates exist; raster is fully runnable (synthetic),
  network needs a real shapefile to execute (the spec/render/gate are verified).
- As of 2026-06-19, GIS codegen has a deterministic capability registry. It
  records runtime-only cells from the coupled seam (`flood_evacuation`,
  `social_spatial_contagion`, point/polygon cells, temporal flood, and dynamic
  flood) but marks them `renderable=False`. The extractor and renderer fail
  loudly for those cells instead of generating unsupported coupled/dynamic code.
- This is a small reference set (3 stories), not a large benchmark.

## Conclusion

Sub-project B is complete end-to-end for raster + network: **one sentence → GIS
model**, verified against locked expectations with a real LLM, guarded by
deterministic validation + a fidelity gate.
