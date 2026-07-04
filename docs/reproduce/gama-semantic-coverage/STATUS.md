# GAMA Semantic Coverage Status

**Date:** 2026-07-01
**Scope:** Documentation-only semantic coverage map for GAMA / GAML concepts in
MyMoMo.
**Related spec:**
`docs/superpowers/specs/2026-07-01-gama-semantic-coverage-phase1-design.md`

## Verdict

GAMA should be treated as MyMoMo's main GIS-native ABM language benchmark, not
as a near-term compatibility target. MyMoMo is stronger on locked claims,
evidence packs, deterministic gates, and open reproduction artifacts. GAMA is
stronger on integrated GIS authoring, GUI workflow, displays, model library
breadth, 3D, and non-programmer modeling ergonomics.

The right architecture move is to classify GAMA concepts as `native`, `bridge`,
`audit_baseline`, or `out_of_scope` before building parsers or templates.

## Coverage Table

| Concept | GAMA meaning | MyMoMo surface | Disposition | Evidence level | Next action | Boundary note |
|---|---|---|---|---|---|---|
| model / global block | Top-level model container, global variables, init, scheduling context | MIR metadata/run/state plus Python model modules | `native` | E0 | Map into future native/bridge/audit registry | MyMoMo does not parse GAML model files |
| species | Agent type with state, behavior, geometry, and population | MIR entities, GISAgent, NetLogoTurtle adjacent semantics | `native` | E0 | Reuse as semantic category in MIR/platform docs | Not GAMA-compatible species syntax |
| reflex | Scheduled behavior rule for species | StagedGISModel lifecycle, AgentSet.do, NetLogo ask/tick semantics | `native` | E0 | Keep as lifecycle pressure term | No GAML reflex parser or priority semantics |
| action | Callable behavior block used by agents or globals | Python methods/functions, mechanisms, gates | `native` | E0 | Leave as authoring concept, not syntax target | No GAML action binding |
| init | Setup phase for model state and agents | setup/build functions, fixtures, platform constructors | `native` | E0 | Use in future MIR schedule vocabulary | No GAMA init execution |
| experiment | Declared run configuration, parameters, outputs | `Experiment`, locked predictions, Evidence Foundry packs | `native` | E0 | Align vocabulary with Evidence Foundry claim contracts | MyMoMo experiments are not GAMA experiments |
| batch / parameter exploration | Parameter sweeps and batch runs | `Experiment`, reproduction sweeps, registry reports | `native` | E0 | Keep native where it strengthens gated reproduction | No GAMA batch UI or DSL |
| display | Integrated visual output surface | `_viz.py`, `_geo_viz.py`, docs artifacts | `audit_baseline` | E0 | Compare output needs only when a reproduction requires displays | Visualization is secondary to gates |
| charts and monitors | Runtime plots, monitors, and output summaries | DataCollector, reports, NetLogo monitor analogues | `native` | E0 | Keep metric/report contracts native | No GAMA chart syntax |
| GIS import | Load spatial files into model spaces | `_io.py`, `_vector_io.py`, RasterSpace, GeoNetwork, manifests | `native` | E2 | Continue manifest-backed real-data bridges | MyMoMo is narrower than GAMA's GIS import breadth |
| OSM / road-network import | Import OSM/network data for mobility and GIS models | GeoNetwork and traffic-count matching; no broad OSM importer | `bridge` | E1 | Prefer manifest or external conversion until a paper forces native OSM import | Do not claim OSM parity |
| raster / grid / image layers | Grid, image, and raster data in spatial models | RasterSpace, raster focal/coverage, observed-raster calibration | `native` | E2 | Leave native; extend only through real-data need | Not a full GAMA image workflow |
| shapefile / GeoJSON vector layers | Vector spatial data and geometries | vector IO, topology operators, point/polygon coverage | `native` | E2 | Leave native for reproduction primitives | No GAMA-level vector UI |
| 3D visualization and geometries | 3D display and spatial modeling | none in open MyMoMo GIS layer | `out_of_scope` | E0 | Defer to unified 3D strategy | Do not imply 3D platform support |
| database I/O | Connect models to databases | manifests and local file artifacts | `bridge` | E0 | Add only for a real-data reproduction requiring DB access | No database connector yet |
| calibration / optimization | Fit parameters and explore scenarios | calibration bridges, residual diagnostics, gates | `native` | E2 | Keep native through explicit target/loss manifests | Not GAMA calibration compatibility |
| user interface for non-programmers | Graphical modeling and experiment workflow | docs, reports, CLI commands | `out_of_scope` | E0 | Learn packaging patterns, do not build GUI now | MyMoMo is not a GAMA UI replacement |
| multi-level or nested agents | Agents containing or coordinating lower-level agents | MIR relations/extensions; platform concepts adjacent | `bridge` | E0 | Defer until a reproduction needs nested hierarchy | No native nested-agent lifecycle |
| event scheduling | Event-based or mixed tick/event execution | ADR notes and platform lifecycle adjacent | `bridge` | E0 | Use Event/Resource Seam Trigger Criteria before implementing | Do not add event engine speculatively |
| traffic / mobility coupling | Movement over road networks, transport behavior | dynamic flood/congestion lifecycle, traffic count validation | `bridge` | E1 | Move to SUMO/MATSim bridge feasibility before deeper traffic claims | Current dynamic models do not prove traffic-flow validity |
| external tool integration | Use external tools/libraries inside a model workflow | Evidence Foundry handoff, bridge manifests, oracle baselines | `audit_baseline` | E0 | Standardize native/bridge/audit registry | Bridges need version, command, input, output, and reduction metrics |

## Do Not Overclaim

This coverage map does not mean MyMoMo can run GAMA models. It does not provide
a GAML parser, a GAMA bridge, GAMA UI compatibility, or feature parity with
GAMA's GIS modeling environment.

The useful claim is narrower:

- GAMA supplies semantic pressure for GIS-native ABM authoring.
- MyMoMo can classify that pressure into native, bridge, audit-baseline, and
  out-of-scope buckets.
- Only concepts that strengthen locked, gated, reproducible evidence should
  become native MyMoMo work.

## Next Specs

The seed classification registry now lives at
`docs/reproduce/platform-capabilities/registry.json`.

1. **Native / Bridge / Audit Registry Phase 1**
   - Create a reusable classification table for future platform comparison work.
   - Initial consumers: GAMA coverage, transport bridge feasibility, LLM society
     layer, closed backend integration.

2. **Transport Bridge Feasibility Phase 1**
   - Define SUMO/MATSim bridge manifest requirements before claiming traffic
     validity from native dynamic congestion or evacuation models.

3. **Event / Resource Seam Trigger Criteria**
   - Define when fixed-tick ABM is insufficient and when a SimPy/AnyLogic-style
     process/resource seam is justified.

## Validation

This is a documentation-only coverage phase. Required verification:

```text
rg -n "[T]BD|[T]ODO|[U]NRESOLVED|[N]EEDS-DECISION|[F]ILL-ME" docs/superpowers/specs/2026-07-01-gama-semantic-coverage-phase1-design.md docs/reproduce/gama-semantic-coverage/STATUS.md
git diff --check
git diff --name-only HEAD -- abm_auto/runtime abm_auto/codegen abm_auto/calibration abm_auto/agents abm_auto/pipeline
```

Expected outputs are empty.
