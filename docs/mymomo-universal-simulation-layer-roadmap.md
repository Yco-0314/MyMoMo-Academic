# MyMoMo Universal Simulation Layer Roadmap

**Status**: Draft v0.2  
**Date**: 2026-05-31  
**Scope**: Turn MyMoMo Academic from an autonomous ABM/code-generation pipeline into a universal simulation semantic layer that can describe, execute, audit, exchange, and learn from simulations across social systems, embodied systems, scientific models, and learned world models.

---

## 1. Executive Thesis

MyMoMo should not become "a social simulator," "a robot simulator," or "a world model." Those are downstream projections of a deeper missing layer.

The stronger position is:

> MyMoMo defines the missing simulation semantic layer: a shared language, compiler, and audit system for describing what exists in a world, how state changes, how actions and constraints operate, what can be observed or intervened on, and how traces should be evaluated.

In this framing, social simulation, embodied robot simulation, system dynamics, discrete-event simulation, causal simulation, and JEPA-style learned world models are not separate strategic identities. They are runtime or learning targets that project from the same semantic contract.

The critical rule:

> Unification happens at the semantic-contract layer, not inside one universal engine.

MyMoMo should define common semantics while compiling into many runtimes. It should not pretend that one simulator can faithfully handle social norms, hospital logistics, rigid-body dynamics, market mechanisms, and latent video prediction with the same execution substrate.

The target stack:

```text
Reality descriptions
  -> MyMoMo Simulation Language (MSL)
  -> Simulation Semantic Core / MIR
  -> domain dialects
       social, embodied, economic, ecological, institutional, physical, cognitive
  -> runtime projections
       ABM, system dynamics, discrete event, causal graph,
       robotics simulator, learned world model, planner
  -> traces, interventions, evaluations, datasets, policies
```

---

## 2. Universal Simulation Layer Thesis

### 2.1 Common Simulation Semantics

Every serious simulation has the same abstract questions, even when the runtime differs:

1. **Entities**: what exists in the world?
2. **State**: what attributes can change?
3. **Relations**: what connects entities?
4. **Processes**: how does state evolve without direct action?
5. **Actions**: what can agents or policies do?
6. **Observations**: who can see what, and with what uncertainty?
7. **Interventions**: what can be changed for experiments or counterfactuals?
8. **Evaluation**: what counts as success, failure, violation, risk, or emergence?

The first product problem is not "Can social simulation help world models?" The deeper problem is:

> Can one semantic layer express these eight questions cleanly enough that different simulators, learners, researchers, and agents can exchange worlds without losing mechanism, provenance, and evaluation meaning?

### 2.2 Domain Dialects, Not Separate Products

MyMoMo should support domain dialects over one semantic core:

- **Social dialect**: roles, norms, institutions, communication, routines, group behavior.
- **Embodied dialect**: sensors, actions, physical spaces, robot constraints, task goals.
- **Economic dialect**: markets, budgets, incentives, matching, bargaining, shocks.
- **Ecological dialect**: populations, resources, habitats, adaptation, feedback.
- **Causal dialect**: interventions, counterfactuals, mechanisms, evidence strength.
- **Learned-world-model dialect**: observations, actions, context-target masks, latent prediction, planning costs.

These dialects should compile into the same canonical MIR. The dialects make authoring natural; MIR makes execution, validation, and exchange reliable.

### 2.3 Why World Models Still Matter

The LeCun / JEPA route remains important, but it is not the master narrative. It is one downstream proof that the semantic layer can produce structured experience for representation learning and planning.

In the Yann LeCun / JEPA direction, the learned world model predicts latent representations rather than reconstructing pixels. MyMoMo's complementary role is to supply structured worlds, mechanisms, interventions, tasks, constraints, and evaluation contracts.

That is valuable even if a particular world-model approach fails, because the same semantic layer still improves academic simulation, reproducibility, trace auditing, intervention generation, and cross-runtime exchange.

---

## 3. Reading The LeCun / JEPA Route

### 3.1 Core Interpretation

LeCun's route is not "LLM but bigger." It is closer to:

1. Learn representations of the world from observation.
2. Predict missing or future latent representations, not raw sensory details.
3. Use those representations for planning under uncertainty.
4. Separate perception, world model, cost, actor, short-term memory, and configurator-like control.
5. Build agents that can reason about consequences without having to generate every pixel.

For MyMoMo, the important implication is:

> A world model needs controllable experience. Simulation languages can become a way to generate structured experience, not merely a way to generate code.

### 3.2 Paper Map From The Provided Links

| Link | Paper / direction | Relevance for MyMoMo |
|---|---|---|
| [1] | LeCun, "A Path Towards Autonomous Machine Intelligence" | Architectural north star: world model, cost, actor, memory, configurator. |
| [2] | I-JEPA, image latent prediction | Early proof that semantic visual representations can be learned by predicting embeddings rather than pixels. |
| [3] | MC-JEPA, motion + content | Useful for dynamic scenes where motion and object identity must be jointly represented. |
| [4] | V-JEPA, video feature prediction | Important bridge from static perception to time and prediction. |
| [5] | Audio-JEPA | Reminder that world models are multimodal, not only visual. |
| [6] | Point-JEPA | Relevant for 3D geometry and robot perception from point clouds. |
| [7] | 3D-JEPA | Relevant for 3D object/world representation. |
| [8] | ACT-JEPA | Directly relevant to policy representation and action-conditioned world modeling. |
| [9] | V-JEPA 2 | Strong signal that video JEPA can move toward understanding, prediction, and planning. |
| [10] | LeJEPA | Theory and training stability; useful if MyMoMo later trains its own small latent models. |
| [11] | Causal-JEPA | Very important: object-level latent interventions are close to MyMoMo's intervention contracts. |
| [12] | V-JEPA 2.1 | Dense video features, useful for robotics and spatial grounding. |
| [13] | LeWorldModel | Stable end-to-end JEPA from pixels, relevant to closing perception-prediction loops. |
| [14] | Neural Paging, arXiv redirects to 2603.02228 | Not core JEPA, but relevant to long-horizon context and memory management for agents. |
| [15] | Rectified LpJEPA | Sparse, non-negative, maximum-entropy representations; relevant for making latent factors easier to probe against MIR variables. |
| [16] | GRASP planning | Parallel stochastic gradient-based planning over learned world models; relevant to the actor/planner layer above MyMoMo-generated tasks. |
| [17] | EB-JEPA library | Practical lightweight codebase for image, video, action-conditioned JEPA, and JEPA-based planning experiments. |
| [18] | Lance | Columnar storage optimized for mixed sequential scans and random access; relevant to large trace/video/object-token datasets. |
| [19] | stable-worldmodel | Reproducible platform for world-model data, baselines, planning solvers, and standardized generalization evaluation. |

### 3.3 The Downstream Strategic Gap

JEPA-style models can learn from video and multimodal streams, but they do not automatically know:

- which events were interventions;
- which object caused which later change;
- which social rule was violated;
- which part of a trajectory was rare but important;
- which scenario belongs to a curriculum;
- which assumption came from a paper versus from an AI guess;
- which failures matter for real deployment.

That is the gap MyMoMo can fill.

### 3.4 Why The New 2026 Additions Matter

The additional papers shift the roadmap from "representation learning" toward "representation plus planning."

**Rectified LpJEPA** matters because world models should not only produce accurate latent predictions; they should produce latents that are usable by downstream probes, planners, and auditors. Sparse and non-negative factors are not the same thing as human-readable symbols, but they may make it easier to align learned features with MIR concepts such as "doorway blocked," "patient identity uncertain," or "human path conflict."

**GRASP** matters because it attacks a practical bottleneck: planning through learned visual world models is hard over long horizons. Its lifted-state idea suggests that MyMoMo should not export only goal states and rewards. It should also export intermediate constraints, soft dynamics checks, and event-level milestones that can stabilize planners.

**EB-JEPA** matters because it is an accessible experimental base. MyMoMo should not begin by training large custom world models. A small EB-JEPA-style setup is enough to test whether MyMoMo traces improve representation, prediction, and planning in a controlled task.

### 3.5 Why Lance And stable-worldmodel Matter

These two references are infrastructure-level, not representation-level.

**Lance** matters because world-model datasets are awkward: researchers need sequential video scans, random frame access, object/state-token lookup, and repeated sampling of short context-target windows. If MyMoMo emits large multimodal traces, a naive pile of MP4, CSV, and JSONL files will become the bottleneck. Lance points toward a better storage substrate for trace replay, random access, and training dataloaders.

**stable-worldmodel** matters because the world-model field is converging on reproducibility as a central problem. The paper frames three bottlenecks that also apply to MyMoMo's future work: fragile one-off codebases, slow video data loading, and weak standardized generalization benchmarks. MyMoMo should not create yet another isolated benchmark stack. It should either interoperate with stable-worldmodel-style data and evaluation conventions or consciously define the semantic layer that sits above them.

This changes the roadmap:

- MIR should export both semantic traces and efficient training datasets.
- `jepa_manifest.json` should be compatible with stable-worldmodel-style loaders where possible.
- Evaluation should include controllable factor shifts, not just in-distribution task success.
- The project should treat storage format and benchmark reproducibility as first-class architecture, not as later engineering cleanup.

---

## 4. Product Positioning

### 4.1 What MyMoMo Is

MyMoMo should become a universal simulation semantic layer, or "world mechanism compiler."

It accepts:

- natural language stories;
- papers and ODD descriptions;
- researcher-authored text specs;
- visual mechanism diagrams;
- robot task descriptions;
- empirical data and calibration targets.

It outputs:

- executable simulations;
- ODD and academic reports;
- trace datasets;
- intervention suites;
- robot task curricula;
- evaluator contracts;
- learned-world-model training manifests.

### 4.2 What MyMoMo Is Not

MyMoMo should not initially train a frontier world model from scratch.

It should not compete head-on with:

- Isaac Sim for photorealistic robotics simulation;
- MuJoCo for fast rigid-body control;
- Habitat for embodied navigation and human-object environments;
- ManiSkill for manipulation benchmarks;
- V-JEPA/LeWorldModel for representation learning.

MyMoMo should orchestrate, annotate, and evaluate those runtimes and learned models through a shared semantic contract.

---

## 5. Core Architecture

The architecture has four layers:

1. **Semantic Core / MIR**: the canonical meaning of a simulation.
2. **Domain Dialects**: social, embodied, economic, ecological, causal, and learned-world-model vocabularies.
3. **Authoring Surfaces**: researcher text, visual editors, AI-generated drafts.
4. **Runtime Targets**: ABM, robotics simulation, system dynamics, causal simulation, datasets, planners, learned world models.

### 5.1 Authoring Surfaces: MSL And Visual Editors

MSL should be readable by researchers and editable by AI, but it is not the source of truth. Visual editors and natural-language workflows should also compile into the same MIR rather than creating parallel model formats.

Example shape:

```yaml
world:
  name: clinic_delivery
  time:
    tick: 1 minute
    horizon: 480 ticks

entities:
  Patient:
    state:
      room: location
      urgency: ordinal[low, medium, high]
      medication_due: bool
  Nurse:
    state:
      role: enum[triage, ward, emergency]
      busy: bool
  Robot:
    state:
      carrying: object?
      battery: percent

spaces:
  hospital_floor:
    type: graph
    nodes: rooms
    edges: corridors

processes:
  - name: emergency_event
    schedule: stochastic
    effect:
      - select Patient where urgency == high
      - move Nurse toward Patient.room

robot_tasks:
  - name: deliver_medicine
    goal: medication reaches correct Patient
    constraints:
      - do not enter restricted rooms
      - yield to emergency staff
      - ask clarification if patient identity confidence < 0.8

observables:
  - task_success
  - social_rule_violations
  - time_to_delivery
  - blocked_human_paths
```

### 5.2 Semantic Core: MIR

MIR is the single source of truth. It is not ABM-specific, robotics-specific, or world-model-specific. It should be stricter than MSL:

- typed;
- schema-valid;
- deterministic under fixed seed;
- fully diffable;
- no ambiguous scheduling;
- no implicit unit conversions;
- every AI assumption explicit;
- every metric bound to a state variable or trace expression.

Minimum MIR modules:

1. `entities`: agent/object/environment types.
2. `state`: typed variables, units, ranges.
3. `relations`: spatial, social, causal, ownership, permission, communication.
4. `time`: tick length, event clocks, horizon, stopping criteria.
5. `processes`: state transitions and stochastic events.
6. `actions`: actor capabilities and preconditions.
7. `observations`: what sensors or researchers can observe.
8. `interventions`: allowed counterfactual changes.
9. `tasks`: goals, costs, constraints, success conditions.
10. `metrics`: evaluation and calibration targets.
11. `provenance`: story, paper, data, AI assumption, human edit.
12. `trace_contract`: expected event logs and replay rules.

### 5.3 Domain Dialects

Domain dialects are typed extensions over MIR, not separate languages:

- `social`: roles, norms, communication, institutions, routines.
- `embodied`: sensors, robot actions, spatial constraints, safety rules.
- `economic`: markets, incentives, budgets, matching, shocks.
- `ecological`: populations, resources, habitats, adaptation.
- `causal`: interventions, evidence, counterfactual queries.
- `learned_world_model`: observations, context-target masks, latent costs, planner contracts.

Each dialect should be optional. A simple Schelling model should not need robot fields; a robot navigation task should not need market fields.

### 5.4 Runtime Targets

MyMoMo should support multiple runtime targets, but staged:

1. Current MyMoMo ABM runtime.
2. System dynamics modules for aggregate feedback loops.
3. Discrete event simulation for queues, workflows, logistics.
4. Robotics adapters:
   - Habitat-style navigation tasks;
   - MuJoCo-style control tasks;
   - Isaac Sim-style high-fidelity scene generation;
   - ManiSkill-style manipulation tasks.
5. Dataset exporters for JEPA-style training.

---

## 6. Embodied Intelligence Bridge

### 6.1 Why Robots Need MyMoMo

Robotics simulators are strong at physics. They are weaker at social causality.

A robot in a hospital, school, household, factory, or city must understand:

- roles and permissions;
- schedules and routines;
- hidden goals;
- human movement patterns;
- social constraints;
- rare failures;
- changing task instructions;
- consequences of interruption;
- when to ask a human.

MyMoMo can generate these social-physical contexts and compile them into training scenarios.

### 6.2 Embodied Task Spec

Add an `embodied_task` layer to MIR:

```yaml
embodied_task:
  robot:
    embodiment: mobile_manipulator
    sensors: [rgb, depth, audio, proprioception]
    actions: [navigate, pick, place, speak, wait, ask]

  goal:
    expression: delivered(medicine, correct_patient)
    deadline: 20 minutes

  constraints:
    hard:
      - collision_count == 0
      - restricted_area_entries == 0
    soft:
      - minimize human_path_blocking
      - minimize unnecessary_questions

  curriculum:
    levels:
      - fixed_room_fixed_patient
      - room_change
      - ambiguous_patient_identity
      - emergency_interrupt
      - conflicting_human_instructions
```

### 6.3 Generated Training Artifacts

For each scenario, MyMoMo should produce:

- `scenario.mir.yaml`: canonical world spec.
- `scene_manifest.json`: spaces, objects, spawn points.
- `agent_script.jsonl`: human/non-robot agent routines.
- `robot_task.json`: goals, action space, reward/cost terms.
- `interventions.jsonl`: counterfactual changes.
- `trace.jsonl`: event stream after simulation.
- `metrics.json`: success, violations, recovery, robustness.
- `jepa_manifest.json`: context-target masks, modalities, action labels.
- `dataset_manifest.json`: data shards, modalities, indexing columns, train/validation/test splits.

---

## 7. Learned World-Model Data Interface

### 7.1 What MyMoMo Provides To JEPA Training

MyMoMo should not only emit videos. It should emit aligned, structured traces:

```text
timestep
  raw observations: rgb/depth/audio/state
  object tokens: id, type, pose, attributes
  agent tokens: role, intention proxy, state
  action tokens: robot action, human action, environment event
  intervention labels: what was changed
  causal labels: which process fired
  cost labels: task success, violation, risk
```

This lets JEPA-style models train on:

- visual prediction;
- object-centric latent prediction;
- action-conditioned latent prediction;
- intervention-conditioned latent prediction;
- multimodal alignment;
- rare-event understanding;
- planning-relevant abstraction.

The manifest should also support energy-based JEPA experiments:

```yaml
jepa_manifest:
  objective_family: energy_based_jepa
  representation_constraints:
    sparsity_probe: true
    nonnegative_probe: true
    maximum_entropy_probe: true
  masks:
    context: [past_frames, current_objects, current_social_state]
    target: [future_objects, future_costs, future_interventions]
  planning:
    action_conditioned: true
    planner: grasp_style
    horizon: 50
    milestones: [leave_pharmacy, avoid_emergency_corridor, reach_patient_room]
```

### 7.2 Suggested Training Objectives

Do not start by training a large model. Start with small probes:

1. **Representation probe**: can a frozen V-JEPA-like encoder distinguish mechanisms?
2. **Transition probe**: can a small predictor forecast latent state after an action?
3. **Intervention probe**: can the model predict the effect of changing a process variable?
4. **Cost probe**: can latent states predict social rule violations before they happen?
5. **Planning probe**: can a planner choose actions that reduce predicted cost?
6. **Sparsity probe**: do Rectified LpJEPA-style constraints produce latents that map more cleanly to MIR variables?
7. **Energy probe**: does an EB-JEPA-style energy score separate valid futures from impossible or rule-violating futures?
8. **Milestone probe**: do intermediate MIR milestones improve long-horizon planning compared with terminal-goal-only planning?

### 7.3 Planning Loop

```text
current observation
  -> encoder
  -> latent state
  -> candidate action sequences
  -> latent world model predicts futures
  -> cost module scores task, safety, social constraints
  -> actor executes first action
  -> trace logger records outcome
  -> evaluator compares predicted and observed futures
```

MyMoMo contributes the candidate task structure, constraints, interventions, and evaluation rules.

GRASP-style planning suggests a more specific contract:

```text
MyMoMo task contract
  -> initial latent state
  -> goal latent/state condition
  -> intermediate MIR milestones
  -> soft dynamics constraints
  -> hard safety constraints
  -> action bounds
  -> cost terms
  -> model-exploitation checks
```

This is important because a planner can exploit defects in a learned world model. MyMoMo should therefore evaluate not only whether the predicted plan looks good in latent space, but whether replaying the plan in the simulator satisfies the symbolic trace contract.

### 7.4 Dataset And Reproducibility Interface

MyMoMo should define a dataset interface that can map to Lance or stable-worldmodel-style pipelines.

Minimum dataset fields:

```yaml
dataset_manifest:
  format_targets: [jsonl, lance_candidate, stable_worldmodel_candidate]
  modalities: [rgb, depth, state, object_tokens, actions, interventions, costs]
  indexes:
    - scenario_id
    - episode_id
    - timestep
    - object_id
    - intervention_id
    - factor_shift_id
  splits:
    train: factor_values_seen
    validation: factor_values_interpolated
    test_ood: factor_values_held_out
  access_patterns:
    sequential_scan: full_episode_replay
    random_access: context_target_window_sampling
    filtered_access: all_episodes_with_social_rule_violation
```

This interface should preserve MyMoMo semantics while letting world-model researchers train with high-throughput loaders. The core design question is not "Should MyMoMo use Lance?" but "Can every MyMoMo-generated trace be stored and sampled without losing mechanism, intervention, and evaluation metadata?"

---

## 8. Phased Roadmap

### Phase 0: Concept Lock And Literature Map

Goal: turn the idea into a stable architecture memo.

Deliverables:

- This roadmap.
- A paper matrix for JEPA/world-model/robotics-sim work.
- A terminology document: MSL, MIR, trace contract, intervention, embodied task.
- A boundary statement: what MyMoMo will and will not build.
- A data-layer decision note: JSONL-first for prototype, Lance/stable-worldmodel-compatible manifests for scale.

Success criteria:

- The project can be explained in one paragraph.
- The LeCun route is translated into product architecture, not just cited.
- Robotics support is framed as orchestration and semantic data generation.

### Phase 1: Simulation Semantic Core v0 From Existing ABM Pipeline

Goal: make the current mechanism spec structured and machine-checkable, while proving that MIR is a general semantic core rather than merely an ABM code-generation helper.

Build:

- `mechanism_spec.yaml` as a typed output after `DESIGN.md`.
- JSON Schema or Pydantic models for MIR v0.
- Validator for entity/state/process/metric references.
- Compiler from MIR v0 to current runtime prompt context.
- Trace checker that verifies generated code follows MIR scheduling and metrics.

Success criteria:

- Existing SIR, Schelling, Bass diffusion, and bounded confidence examples can produce MIR.
- MIR catches missing units, ambiguous update order, and invalid metrics before code generation.
- Generated simulations can be replayed with stable seeds.
- At least one small embodied or social-navigation task can reuse the same entity/state/process/action/evaluation concepts without a separate schema.

### Phase 2: Researcher-Facing MSL

Goal: let researchers edit models without touching Python.

Build:

- Markdown + YAML MSL syntax.
- Round-trip conversion: MSL -> MIR -> rendered MSL.
- Human-edit provenance: which fields were edited by AI versus researcher.
- ODD generator from MIR, not directly from freeform design text.

Success criteria:

- A non-programmer can edit parameters, agents, rules, and metrics.
- Edits survive regeneration without being overwritten by the LLM.
- ODD output traces each rule back to MIR provenance.

### Phase 3: Social-Physical Scenario Layer

Goal: move beyond classic ABM into task worlds.

Build:

- `space` module with rooms, graphs, zones, permissions.
- `role` and `institution` modules for social rules.
- `routine` module for human agent behavior over time.
- `event` module for interruptions, emergencies, shocks.
- `task` module for robot or policy actors.

Success criteria:

- Hospital delivery, household assistance, office navigation, and warehouse coordination can be expressed in MSL.
- Each scenario produces a task curriculum and trace contract.
- Rule violations and recovery behavior can be measured.

### Phase 4: Robotics Simulator Adapters

Goal: compile semantic scenarios into embodied training targets.

Build:

- Neutral scene manifest.
- Adapter prototype for one simulator first.
- Human routine export.
- Robot goal and reward/cost export.
- Trace importer from simulator logs back into MyMoMo.

Recommended first adapter:

- Use a lightweight or already-scriptable environment before high-fidelity Isaac Sim.
- Prioritize fast iteration and trace fidelity over visual realism.

Success criteria:

- One scenario can generate executable embodied episodes.
- Simulator output can be mapped back to MIR events.
- MyMoMo can score both task success and social-rule violations.

### Phase 5: JEPA Dataset And Probe Experiments

Goal: prove MyMoMo can generate useful world-model training data.

Build:

- `jepa_manifest.json` exporter.
- `dataset_manifest.json` exporter with stable train/validation/test factor splits.
- Context-target mask specifications.
- Action/intervention labels aligned with frames and object states.
- Baseline probes using frozen visual/video encoders where possible.
- EB-JEPA smoke test on one small generated environment.
- Rectified LpJEPA-inspired sparsity/non-negativity probes over object and event latents.
- Optional Lance export spike for random access to context-target windows.

Experiments:

- Predict next latent state after navigation action.
- Predict effect of moving an obstacle.
- Predict whether a robot will block a human path within N seconds.
- Predict whether asking a question improves task success.
- Compare dense versus sparse latent probes on mechanism classification and intervention prediction.
- Train an EB-JEPA-style Two-Rooms-like task where MyMoMo controls social rules and event schedules.
- Compare in-distribution, interpolated, and held-out factor shifts using stable-worldmodel-style evaluation splits.

Success criteria:

- Latent probes outperform raw heuristic baselines.
- Intervention labels improve prediction under counterfactual changes.
- Social-rule violation prediction works before the violation happens.
- Dataset samples are reproducible by scenario id, episode id, timestep, seed, and factor shift.

### Phase 6: Planning And Counterfactual Control

Goal: use learned world-model predictions for action selection.

Build:

- Candidate action generator.
- Cost module from MIR task constraints.
- Simple MPC or search over predicted latent futures.
- GRASP-style lifted-state planning experiment for one visual or state-based world model.
- Counterfactual evaluator: compare "ask", "wait", "move", "reroute".
- Simulator replay verifier to catch plans that exploit model errors.

Success criteria:

- Agent can choose safer or more effective actions under changed conditions.
- Planning improves over reactive policies in task success and violation metrics.
- Failure cases are explainable via MIR terms.
- Latent-space plans replay successfully in the simulator, not only inside the learned model.

---

## 9. Evaluation Framework

### 9.1 Engineering Validity

- Schema validity.
- Reference integrity.
- Unit consistency.
- Deterministic replay under seed.
- Code-generation fidelity to MIR.
- Trace completeness.

### 9.2 Scientific Validity

- ODD completeness.
- Assumption provenance.
- Sensitivity analysis.
- Calibration fit where empirical data exists.
- Mechanism ablation.
- Reproduction fidelity for known papers.

### 9.3 Learned-World-Model Validity

- Latent prediction error.
- Intervention prediction accuracy.
- OOD scenario robustness.
- Long-horizon rollout stability.
- Planning success.
- Error localization: perception, transition, cost, policy, or simulator gap.
- Reproducible benchmark splits by controllable visual, geometric, physical, and social factors.
- Data loading and sampling parity: the same context-target query returns the same sample across runs.

### 9.4 Embodied Safety Validity

- Collision rate.
- Rule violation rate.
- Human path blocking.
- Clarification quality.
- Recovery from changed instructions.
- Performance under rare events.

---

## 10. Deep Reflections And Risks

### 10.1 Simulation Is Not Reality

The biggest danger is believing that a well-specified simulated world is a true world. MyMoMo should treat simulations as hypotheses, not as reality.

Every generated world should carry:

- assumption provenance;
- confidence;
- data support;
- known exclusions;
- calibration status;
- transfer-risk notes.

### 10.1.1 Reproducibility Is Part Of The Science

World-model research can look successful when each paper uses its own loaders, environments, seeds, and evaluation splits. stable-worldmodel is a warning that infrastructure fragmentation is already a scientific problem.

For MyMoMo, reproducibility means:

- the semantic spec is versioned;
- the simulator seed is versioned;
- dataset conversion is deterministic;
- factor splits are explicit;
- baseline configs are saved;
- evaluator outputs are replayable.

Without this, MyMoMo would produce interesting demos but weak science.

### 10.2 Latent Prediction Is Not Causal Understanding

JEPA-like latent prediction can learn powerful regularities, but prediction alone may not identify causal structure. MyMoMo can help by emitting intervention labels and counterfactual scenarios, but the learned model still needs causal evaluation.

Practical stance:

- use simulation to generate interventions;
- train latent models on those interventions;
- test whether predictions remain correct when mechanisms change;
- punish shortcut learning through adversarial scenario design.

### 10.3 Social Simulation Can Encode Bad Assumptions

Social models are normative. A hospital robot scenario can encode whose path matters, whose time counts, who has authority, and what "success" means.

MyMoMo must make these choices visible. Hidden social assumptions are more dangerous than visible imperfect assumptions.

### 10.4 Do Not Collapse Symbolic And Latent Worlds Too Early

MIR is symbolic and typed. JEPA representations are latent and distributed. Forcing one to become the other too early may damage both.

Better:

- MIR generates worlds, labels, interventions, and evaluation.
- JEPA learns latent predictive structure.
- Probes and planners connect the two.
- Keep the boundary explicit.

### 10.5 The First Killer Demo Should Be Modest

Do not start with "general world model." Start with:

> A robot delivery task in a dynamic social environment where MyMoMo generates scenario variants, the simulator produces traces, a latent predictor anticipates failures, and a planner chooses between ask/wait/reroute actions.

This is small enough to build and rich enough to show the whole thesis.

### 10.6 Sparse Latents Are Not Symbols

Rectified LpJEPA-style sparse and non-negative representations are attractive because they may expose cleaner factors. But sparse features are still learned variables, not guaranteed concepts.

Practical stance:

- probe whether sparse dimensions align with MIR state variables;
- measure stability across seeds and scenario variants;
- avoid naming a latent factor as a human concept unless interventions support that interpretation;
- prefer "latent factor associated with path blockage" over "the blockage neuron."

### 10.7 Planners Will Exploit Learned Model Errors

Gradient-based planning can find elegant plans, but it can also find adversarial holes in the world model. GRASP-style lifted planning helps with long horizons, but MyMoMo must still replay candidate plans in a simulator and compare predicted versus actual trace contracts.

Planning success should therefore have two gates:

1. The latent planner predicts a low-cost future.
2. The symbolic/simulator replay confirms the trace is valid.

---

### 10.8 Universal Layers Can Become Empty Abstractions

The biggest new risk in the universal simulation layer framing is over-abstraction. A layer that tries to describe everything can become too generic to help anyone.

Practical stance:

- start from concrete runtimes and concrete examples;
- require every MIR field to support validation, compilation, trace checking, or evaluation;
- reject concepts that sound philosophical but cannot be tested;
- add dialect fields only when at least two examples need them or one example cannot be expressed without them.

### 10.9 One Semantic Layer Does Not Mean One Ontology Of Truth

MyMoMo should let researchers encode competing world descriptions. It should not force one universal ontology of society, physics, economics, or cognition.

The semantic layer should support:

- multiple models of the same phenomenon;
- explicit assumptions and provenance;
- mechanism comparison;
- intervention tests;
- calibration and falsification.

Universal means interoperable, not final.

---

## 11. Recommended First Milestone

Build **Simulation Semantic Core v0**, not a full language, visual editor, or world model.

Concrete scope:

1. Convert `mechanism_spec.md` into structured `mechanism_spec.yaml`.
2. Add typed fields for schedule, state transitions, parameters, metrics, assumptions.
3. Add preliminary `embodied_task` schema.
4. Generate a trace contract from MIR.
5. Use one current ABM example and one new social-robot scenario.
6. Produce a paper-style report and a JEPA dataset manifest from the same MIR.
7. Add an EB-JEPA-compatible tiny dataset export for one navigation-like task.
8. Add two probes: dense versus sparse representation alignment, and planner prediction versus simulator replay.
9. Add a `dataset_manifest.json` with stable-worldmodel-style factor splits and Lance-compatible indexing fields.

This proves the core idea:

> One semantic world specification can support academic simulation, engineering reliability, embodied task generation, reproducible datasets, and learned-world-model experiments without making any downstream runtime the center of the project.

---

## 12. References

- Yann LeCun, "A Path Towards Autonomous Machine Intelligence": https://openreview.net/pdf?id=BZ5a1r-kVsf
- I-JEPA: https://arxiv.org/abs/2301.08243
- MC-JEPA: https://arxiv.org/abs/2307.12698
- V-JEPA: https://arxiv.org/abs/2404.08471
- Audio-JEPA: https://arxiv.org/abs/2507.02915
- Point-JEPA: https://arxiv.org/abs/2404.16432
- 3D-JEPA: https://arxiv.org/abs/2409.15803
- ACT-JEPA: https://arxiv.org/abs/2501.14622
- V-JEPA 2: https://arxiv.org/abs/2506.09985
- LeJEPA: https://arxiv.org/abs/2511.08544
- Causal-JEPA: https://arxiv.org/abs/2602.11389
- V-JEPA 2.1: https://arxiv.org/abs/2603.14482
- LeWorldModel: https://arxiv.org/abs/2603.19312
- Neural Paging: https://arxiv.org/abs/2603.02228
- Rectified LpJEPA: https://arxiv.org/abs/2602.01456
- Rectified LpJEPA code: https://github.com/YilunKuang/rectified-lp-jepa
- GRASP planning: https://arxiv.org/abs/2602.00475
- GRASP project page: https://www.michaelpsenka.io/grasp/
- EB-JEPA library paper: https://arxiv.org/abs/2602.03604
- EB-JEPA code: https://github.com/facebookresearch/eb_jepa
- Lance: https://arxiv.org/abs/2504.15247
- stable-worldmodel: https://arxiv.org/abs/2605.21800
- stable-worldmodel code: https://github.com/galilai-group/stable-worldmodel
