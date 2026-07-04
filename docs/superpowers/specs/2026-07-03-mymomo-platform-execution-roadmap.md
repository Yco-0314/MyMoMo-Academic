# MyMoMo Platform Execution Roadmap

**Date:** 2026-07-03
**Scope:** Public MyMoMo-GIS-Academic execution order for the larger MyMoMo /
unified ABM platform direction.

## Purpose

This roadmap turns the previously discussed large plans into an executable
queue. It is not a new runtime abstraction and not a promise to build a
monolithic platform in one phase. It defines how Codex and Claude should move
from the current GISABM base toward a broader unified physical, social, and
biological simulation platform without losing the project's gate-first evidence
discipline.

The execution rule is:

```text
large direction
-> one small phase
-> written spec
-> implementation plan
-> tests and deterministic gate
-> merge
-> status update
-> next phase
```

## Current Position

The public line already has a strong GISABM spine:

- coupled raster/network/social/point/polygon/temporal/dynamic GIS adapters;
- dynamic flood, congestion, and incident moving-agent lifecycles;
- GIS codegen registry and runnable templates for the main synthetic cells;
- NetLogo-inspired topology, focal, coverage, and semantic-layer work;
- MIR v0 open/closed semantic contract on the public side;
- manifest-backed observed raster, traffic count, official traffic, and
  official incident reproducibility packs;
- timestamp-to-simulation-clock incident bridge;
- deterministic gates and base-engine zero-change oracles.

The risk now is not missing features. The risk is executing the larger vision as
one broad narrative without enough small, testable evidence. This roadmap keeps
the system advancing through bounded proof cells.

## Execution Lanes

### Lane A: GISABM Real-Data Validity

**Goal:** Move selected synthetic or official-style cells toward bounded,
auditable official samples.

**Next task:** Official Incident Real Sample Pack Phase 1.

**Success signal:** A small real official incident sample is manifest-backed,
checksum-verified, mapped from timestamps to ticks, and routed through the
existing incident intake/effect smoke without claiming traffic-flow validity.

**Not included:** full real-time feeds, production map matching, route-choice
validation, SUMO/MATSim parity, or congestion calibration.

### Lane B: GISABM Generalization

**Goal:** Prove the platform can transfer methods across spatial
representations, not only add one-off adapters.

**Next task:** Spatial Method Transfer Runtime Cell Phase 1.

**Success signal:** The registered `spatial_method_transfer` gap becomes a real
runtime cell with a deterministic gate showing the same method applied across at
least two compatible spatial representations.

**Not included:** automatic scientific method discovery or universal model
translation.

### Lane C: Evidence Foundry

**Goal:** Replace the AutoData-inspired framing with a MyMoMo-native evidence
system: challenge definitions, locked predictions, verdict bundles, refutation
records, and reproducibility manifests.

**Next task:** Evidence Foundry Challenge Harness Phase 2.

**Success signal:** A challenge pack can define claims, expected evidence,
allowed data, gate commands, verdict fields, and failure reporting without being
tied to one paper reproduction.

**Not included:** autonomous paper reproduction by Codex when Claude owns that
work, or private-study disclosure.

### Lane D: NetLogo Semantics And Model Migration

**Goal:** Turn the NetLogo semantic layer into concrete migration capability.

**Next task:** NetLogo Semantic Migration Gate Phase 1.

**Success signal:** A small NetLogo-like semantic model spec can round-trip
through MyMoMo's semantic/MIR/codegen surfaces into a runnable model with a
gate, while preserving declared patches/turtles/links/ticks/global parameters.

**Not included:** full NetLogo parser compatibility or complete NetLogo
language execution.

### Lane E: Unified ABM Platform Bridge

**Goal:** Prepare the public MyMoMo academic line to serve the broader unified
platform covering social, physical, and biological/closed extension simulation.

**Next task:** Unified ABM Bridge Contract Phase 1.

**Success signal:** A bridge document and small schema clarify what public MIR,
GISABM, Evidence Foundry, NetLogo semantics, and closed extension/private components
exchange, without forcing all domains into one runtime.

**Not included:** a grand unified simulator, shared `CoupledModel`, 3D terrain
engine, virtual-cell runtime, or private closed extension artifacts.

### Lane F: Cross-Agent Continuity

**Goal:** Keep Codex and Claude Code able to hand work across limit stops,
branches, and private/public boundaries.

**Next task:** Keep using `AGENTS.md`, `CLAUDE.md`, and
`docs/agent-handoff-protocol.md` as the durable protocol. Update only when a
new rule has become stable.

**Success signal:** Every handoff includes branch, commit, changed files,
commands run with observed results, verification status, remaining task, and
forbidden base-engine diff status when relevant.

**Not included:** dumping long transcripts into `AGENTS.md`.

## Ordered Queue

1. **Official Incident Real Sample Pack Phase 1**
   - Owner: Codex.
   - Why first: it directly follows the timestamp clock bridge and strengthens
     the weakest incident-data boundary.
   - Output: spec, plan, runtime/fixture/tests if data is locally available,
     gate, docs, merge.

2. **Spatial Method Transfer Runtime Cell Phase 1**
   - Owner: Codex.
   - Why second: it turns the current registered nonrenderable gap into real
     generalized GISABM capability.
   - Output: runtime cell, deterministic gate, registry status update, docs.

3. **Evidence Foundry Challenge Harness Phase 2**
   - Owner: Codex for public harness; Claude for paper-reproduction payloads.
   - Why third: it gives all future reproductions and validation bridges a
     common evidence contract.
   - Output: challenge schema/manifest, gate, sample challenge, docs.

4. **NetLogo Semantic Migration Gate Phase 1**
   - Owner: Codex.
   - Why fourth: NetLogo semantics should become migration proof, not just
     architectural commentary.
   - Output: semantic model fixture, MIR/codegen bridge or adapter, gate.

5. **Unified ABM Bridge Contract Phase 1**
   - Owner: Codex for public contract; Claude/private side for closed extension details.
   - Why fifth: the unified platform needs stable public evidence/MIR/GIS
     contracts before runtime unification.
   - Output: public bridge schema or contract doc, no private artifact leakage.

6. **3D Terrain / Physical-Space Architecture**
   - Owner: later Codex phase.
   - Why later: 3D becomes useful after the real-data, method-transfer, evidence,
     and semantic-contract surfaces are clearer.
   - Output: terrain/mesh/DEM bridge spec before any renderer or 3D engine.

## Parking Lot

These should not be pulled forward unless explicitly requested:

- formal Anshuka P5 locked rerun from the private addendum;
- full official incident or traffic feeds;
- production map matching;
- traffic-flow validity, capacity, or BPR calibration;
- full NetLogo parser compatibility;
- grand `CoupledModel` extraction;
- unified physical/social/biological runtime;
- private closed extension implementation details in the public repo.

## Phase Template

Every future phase should state:

- **Claim:** what the phase proves.
- **Boundary:** what it explicitly does not prove.
- **Data contract:** fixtures, manifest schema, checksums, provenance.
- **Runtime contract:** public functions/classes and expected outputs.
- **Gate:** deterministic pass/fail signature.
- **Tests:** targeted, adjacent, full GIS where relevant.
- **Base-engine proof:** forbidden diff and oracle commands when code changes.
- **Handoff:** Codex/Claude owner and next command.

## Verification Standard

For code phases, completion means:

```text
targeted tests pass
full relevant suite passes
SCIENCE GATE: PASS
ENGINE ORACLE: PASS
non-GIS base suite checked when relevant
forbidden base-engine diff is empty
docs updated
branch merged
handoff state clear
```

For documentation-only phases, completion means:

```text
spec is committed
incomplete-marker scan is clean
scope boundaries are explicit
next implementation phase is named
```

## Strategic Boundary

MyMoMo-GIS-Academic remains the public academic wedge. It should expose the
reusable runtime, MIR, GIS, validation, evidence, and migration contracts that
can serve the broader unified ABM platform. It should not expose private closed extension
assets, private paper-reproduction artifacts, or speculative unified-platform
runtime designs before there is a small gate-backed contract to justify them.
