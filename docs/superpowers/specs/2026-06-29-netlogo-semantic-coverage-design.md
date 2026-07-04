# NetLogo Semantic Coverage Phase 1 - Design Spec

**Status:** Draft for review.
**Date:** 2026-06-29
**Repo:** MyMoMo-GIS-Academic
**Parent:** `2026-06-29-abm-platform-comparative-architecture-map.md`

## Summary

Build a NetLogo semantic coverage map before adding any broader NetLogo parser,
exporter, or runnable template. The output of Phase 1 is a reviewer-readable
truth table that maps NetLogo language and model-library concepts to the current
MyMoMo MIR/platform/GIS/oracle surface.

This phase is documentation and evidence mapping only. It does not implement a
NetLogo interpreter, does not extend `abm_auto/ingest/netlogo.py`, does not add
codegen templates, and does not claim that arbitrary `.nlogo` models can run in
MyMoMo.

## Why

NetLogo is the strongest reference for compact ABM authoring semantics:
observer, turtles, patches, links, breeds, agentsets, `ask`, `tick`, interface
widgets, plots, BehaviorSpace, and extension-backed domain primitives. MyMoMo
already has pieces that touch this space:

- a `.nlogo` / `.nlogox` to `story.md` ingest path;
- a neutral Mesa-shaped platform floor (`Agent`, `AgentSet`, `DataCollector`,
  `AgentModel`, `StagedAgentModel`);
- MIR v0 as the open semantic contract;
- NetLogo oracle support for selected BehaviorSpace experiments;
- NetLogo-faithful topology and GIS-extension parity cells.

Those pieces are useful, but they are not the same thing as NetLogo semantic
coverage. Without an explicit map, it is easy to overclaim: a parser that reads
breeds is not an executor for `ask`; a GIS parity primitive is not full NetLogo
language parity; an oracle fixture is not universal compatibility.

The goal is to make the boundary machine-checkable enough for future work:
what is native, what is partial, what is oracle-backed, what is missing, and
what should stay out of scope.

## Current Evidence

### Existing NetLogo ingest

`abm_auto/ingest/netlogo.py` currently parses:

- `.nlogo` text sections and NetLogo 7+ `.nlogox` XML;
- Info and Code tabs;
- `globals`;
- `breed [...]`;
- `<breed>-own`;
- `turtles-own`;
- `patches-own` presence;
- sliders;
- plots;
- world width, height, and wrapping flags where available.

It then emits a `story.md` scaffold. It does not interpret NetLogo procedures,
agentset expressions, reporter semantics, random-number semantics, or extension
commands.

### Existing MIR surface

`abm_auto/mir/_schema.py` provides stable open clusters:

- `metadata`;
- `entities`;
- `state`;
- `space`;
- `relations`;
- `processes`;
- `layers`;
- `metrics`;
- `run`;
- `fidelity`;
- `trace`;
- `extensions`.

This is enough to record many NetLogo concepts, but Phase 1 must not pretend
that a formal NetLogo-to-MIR mapping already exists. The coverage map should
name where each concept would live and mark unsupported mappings explicitly.

### Existing platform surface

`abm_auto/_platform.py` provides:

- `Agent`;
- `AgentSet`;
- deterministic `sequential` and `random_order` activation;
- `AgentSet.do(...)` for named stages;
- `DataCollector`;
- `RunReporter`;
- `AgentModel`;
- `StagedAgentModel`.

This is close to Mesa-style lifecycle semantics. It can support many NetLogo
ports, but it does not currently expose first-class NetLogo observer, turtle,
patch, link, world, or agentset expression objects.

### Existing oracle and parity support

Current NetLogo-related evidence includes:

- `abm_auto/verification/netlogo_oracle.py`, which can run BehaviorSpace
  experiments through NetLogo headless when a local NetLogo install is present;
- committed NetLogo fixture outputs for `Virus_on_a_Network.nlogo`;
- `netlogo_spatially_clustered` as a topology adapter with oracle-backed tests;
- GIS-extension parity cells for topology clip, raster focal operations, and
  raster coverage in the GIS codegen registry.

These are strong local parity points. They should be recorded as oracle-backed
or native capability evidence, not generalized into full language support.

## Deliverable

Add a new documentation artifact in a follow-up implementation phase:

```text
docs/reproduce/netlogo-semantic-coverage/STATUS.md
```

The document should contain a coverage table with one row per NetLogo concept.
Each row should use the same fixed schema:

| Field | Meaning |
|---|---|
| `concept` | NetLogo language or model-library concept |
| `netlogo_meaning` | What the concept means in NetLogo terms |
| `current_my_momo_surface` | Existing MyMoMo file, class, gate, or doc that touches it |
| `support_status` | One of the fixed statuses below |
| `mir_mapping` | Where the concept would live in MIR, if applicable |
| `platform_mapping` | Where the concept would live in the platform floor, if applicable |
| `evidence_level` | E0-E6 from the comparative architecture map |
| `evidence` | Test, gate, fixture, oracle, or doc proving the row |
| `next_action` | Implement, leave-as-is, bridge, oracle-test, or defer |
| `boundary_note` | What the row does not prove |

## Fixed Status Values

The coverage table must use only these status values:

- `native`: directly represented and runnable in MyMoMo today;
- `partial`: parsed or representable, but not semantically executable end to end;
- `oracle_backed`: compared against NetLogo for a bounded fixture or behavior;
- `gis_parity`: implemented for the NetLogo GIS-extension analogue, not general
  NetLogo language coverage;
- `missing`: meaningful for NetLogo parity but not currently represented;
- `bridge_candidate`: should probably call or compare against an external tool;
- `out_of_scope`: not needed for current reproduction or platform pressure.

## Initial Coverage Rows

The first implementation should cover at least these rows.

| Concept | Expected status | Current surface | Boundary |
|---|---|---|---|
| `.nlogo` / `.nlogox` file ingest | `partial` | `abm_auto/ingest/netlogo.py` | Reads structure, does not execute procedures |
| Info tab | `partial` | `to_story_md(...)` | Summarized into story text, not a formal claim contract |
| Code tab | `partial` | `NetLogoModel.code_text` | Stored as text; no AST or interpreter |
| `globals` | `partial` | parser extracts names | No type/default/range semantics except sliders |
| `breed` | `partial` | parser extracts singular/plural names | No breed-specific activation semantics |
| `turtles-own` / `<breed>-own` | `partial` | parser extracts variable names | No typed state schema or update semantics |
| `patches-own` | `partial` | parser detects patch state | No patch grid object or patch update lifecycle |
| turtles | `missing` | platform `Agent` is adjacent | No first-class turtle API or heading/movement semantics |
| patches | `missing` | GIS/raster/grid concepts are adjacent | No NetLogo patch coordinate/world semantics |
| links | `missing` | network concepts are adjacent | No first-class directed/undirected NetLogo link agents |
| observer | `missing` | `AgentModel` is adjacent | No formal observer command context |
| agentsets | `missing` | `AgentSet` is adjacent | No NetLogo expression/filter semantics |
| `ask` | `missing` | `AgentSet.do(...)` is adjacent | No NetLogo ask ordering/context semantics |
| `setup` / `go` | `partial` | `AgentModel.run` and staged lifecycle | No procedure parser or button binding |
| `tick` | `partial` | model `t` and reporter records | No exact NetLogo tick/reset-ticks mapping |
| sliders | `partial` | parser extracts slider ranges/defaults | No automatic parameter binding into runnable specs |
| switches/choosers/input boxes | `missing` | none | Not parsed as structured controls |
| monitors | `missing` | `DataCollector` is adjacent | No monitor expression parser |
| plots | `partial` | parser extracts plot names | No plot pen or update-command semantics |
| BehaviorSpace | `oracle_backed` | `netlogo_oracle.py` | Runs selected experiments only |
| random-number semantics | `oracle_backed` | ADR-006 notes integer-random mismatch | Known bounded mismatch, not full parity |
| spatially clustered network | `oracle_backed` | `netlogo_spatially_clustered` tests | One topology primitive only |
| NetLogo GIS topology | `gis_parity` | `topology_clip` registry capability | GIS-extension analogue only |
| NetLogo GIS focal raster | `gis_parity` | `raster_focal` registry capability | GIS-extension analogue only |
| NetLogo GIS coverage | `gis_parity` | `raster_coverage` registry capability | GIS-extension analogue only |
| NetLogo extensions other than GIS | `missing` | none | Extension-by-extension triage needed |
| HubNet / UI interaction | `out_of_scope` | none | Not relevant to current reproduction loop |
| 3D view | `out_of_scope` | none | Deferred until 3D platform strategy |

## Implementation Plan

Phase 1 implementation should be small and documentation-only:

1. Create `docs/reproduce/netlogo-semantic-coverage/STATUS.md`.
2. Fill the coverage table above with evidence links to current files, tests,
   ADRs, and specs.
3. Include a short "Do not overclaim" section stating that this is semantic
   coverage analysis, not NetLogo compatibility.
4. Include a "Next executable cells" section ranking the first three useful
   follow-up tasks.
5. Run lightweight documentation checks only.

Suggested follow-up ranking:

1. `agentset_ask_tick` executable cell: a tiny turtle/agentset/tick lifecycle
   gate, implemented natively on the platform floor.
2. `netlogo_controls_to_spec` extractor cell: map sliders, switches, choosers,
   monitors, and plots into a structured non-executing spec.
3. `behaviorspace_manifest` bridge cell: record NetLogo headless command,
   experiment name, output table, and reduction metrics as a rerunnable manifest.

## Non-Goals

- No full NetLogo parser.
- No NetLogo interpreter.
- No `.nlogo` to Python transpiler.
- No runnable template for arbitrary NetLogo models.
- No GAMA semantic coverage in this phase.
- No closed extension work; Claude is handling that track.
- No edits to `abm_auto/runtime/`, `abm_auto/codegen/`,
  `abm_auto/calibration/`, `abm_auto/agents/`, or `abm_auto/pipeline/`.
- No claim that GIS-extension parity means full NetLogo language parity.
- No claim that oracle-backed fixture parity means general model equivalence.

## Validation For This Spec

Because this phase is documentation-only, validation is:

```text
rg -n "[U]NRESOLVED|[N]EEDS-DECISION|[F]ILL-ME" docs/superpowers/specs/2026-06-29-netlogo-semantic-coverage-design.md
git diff --check
```

The follow-up implementation phase should add the `STATUS.md` artifact and run:

```text
rg -n "[U]NRESOLVED|[N]EEDS-DECISION|[F]ILL-ME" docs/reproduce/netlogo-semantic-coverage/STATUS.md
git diff --check
git diff --name-only HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

Runtime tests and engine oracle runs are not required for a documentation-only
coverage table unless code changes are introduced.

## Review Questions

1. Are the fixed status values sufficient, or should `parsed_only` be split out
   from `partial`?
2. Should `agentset_ask_tick` be the first executable follow-up, or should the
   next task stay documentation-only and cover GAMA first?
3. Should BehaviorSpace be treated as an audit baseline only, or also as a
   future experiment-manifest bridge?
