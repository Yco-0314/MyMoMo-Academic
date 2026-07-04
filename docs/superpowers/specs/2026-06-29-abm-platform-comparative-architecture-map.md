# ABM Platform Comparative Architecture Map

**Status:** Design / strategy map, no code change.
**Date:** 2026-06-29
**Scope:** Compare NetLogo, Mesa, GAMA, and adjacent stronger platforms by task
family, then derive MyMoMo architecture evolution rules for the academic wedge
that serves the broader unified ABM platform.

## Context

MyMoMo-GIS-Academic already has a Mesa-shaped platform floor, NetLogo GIS parity
cells, GIS codegen registry coverage, multi-layer coupling adapters, real-data
validation/calibration bridges, and locked reproduction bundles. It is the open
academic wedge of the broader unified ABM platform: it produces public,
auditable capability evidence, trust contracts, reproduction artifacts, and
baseline comparisons that can be consumed by the larger physical-social-
biological simulation strategy. It should not independently try to become a
general replacement for NetLogo, Mesa, GAMA, MATSim, SUMO, or AnyLogic. ADR-024
already sets the division of labor: the academic arm leads on autonomy,
anti-fabrication, and reproducibility evidence, while engine power is pulled in
only when a concrete reproduction needs it.

The platform comparison is still useful because each incumbent exposes a
different semantic pressure:

- NetLogo shows the most compact ABM authoring language.
- Mesa shows a Python-native agent/runtime/data-collection shape.
- GAMA shows what GIS-native ABM language coverage looks like.
- Repast, MASON, Agents.jl, and FLAME GPU show scale/runtime alternatives.
- MATSim and SUMO show that serious transport should often be bridged, not
  reimplemented.
- AnyLogic and SimPy show multi-method and event/resource simulation pressure.

This document converts those observations into an explicit architecture map.

## Sources Checked

- NetLogo homepage and documentation index:
  <https://www.netlogo.org/index>
- Mesa overview:
  <https://mesa.readthedocs.io/latest/overview.html>
- Mesa-Geo documentation:
  <https://mesa-geo.readthedocs.io/stable/>
- GAMA documentation home:
  <https://gama-platform.org/wiki/Home>
- Repast Suite and Repast4Py documentation:
  <https://repast.github.io/>,
  <https://repast.github.io/repast4py.site/index.html>
- MASON / Distributed MASON homepage:
  <https://people.cs.gmu.edu/~eclab/projects/mason/>
- MATSim homepage:
  <https://matsim.org/>
- Eclipse SUMO homepage:
  <https://eclipse.dev/sumo/>
- FLAME GPU homepage:
  <https://flamegpu.com/>
- Agents.jl documentation:
  <https://juliadynamics.github.io/Agents.jl/stable/>
- AgentPy documentation:
  <https://agentpy.readthedocs.io/en/latest/>
- SimPy documentation:
  <https://simpy.readthedocs.io/en/latest/>
- AnyLogic features page:
  <https://www.anylogic.com/features/>
- UrbanSim homepage:
  <https://www.urbansim.com/>

## Comparison By Task Family

| Task family | Strong incumbents | What they are better at | MyMoMo stance |
|---|---|---|---|
| Compact ABM authoring | NetLogo | Fast teaching, model-library patterns, `turtles` / `patches` / `links` / `ask` / `tick` semantics | Extract semantic coverage; do not clone the language wholesale |
| Python ABM workflow | Mesa, AgentPy | Python-native model classes, AgentSet-style activation, data collection, notebooks, experiments | Keep Mesa-shaped floor; add only gaps that affect reproducibility or codegen |
| GIS-native ABM language | GAMA, Mesa-Geo, GeoMason, Agents.jl | Spatially explicit models, GIS files, OSM, vector/raster handling, visualization | GAMA is the main GIS-language benchmark; MyMoMo competes on gated reproduction, not GIS breadth |
| Transport simulation | MATSim, SUMO, AnyLogic transport libraries | Large-scale transport demand, public/private modes, microscopic vehicles, traffic lights, second-by-second dynamics | Bridge or audit these tools when needed; do not rebuild full traffic engines first |
| Event/resource systems | SimPy, AnyLogic, MASON DES | Discrete-event processes, queues, limited resources, mixed ABM + DES models | Add an event/resource seam only when a reproduction demands it |
| High-performance ABM | Repast HPC, Repast4Py, FLAME GPU, Agents.jl, Distributed MASON | MPI/distributed execution, GPU-scale agents, faster compiled/scientific runtimes | Treat as future backend pressure; first preserve MIR/gate semantics |
| Industrial decision support | AnyLogic, UrbanSim | Domain libraries, dashboards, cloud, stakeholder-facing scenario tools | Learn packaging/workflow patterns; avoid closed commercial platform imitation |
| Reproducibility and audit | MyMoMo | Locked predictions, science gates, fidelity gates, L3 bundles, anti-fabrication discipline | This remains the core differentiator |

## Platform Lessons

### NetLogo

NetLogo is the authoring-language reference. Its key lesson is not syntax; it is
the minimal conceptual grammar: observer, patches, turtles, links, breeds,
agentsets, `ask`, `to setup`, `to go`, `tick`, sliders, monitors, plots, and
BehaviorSpace. MyMoMo should map these concepts into MIR/platform semantics.

**Do not copy:** a full NetLogo parser as the first move.

**Do copy:** a semantic coverage table and a small set of oracle-backed ports
where NetLogo behavior matters.

### Mesa And Mesa-Geo

Mesa is the Python authoring/runtime reference. Its current documentation
centers model and agent classes, AgentSet activation, discrete spaces,
continuous space, event scheduling, DataCollector, and browser visualization.
Mesa-Geo adds GeoSpace and GeoAgents over Shapely/GeoPandas vector data.

MyMoMo already adopted the low-risk part: Mesa's shape, not Mesa as a
dependency. The next useful comparison is whether MyMoMo's platform floor has
equivalents for AgentSet selection/grouping, event scheduling, data collection,
and space semantics.

**Do not copy:** generic Mesa compatibility as a product goal.

**Do copy:** AgentSet/data/event API ideas where they simplify verified models.

### GAMA

GAMA is the serious GIS-ABM benchmark. It has a high-level GAML language,
spatially explicit modeling, GIS loading, OSM, grids, images, 3D files,
databases, visualization, batch tools, parameter-space exploration, calibration,
and a broad model library. GAMA also explicitly targets non-computer-scientist
modelers.

MyMoMo is behind GAMA on GIS engine breadth and UI maturity. The honest
position is to use GAMA as the coverage benchmark while keeping MyMoMo's
distinct claim: audited, locked, rerunnable scientific reproduction.

**Do not copy:** "be a better GAMA" as a near-term goal.

**Do copy:** GAML-level concepts: species, reflex, experiment, display, data
import, and parameter exploration as semantic categories.

### Repast, MASON, Agents.jl, FLAME GPU

These are runtime and scale references.

- Repast has workstation, HPC, and Python distributed variants.
- MASON is a fast Java simulation core with GIS, DES, distributed, and 2D/3D
  visualization extensions.
- Agents.jl shows a high-performance scientific-computing path with OSM,
  event queues, RL integration, and ecosystem integration.
- FLAME GPU shows how large agent populations can be expressed through formal
  agent specifications mapped to optimized CUDA execution.

**Do not copy:** a second runtime before MyMoMo has enough MIR pressure.

**Do copy:** backend-separation discipline. The MIR/open semantic layer should
remain able to target Python reference execution today and stronger runtime
backends later.

### MATSim And SUMO

MATSim and SUMO are transport specialists. MATSim is a large-scale
agent-based transport simulation framework with day-level traveler behavior and
iterative optimization. SUMO is a microscopic, continuous, multimodal traffic
simulator with vehicle/pedestrian/public-transport simulation, TraCI, network
import, demand generation, and traffic-light support.

MyMoMo should not hand-roll full traffic physics to validate flood evacuation or
mobility papers. It should define audited bridges:

- MyMoMo owns scenario provenance, assumptions, agent decision logic, and gates.
- SUMO/MATSim own low-level traffic execution when fidelity requires it.
- The bridge must record exact inputs, version, command, outputs, and reduction
  metrics.

### AnyLogic, SimPy, UrbanSim

AnyLogic is the multi-method industrial reference: ABM, discrete event, system
dynamics, statecharts, stock-flow diagrams, industry libraries, GIS maps, cloud,
and experiment tooling. SimPy is the Python event/resource reference. UrbanSim
is the domain platform reference for urban development, land use, transportation,
economy, environment, 3D visualization, and scenario planning.

MyMoMo should not become a commercial-style all-in-one decision platform. It
should learn the missing modeling pressures: event queues, resources/capacity,
system-dynamics coupling, stakeholder scenario bundles, and domain-specific
observed-data contracts.

## Capability Axes For MyMoMo

Every future platform comparison should be recorded against these axes:

| Axis | Examples | Native / bridge / audit decision |
|---|---|---|
| Agent language | breeds, species, statecharts, reflexes, staged lifecycle | Native when it affects codegen authoring |
| Space | raster, grid, network, vector, OSM, continuous, 3D | Native for GIS reproduction primitives; bridge for specialist engines |
| Time | tick, staged tick, event queue, continuous time, day plans | Native minimal event queue only when forced |
| Interaction | local neighborhood, network, social graph, traffic conflict, resource queue | Native for generic ABM; bridge for specialist physics |
| Data I/O | CSV, GeoTIFF, shapefile, GeoJSON, OSM, database, manifest | Native manifest contracts and provenance |
| Experiment | sweeps, BehaviorSpace, GAMA batch, AnyLogic experiments, notebooks | Native locked experiment bundles |
| Calibration | grid search, ABC, Bayesian, optimizer, external calibration | Native only through verified target/loss bridges |
| Visualization | plots, dashboards, 2D/3D, stakeholder UI | Secondary; useful but not the science gate |
| Scale | multiprocessing, MPI, GPU, compiled runtime | Backend pressure after MIR/gate contract is stable |
| Trust | prediction lock, fidelity gate, oracle, rerunnable bundle | Native and load-bearing |

## From Comparative Map To Unified Platform Strategy

This file is not the full unified-platform strategy document. It is the academic
wedge's comparative evidence map: it says which incumbent capabilities should be
native, bridged, used as audit baselines, or left out of scope. To serve the
broader unified physical-social-biological platform, this map must also export
the contracts that make cross-domain simulation comparable and auditable.

The unified platform should not be defined as "one runtime for every kind of
simulation." It should be defined as one loop:

```text
claim -> data/assumptions -> mechanism or bridge -> run/replay -> evidence -> verdict -> decision
```

The academic wedge proves and publishes pieces of that loop. The closed or
product platform can add mechanism search, decision workflows, sensitive data,
and high-scale execution, but it should consume the same open contracts.

### Claim Contract

Every simulation should carry a claim object before it runs:

- the claim being tested;
- the population, geography, domain, and time scope;
- the intervention or counterfactual;
- success metrics and refutation thresholds;
- assumptions that cannot be silently generalized;
- what counts as REPRO, PARTIAL, MISS, or out-of-scope.

This prevents the platform from becoming a machine that merely runs models. It
turns each model into an auditable argument.

### Evidence Ladder

Capabilities should report an evidence level, not a binary "supported" flag:

| Level | Meaning |
|---|---|
| E0 | Synthetic unit gate only |
| E1 | Local fixture or toy truth |
| E2 | Real local data plumbing |
| E3 | Locked real-data reproduction |
| E4 | Held-out validation or external benchmark |
| E5 | Multi-study replicability map |
| E6 | Prospective prediction locked before the real outcome is observed |

This keeps synthetic gates, real-data reproductions, LLM-agent simulations,
traffic bridges, and biological benchmarks from being described with the same
scientific strength.

### Scale Contract

Physical, social, and biological simulations live on incompatible natural
scales. A coupled scenario must state:

- time unit and update semantics;
- spatial unit or topology;
- aggregation and downscaling rules;
- state handoff rules between layers;
- information loss or unmodeled-scale disclosure.

Without this contract, cross-layer coupling can sound plausible while being
scientifically undefined.

### Open/Closed Proof Interface

The academic wedge should export open artifacts to the unified platform:

- MIR or scenario spec;
- manifests and data provenance;
- claim contract;
- evidence level;
- replay or trace;
- verdict bundle;
- failure residuals and MISS reports.

The unified platform can return anonymized scenario requests, bridge contracts,
closed mechanism candidates, or product workflow requirements. Open code should
not import closed modules; exchange should happen through durable artifacts.

### Backend Execution Strategy

External platforms should not be treated only as competitors or inspiration.
They are possible execution backends, bridges, or baselines:

- Python reference backend for small, auditable gates;
- columnar/vectorized backend for larger social simulations;
- SUMO/MATSim for traffic fidelity;
- GPU/HPC backends for large agent populations;
- virtual-cell model backends for biological response prediction;
- LLM-agent backends for language-mediated behavior.

The stable layer is MIR plus the claim/evidence/trace contract, not a single
runtime.

### MISS Handoff Protocol

A MISS is not just a failed reproduction. It is the handoff from the open
academic wedge to closed mechanism search or deeper platform work:

```text
open academic: claim + data + model -> MISS
handoff: MIR + manifest + failed gate + residual pattern
closed platform: mechanism search / alternative explanation / decision sandbox
return path: publishable candidate mechanism -> new open proof
```

This is how failed reproductions become fuel for the unified platform instead
of dead ends.

## Architecture Direction

### D1. Make "native vs bridge vs audit baseline" explicit

Do not register all platform capabilities as native MyMoMo goals. Each external
capability must be classified:

- **Native:** implement in MyMoMo because it is a core ABM/GIS/reproducibility
  semantic needed across papers.
- **Bridge:** call an external engine because a specialist domain engine is
  already better.
- **Audit baseline:** run an external tool only to compare or validate MyMoMo's
  result.
- **Out of scope:** useful elsewhere but not tied to a current reproduction or
  architectural pressure.

### D2. Extend MIR as the stable semantic layer

MIR should be the open semantic contract that can preserve NetLogo/GAMA/Mesa-like
meaning without binding MyMoMo to their runtimes. Platform-specific syntax should
map into MIR concepts such as entities, layers, relations, schedules, mechanisms,
observations, experiments, and extensions.

### D3. Build semantic coverage before parser coverage

The next NetLogo/GAMA work should be a semantic coverage map, not a parser:

- NetLogo: observer, patches, turtles, links, breeds, agentsets, `ask`, `tick`,
  sliders, monitors, plots, BehaviorSpace.
- GAMA: model, global, species, reflex, action, experiment, display, GIS import,
  batch, calibration.
- Mesa: Agent, Model, AgentSet, spaces, DataCollector, event scheduling,
  SolaraViz.

Only after coverage is explicit should MyMoMo decide whether a parser, exporter,
or codegen template is worth building.

### D4. Treat transport as bridge-first

Dynamic congestion and flood evacuation currently prove moving-agent lifecycle
semantics, not traffic-flow validity. A future real traffic/flood evacuation
study should evaluate SUMO/MATSim bridge feasibility before adding deeper native
traffic physics.

### D5. Add event/resource semantics only when a reproduction forces it

SimPy and AnyLogic show that queues, service capacity, and process flows matter.
MyMoMo should not add a generic event engine speculatively. The first event seam
should be paid for by a concrete reproduction where fixed ticks are the wrong
modeling unit.

### D6. Keep trust as the differentiator

The incumbents are stronger authoring and execution tools. MyMoMo's claim is
that it can autonomously turn scientific intent into a locked, gated, reproducible
artifact and honestly report REPRO / PARTIAL / MISS. Every imported platform
idea must strengthen that loop or be deferred.

## Proposed Next Specs

1. **NetLogo Semantic Coverage Phase 1**
   - Build a table mapping NetLogo language primitives to MIR/platform concepts.
   - Mark native-supported, partial, missing, oracle-backed, and out-of-scope.
   - No parser and no runnable template in Phase 1.

2. **GAMA Semantic Coverage Phase 1**
   - Map GAML concepts into MyMoMo: species, reflex, action, experiment, display,
     GIS import, batch, calibration.
   - Identify the first two GIS-language gaps that matter for real reproduction.

3. **Transport Bridge Feasibility Phase 1**
   - Compare SUMO and MATSim bridge contracts for one small synthetic network.
   - Define what a rerunnable bridge manifest must include.
   - No production traffic bridge until a paper needs it.

4. **Event/Resource Seam Trigger Criteria**
   - Define when SimPy-style event/resource semantics become necessary.
   - Produce a gateable example only after a concrete reproduction exposes the
     need.

## Non-Goals

- No attempt to outbuild GAMA as a general GIS engine.
- No full NetLogo/GAML parser in this phase.
- No generic backend compiler to Mesa, Repast, GAMA, SUMO, or MATSim.
- No 3D visual platform.
- No traffic-flow validity claim from the current dynamic congestion model.
- No speculative GPU/HPC backend.

## Success Criteria

- Future platform work can state whether a capability is native, bridge,
  audit-baseline, or out of scope.
- NetLogo and GAMA become semantic benchmarks, not vague inspiration.
- Specialist engines are used where they are better, without weakening MyMoMo's
  provenance and gate contract.
- MyMoMo's differentiator stays precise: autonomous, locked, gated,
  reproducible scientific modeling rather than broad engine imitation.
