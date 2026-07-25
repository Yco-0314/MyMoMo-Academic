# Public v4 Contract Projection Design

**Status:** Approved for implementation through the previously authorized public
projection sequence.
**Date:** 2026-07-25

## Purpose

Publish the open semantic contract needed to describe and revise a GIS ABM,
plus one bounded proof that an eligible synthetic GIS contract can be executed
deterministically.  This is a public v4 projection of the unified-platform
contract seam, not a release of the private process runner.

## Chosen Shape

The projection has two layers:

1. `abm_auto.mir._model_contract` owns canonical JSON, identity and revision
   digests, semantic patching, locks, and the quick-to-research lifecycle
   boundary.  It is pure Python and does not import GIS.
2. `abm_auto.gis._contract_execution` owns the one GIS adapter.  It accepts an
   exact, unlocked, quick `NaturalLanguageModelContract` that losslessly maps to
   a synthetic `raster_sir` `GISModelSpec`, builds the known synthetic raster in
   process, calls the trusted raster SIR runtime directly, and returns a small
   immutable receipt.

The execution path is deliberately direct:

```text
contract -> MIR -> GISModelSpec -> RasterSpace -> run_raster_sir -> gate -> receipt
```

There is no template rendering, generated-code execution, subprocess, external
file, network request, natural-language extraction, real-data path, GAMA
interoperability claim, or scientific-reproduction verdict.

## Eligibility Contract

Only the following exact contract shape may run:

- `mode == "quick"` and `lock.status == "unlocked"`;
- a lossless `mir_to_gis_spec(contract.mir)` round trip;
- `capability == "raster_sir"`, `spatial_type == "raster"`, and
  `mechanism == "sir"`;
- empty `data_path` (the fixture is synthetic);
- scalar `seed` and `steps` values accepted by `GISModelSpec`.

All other contracts are rejected with deterministic issue text.  Eligibility is
not a scientific quality judgment; it only bounds the executable public cell.

## Receipt and Evidence Boundary

The direct receipt records only contract identity/revision, MIR digest,
capability, gate result, a compact deterministic result summary, and the
`quick_exploratory` evidence scope.  It must not include code hashes, stdout,
stderr, process status, filesystem paths, or arbitrary model output.

Passing the receipt means that this constrained semantic contract selected the
known synthetic raster-SIR runtime and produced its deterministic gate result.
It does not prove natural-language understanding, GAMA compatibility, real-data
fitness, causal validity, or a published-study reproduction.

## Packaging Decision

This projection does not change the existing public wheel/sdist exclusion of
`abm_auto/gis`.  The implementation is source-visible and tested in the v4
repository with the GIS extra; making GIS a packaged artifact is a separate
release and dependency-surface decision, not an incidental side effect of this
contract seam.

## Verification

- Unit tests cover canonical contract identity, semantic patch equivalence,
  lifecycle transitions, malformed JSON, and the direct adapter's eligibility.
- The synthetic raster-SIR contract is run twice and must yield the same receipt
  and gate summary.
- Contracts with real paths, a locked state, a different capability, or a
  non-lossless GIS projection must fail before simulation.
- The full GIS suite, base-engine science/oracle gates, protected-path diff, and
  public sanitizer must remain clean.
