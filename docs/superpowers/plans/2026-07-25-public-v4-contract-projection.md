# Public v4 Contract Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a pure MIR model-contract layer and a bounded, direct synthetic
Raster-SIR contract execution seam in the public v4 GIS projection.

**Architecture:** Apply the public-safe ADR-026 typed-outcome foundation first.
Then add the pure MIR contract records and a GIS-owned adapter that calls the
reference raster SIR runtime in process.  Keep every execution concern that
requires rendering or a subprocess private.

**Tech Stack:** Python 3.11, dataclasses, canonical JSON, hashlib, NumPy,
RasterSpace, existing GIS gates, pytest.

---

### Task 1: Reconcile the public ADR-026 foundation

**Files:**
- Modify: typed-outcome, lock-review, repro-bundle, study-corpus modules
- Add: public-neutral ADR-026 documents, synthetic typed-outcome fixture, tests

- [ ] Apply the already-tested generic public v3 ADR-026 delta without its
  branch-specific plan/spec filenames.
- [ ] Run the typed-outcome and lock-review test selection.
- [ ] Commit the reconciled public foundation.

### Task 2: Publish the pure MIR model-contract layer

**Files:**
- Create: `abm_auto/mir/_model_contract.py`
- Modify: `abm_auto/mir/__init__.py`
- Add: `tests/test_natural_language_model_contract.py`

- [ ] Port the public-safe deterministic model-contract records, canonical
  digests, strict JSON loading, semantic patch equivalence, and lifecycle
  guards from the private source.
- [ ] Exclude all GAMA-specific test/adapter surface.
- [ ] Run the dedicated model-contract tests.
- [ ] Commit the pure contract core.

### Task 3: Add the direct synthetic GIS adapter

**Files:**
- Create: `abm_auto/gis/_contract_execution.py`
- Add: `tests/gis/test_contract_execution.py`

- [ ] Write failing tests for the eligible raster-SIR contract, deterministic
  repeatability, and rejection of locked, real-data, non-raster-SIR, and
  non-lossless contracts.
- [ ] Implement pure eligibility plus direct in-process RasterSpace,
  `run_raster_sir`, and `spatial_spread_gate` execution.
- [ ] Return a minimal immutable receipt bounded to `quick_exploratory`.
- [ ] Run the adapter tests and commit.

### Task 4: Public release verification

**Files:**
- Modify: `docs/superpowers/specs/2026-07-25-public-v4-contract-projection-design.md`

- [ ] Run focused, GIS, and full test suites plus both engine oracles.
- [ ] Verify no protected base-engine files changed.
- [ ] Run the public sanitizer against all changed files.
- [ ] Obtain specification and quality reviews, push the reconciled branch, and
  create a draft public v4 pull request.
