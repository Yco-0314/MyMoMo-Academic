# GIS codegen B4 (story -> GISModelSpec) — Locked expectations

**Locked:** 2026-06-17, BEFORE running the real LLM extractor. Anti-fabrication:
write down what the extractor SHOULD produce for reference stories first, then run
the real DeepSeek call and report match/mismatch honestly.

## Reference stories -> expected GISModelSpec

| # | Story | Expected spatial_type | Expected mechanism | Expected data_path |
|---|---|---|---|---|
| S1 | "Simulate an epidemic spreading over the **population density raster** of a city." | `raster` | `sir` | `""` |
| S2 | "Model commuters **routing on a city road network** loaded from `/tmp/roads.shp`." | `network` | `routing_load` | `/tmp/roads.shp` |
| S3 | "An opinion-dynamics model on a **random small-world network** of agents." | (not GIS — intent axis returns is_gis=False; not sent to the extractor) | — | — |

## Full-loop expectation

For S1 (fully runnable, synthetic raster): story → extract → render → **run the
generated model → the spatial-spread gate PASSES**. This is the end-to-end
autonomous "one sentence → GIS model".

## Verdict rule

The extractor **succeeds** on a story if the produced spec matches the expected
spatial_type + mechanism (+ data_path when named). Any mismatch is reported as a
miss, not glossed. The LLM is non-deterministic; a miss is recorded with the actual
output.
