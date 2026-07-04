# NetLogo Semantic Coverage Status

**Date:** 2026-06-30
**Scope:** Semantic coverage map for NetLogo concepts in MyMoMo.
**Related spec:** `docs/superpowers/specs/2026-06-29-netlogo-semantic-coverage-design.md`

## Verdict

Phase 1 now has fifteen native executable cells:

```text
agentset_ask_tick
patch_grid_cell
netlogo_metric_expression_gate
link_agent_cell
netlogo_link_metric_gate
netlogo_link_predicate_gate
netlogo_turtle_patch_position_gate
netlogo_patch_neighbors_gate
netlogo_turtles_on_patch_gate
netlogo_sprout_gate
netlogo_heading_movement_gate
netlogo_radius_query_gate
netlogo_diffuse_gate
netlogo_other_agentset_gate
netlogo_virus_network_setup_slice_gate
```

This proves that MyMoMo can natively express a small NetLogo-like lifecycle over
the neutral platform: turtle-like agents, breed-filtered agentsets, ask over a
snapshot, stateful patch grid cells with coordinate lookup, explicit
tick/reset-ticks, globals, monitor collection, minimal link agents, and one
limited Virus-style metric expression family plus tiny link metric and
link-neighbor predicate families, integer-only turtle position over patches,
bounded patch-neighbor reporters, scan-based patch-local turtle aggregation,
minimal patch-origin turtle creation, cardinal-only heading movement, and
bounded radius queries plus scalar patch diffusion and exclude-self turtle
agentsets. The first fixture-driven Virus setup slice now also covers seeded
`one_of` / `n_of` selection and nearest-unlinked link creation as explicit
Python semantics.

Separately, a deterministic fixture gap audit now scans the committed
`Virus_on_a_Network.nlogo` fixture and reports supported semantic families plus
blocking gaps and unclassified Code-tab text. This is fixture pressure for
deciding the next cell; it is not a native `.nlogo` runner.

It does not prove full NetLogo compatibility. It does not parse procedures,
execute arbitrary `.nlogo` files, implement full link syntax, broader directed
link reporters, continuous heading movement, wrapping, diffuse, full sprout
parser/topology semantics, full sprout syntax/lifecycle, full `in-radius`
parsing, full agentset expression algebra, pen drawing, or reproduce NetLogo
random-number semantics. It also does not parse the fixture's `min-one-of` /
`distance` expressions from source.

## Implemented Evidence

| Evidence | Location | Meaning |
|---|---|---|
| Native semantic cell | `abm_auto/netlogo_semantics.py` | Minimal `NetLogoWorld`, `NetLogoTurtle`, and `NetLogoAgentSet` on top of `abm_auto._platform` |
| TDD gate | `tests/test_netlogo_semantics.py` | Pins ask snapshot, tick semantics, breed filters, globals, monitors, and seeded ask order |
| Patch grid cell | `tests/test_netlogo_semantics.py` | Pins native patches, patch state, coordinate lookup, patch agentsets, and ask-over-patches |
| Turtle patch position cell | `tests/test_netlogo_semantics.py` | Pins integer `xcor`/`ycor`, `setxy(...)`, and `patch_here()` over the native patch grid |
| Cardinal movement cell | `tests/test_netlogo_semantics.py` | Pins cardinal `heading`, `set_heading(...)`, `rt(...)`, `lt(...)`, and positive-integer `fd(...)` over bounded patches |
| Patch neighbors cell | `tests/test_netlogo_semantics.py` | Pins bounded `neighbors4()` and `neighbors()` on the native patch grid |
| Turtles-on-patch cell | `tests/test_netlogo_semantics.py` | Pins scan-based `turtles_here()` / `turtles_on(...)` patch-local aggregation |
| Sprout cell | `tests/test_netlogo_semantics.py` | Pins minimal patch-origin `sprout(...)` turtle creation at source patch coordinates |
| Radius query cell | `tests/test_netlogo_semantics.py` | Pins bounded integer-radius `patches_in_radius(...)` and `turtles_in_radius(...)` scans |
| Diffuse cell | `tests/test_netlogo_semantics.py` | Pins bounded synchronous scalar patch diffusion without wrapping |
| Other agentset cell | `tests/test_netlogo_semantics.py` | Pins exclude-self `other_than(...)` and `other_turtles_in_radius(...)` local interaction queries |
| Link agent cell | `tests/test_netlogo_semantics.py` | Pins native links, link state, endpoint lookup, link agentsets, ask-over-links, and undirected neighbor queries |
| Metric expression gate | `tests/test_netlogo_metric_expressions.py` | Pins native evaluation for Virus-style `count turtles with [...]` metrics and plot percentages |
| Link metric gate | `tests/test_netlogo_metric_expressions.py` | Pins native evaluation for `count links` and context-bound `count link-neighbors` metrics |
| Link predicate gate | `tests/test_netlogo_metric_expressions.py` | Pins native evaluation for context-bound `count link-neighbors with [...]` state predicates |
| Controls-to-spec cell | `tests/test_netlogo_controls.py` | Pins structured, non-executing Interface-tab controls ingest for sliders, switches, choosers, input boxes, monitors, plots, and plot pens |
| Controls-to-MIR adapter | `tests/test_netlogo_mir_adapter.py` | Pins non-executing mapping from `NetLogoControlsSpec` to open MIR `run.params`, `metrics`, and `trace` |
| BehaviorSpace manifest bridge | `tests/test_netlogo_behaviorspace_manifest.py` | Pins experiment metadata extraction, audit command packaging, tool availability, table reduction, and JSON manifest round-trip |
| BehaviorSpace CLI pack | `tests/test_netlogo_behaviorspace_cli_pack.py` | Pins reviewer-facing `manifest.json` + `MANIFEST.md` packaging through `abm-auto netlogo-behaviorspace-pack` |
| Virus setup random/network slice | `tests/test_netlogo_semantics.py` | Pins seeded `one_of` / `n_of` selection and nearest-unlinked link creation for a manual native Virus setup slice |
| Fixture gap audit | `tests/test_netlogo_gap_audit.py` | Pins a deterministic supported-vs-gap report for `Virus_on_a_Network.nlogo`, including native turtle/link/control/random/minimal-network support and explicit parser/procedure/layout gaps |
| Prior ingest evidence | `abm_auto/ingest/netlogo.py` | Parses some `.nlogo` / `.nlogox` structure into story scaffolds |
| Prior oracle evidence | `abm_auto/verification/netlogo_oracle.py` | Runs selected BehaviorSpace experiments through NetLogo headless when available |
| Prior GIS parity evidence | `tests/gis/test_codegen_netlogo_parity.py` | Covers NetLogo GIS-extension analogues for topology/focal/coverage |

## Coverage Table

| Concept | NetLogo meaning | Current MyMoMo surface | Status | MIR mapping | Platform mapping | Evidence level | Evidence | Next action | Boundary note |
|---|---|---|---|---|---|---|---|---|---|
| `.nlogo` / `.nlogox` file ingest | Read NetLogo model files | `abm_auto/ingest/netlogo.py` | `partial` | `metadata`, `processes`, `run`, `extensions` | none | E0 | parser tests via existing ingest path | leave-as-is until extractor work | Reads structure, does not execute procedures |
| Info tab | Human model explanation | `to_story_md(...)` | `partial` | `metadata.description`, `trace` | none | E0 | story conversion path | later map into claim contract | Text summary, not a formal claim object |
| Code tab | NetLogo procedures and declarations | `NetLogoModel.code_text` | `partial` | `processes`, `extensions` | none | E0 | raw code text retained | defer parser | Stored as text; no AST or interpreter |
| `globals` | Observer-level variables | ingest parser plus `NetLogoWorld.globals` | `native` | `state`, `run.params` | `NetLogoWorld.globals` | E0 | `test_breed_filtered_agentsets_globals_and_monitors_form_a_minimal_cell` | add typed controls later | Native dict only; no NetLogo scoping parser |
| `breed` | Named turtle subtype | ingest parser plus `NetLogoTurtle.breed` | `native` | `entities[].type` | `NetLogoTurtle.breed`, `with_breed(...)` | E0 | `tests/test_netlogo_semantics.py` | extend to breed-owned schema later | No full breed declaration lifecycle |
| `turtles-own` / `<breed>-own` | Turtle variables | parser extracts names; turtle state dict stores values | `partial` | `entities[].state` | `NetLogoTurtle.state` | E0 | parser plus native turtle state tests | add typed state schema | No declaration/type validation |
| `patches-own` | Patch variables | parser detects patch state plus `NetLogoPatch.state` | `native-minimal` | `space`, `state`, `layers` | `NetLogoPatch.state` | E0 | `tests/test_netlogo_semantics.py` | add typed patch state schema only when needed | Wrapping, diffuse, full sprout syntax/lifecycle, and continuous turtle movement are not implemented |
| turtles | Mobile NetLogo agents | `NetLogoTurtle`, integer `xcor`/`ycor`, cardinal `heading`, `setxy(...)`, `patch_here()`, positive-integer `fd(...)`, patch-local aggregation, bounded radius scans | `native-minimal` | `entities`, `space` | `Agent` subclass plus patch-grid lookup | E0 | `tests/test_netlogo_semantics.py` | add broader movement only when needed | Cardinal integer patch movement only; no continuous heading, pen, wrapping, collision, or broader turtle primitives |
| patches | Grid cells | `NetLogoPatch`, `NetLogoPatchSet`, `NetLogoWorld.create_patches(...)`, `patch_at(...)`, turtle `patch_here()`, bounded `neighbors4()` / `neighbors()`, `turtles_here()`, `sprout(...)`, bounded radius scans, `diffuse_patch_scalar(...)` | `native-minimal` | `space`, `layers`, `state` | `NetLogoPatch`, `NetLogoPatchSet` | E0 | `tests/test_netlogo_semantics.py` | add patch spatial primitives only when needed | No wrapping, full diffuse parser/topology semantics, full `in-radius` parser, or continuous heading-based turtle movement |
| links | Link agents between turtles | `NetLogoLink`, `NetLogoLinkSet`, `NetLogoWorld.create_link(...)`, `link_between(...)`, `link_neighbors(...)`, `create_link_with_nearest_unlinked(...)` | `native-minimal` | `relations`, `entities` | `NetLogoLink`, `NetLogoLinkSet` | E0 | `tests/test_netlogo_semantics.py`, `tests/test_netlogo_metric_expressions.py` | broaden directed/breed-specific link reporters only when fixtures require them | Directed neighbor reporters, link-breed parsing, source parsing for `min-one-of`/`distance`, layout, and full NetLogo link syntax are not implemented |
| observer | Global command context | `NetLogoWorld` | `partial` | `metadata`, `run`, `trace` | `AgentModel` subclass | E0 | `tests/test_netlogo_semantics.py` | keep thin | No NetLogo command context parser |
| agentsets | Dynamic sets of agents | `NetLogoAgentSet` | `native` | `entities` query expression in future | `NetLogoAgentSet.where`, `with_breed`, `other_than`, `one_of`, `n_of` | E0 | `tests/test_netlogo_semantics.py` | add more selectors when needed | Minimal filters and seeded selection only; no general NetLogo agentset parser/algebra |
| `ask` | Execute command over agentset | `NetLogoWorld.ask(...)` | `native` | `processes[].schedule` | ask over snapshot plus seeded order | E0 | ask snapshot/order tests | compare against NetLogo fixture later | Does not parse command blocks |
| `setup` / `go` | Button-bound model procedures | manual Python methods on world/model | `partial` | `processes`, `run` | `AgentModel.run` adjacent | E0 | platform tests plus semantic cell | defer procedure binding | No NetLogo procedure parser |
| `tick` | Advance model clock | `NetLogoWorld.tick`, `reset_ticks` | `native` | `run.params.time` in future | model `t` | E0 | explicit tick/reset test | add `tick_advance` only if needed | Integer ticks only |
| sliders | Interface parameters | `NetLogoControlsSpec.sliders` plus `netlogo_model_to_mir(...)` | `partial` | `run.params` | none | E0 | `tests/test_netlogo_controls.py`, `tests/test_netlogo_mir_adapter.py` | later DSL/codegen binding | Structured ingest and MIR packaging only; raw expressions are preserved, not evaluated |
| switches/choosers/input boxes | Interface controls | `NetLogoControlsSpec.switches`, `.choosers`, `.input_boxes` plus MIR adapter | `partial` | `run.params` | none | E0 | `tests/test_netlogo_controls.py`, `tests/test_netlogo_mir_adapter.py` | later DSL/codegen binding | Parsed and packaged, not bound into runnable specs |
| monitors | Interface metrics | `NetLogoWorld.monitor(...)`, `evaluate_netlogo_metric(...)`, `NetLogoControlsSpec.monitors`, MIR metrics | `partial` | `metrics` | monitor collection records plus native count-expression families | E0 | `tests/test_netlogo_semantics.py`, `tests/test_netlogo_controls.py`, `tests/test_netlogo_mir_adapter.py`, `tests/test_netlogo_metric_expressions.py` | broaden expression families only when fixtures require them | Only Virus-style turtle counts plus `count links`, context-bound `count link-neighbors`, and `count link-neighbors with [...]` are native; no general monitor AST |
| plots | Interface plots | `NetLogoControlsSpec.plots` plus `evaluate_netlogo_metric(...)` for Virus-style plot percentages | `partial` | `metrics`, `trace` | one native plot percentage expression family plus safe arithmetic over link counts | E0 | `tests/test_netlogo_controls.py`, `tests/test_netlogo_mir_adapter.py`, `tests/test_netlogo_metric_expressions.py` | broaden plot expression families only when fixtures require them | Plot pen commands are otherwise preserved as raw text, not generally executed |
| BehaviorSpace | Experiment sweeps and outputs | `netlogo_oracle.py` plus `netlogo_behaviorspace.py` manifest bridge | `oracle_backed` | `run`, `fidelity`, `trace` | external audit baseline | E1 | fixture outputs plus `tests/test_netlogo_behaviorspace_manifest.py` | use pack writer for reviewer-facing oracle baselines | Packageable as audit manifests and repro packs, not native MyMoMo execution |
| Fixture-driven gap audit | Deterministically classify what a parsed fixture can and cannot run natively | `abm_auto/netlogo_gap_audit.py` | `audit_only` | `fidelity`, `trace` in future | none | E0 | `tests/test_netlogo_gap_audit.py` | pick the next cell from reported fixture gaps | Static feature-family scan only; no AST, no execution, no compatibility proof; `can_run_natively` stays false when unclassified Code-tab text remains |
| random selection | Select agents from an agentset | `NetLogoWorld.one_of(...)`, `NetLogoWorld.n_of(...)`, agentset forwarding methods | `native-minimal` | `processes`, `entities` | seeded Python RNG over snapshots | E0 | `tests/test_netlogo_semantics.py` | compare against oracle per model when required | Stable under Python seed; not exact NetLogo RNG parity |
| random-number semantics | NetLogo RNG behavior | ADR-006 known mismatch notes | `oracle_backed` | `fidelity` | seeded Python RNG adjacent | E1 | topology/oracle tests | compare per model when required | Not exact NetLogo RNG parity |
| spatially clustered network | NetLogo model-library topology | `netlogo_spatially_clustered` | `oracle_backed` | `relations`, `space` | runtime topology adapter | E1 | `tests/test_topologies.py` | leave-as-is | One topology primitive only |
| NetLogo GIS topology | GIS extension vector topology | `topology_clip` codegen capability | `gis_parity` | `space`, `relations`, `fidelity` | GIS capability registry | E0 | `tests/gis/test_codegen_netlogo_parity.py` | leave-as-is | GIS-extension analogue only |
| NetLogo GIS focal raster | GIS extension focal raster ops | `raster_focal` capability | `gis_parity` | `space`, `layers`, `fidelity` | GIS capability registry | E0 | `tests/gis/test_codegen_netlogo_parity.py` | leave-as-is | GIS-extension analogue only |
| NetLogo GIS coverage | GIS extension polygon-to-raster coverage | `raster_coverage` capability | `gis_parity` | `space`, `layers`, `fidelity` | GIS capability registry | E0 | `tests/gis/test_codegen_netlogo_parity.py` | leave-as-is | GIS-extension analogue only |
| NetLogo extensions other than GIS | External extension commands | none | `missing` | `extensions` | none | E0 | coverage map only | extension-by-extension triage | No general extension support |
| HubNet / UI interaction | Participatory UI/network interaction | none | `out_of_scope` | none | none | E0 | coverage map only | defer | Not relevant to current reproduction loop |
| 3D view | NetLogo 3D visualization | none | `out_of_scope` | `space` in future | none | E0 | coverage map only | defer to 3D platform strategy | No 3D semantic layer yet |

## Do Not Overclaim

The native cell proves that MyMoMo can host a small NetLogo-like semantic
pattern on its own platform floor. It does not mean MyMoMo can import arbitrary
NetLogo models. The current boundary is:

- native: small turtle/agentset/ask/tick/global/monitor cell, stateful patch
  grid cells, minimal link agents, a limited metric expression family, and a
  tiny link metric/predicate family, integer turtle-to-patch position, and
  bounded patch neighbors plus patch-local turtle aggregation and minimal
  sprout plus cardinal movement, bounded radius scans, scalar patch diffusion,
  exclude-self turtle agentsets, seeded selection, and a manual nearest-unlinked
  Virus setup link helper;
- partial: file ingest, declarations, structured controls, story conversion;
- oracle-backed: selected BehaviorSpace/topology evidence;
- GIS parity: selected GIS-extension analogue operators;
- audit-only: fixture gap reporting for prioritizing the next runnable cell;
- missing: broader expression parser, command parser, broader extension support,
  and full NetLogo link syntax.

## Next Executable Cells

1. Choose the next cell from the remaining `Virus_on_a_Network.nlogo` audit
   gaps rather than from speculative primitive coverage. Current pressure
   points are `code_tab_procedure_execution`, `agentset_expression_parser`,
   `control_flow_parser`, `random_number_semantics`,
   broader `network_generation` source parsing (`min-one-of` / `distance`), and
   `visual_layout`.
2. The basic `n-of` / `one-of` / nearest-unlinked `create-link-with` setup slice
   is now native. Do not generalize agentset algebra, layouts, or arbitrary
   procedure execution without a locked fixture expectation.

## Validation

Observed local validation for this slice:

```text
.venv/bin/python -m pytest tests/test_netlogo_semantics.py tests/test_netlogo_gap_audit.py tests/test_netlogo_metric_expressions.py -q
62 passed

.venv/bin/python engine_oracle.py --science
SCIENCE GATE: PASS

.venv/bin/python engine_oracle.py --check
ENGINE ORACLE: PASS

.venv/bin/python -m pytest tests/ -q --ignore=tests/gis
1162 passed, 5 skipped, 4 warnings

git diff --name-only HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
<no output>
```

The full non-GIS suite first hit the local sandbox's multiprocessing semaphore
permission boundary in `tests/test_experiment.py::test_parallel_matches_serial`;
the same command passed when rerun with the required elevated sandbox
permission.

Historical validation from previous NetLogo semantic cells is preserved by git
history and can be replayed with the older commands if needed.

Base-engine forbidden directories remain untouched by this phase.
