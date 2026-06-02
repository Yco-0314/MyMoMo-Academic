---
status: Accepted
date: 2026-05-29
decision-makers: yco
supersedes: (extends ADR-006 calibration recovery)
---

# ADR-007: Schema-driven codegen via MechanismSpec + TemplateGenerator

> _Editorial note (2026-06-02): the original challenge's event name has been neutralized to "the virus-on-a-network (SIR-on-network) calibration challenge"; the decision and rationale below are unchanged._

## Context

abm-auto's value proposition is "story.md → working calibrated ABM
model". Until 2026-05-29 that promise rested entirely on the LLM
(CoderAgent) writing all 7 model files from a free-form DESIGN.md.
End-to-end dogfooding revealed this fragile: **0% codegen success rate
on the virus-on-a-network SIR story** after the Topology callable seam (commit
276c1a9) replaced the old `network_type=str` string API.

Root cause: boilerplate code that wires Topology / Network / Scenario /
DataCollector is purely mechanical. The LLM re-derives it from scratch
on every run and gets it slightly wrong each time (LLM writes
`topologies.watts_strogatz(n=150, k=6, p=0.1)` when correct is
`topologies.watts_strogatz(k=6, p=0.1)` — `n` is derived from
`agent_lists` automatically). 5 GVR retries failed to recover.

Layers 1 + 2 of the architectural fix (anti-pattern validator, better
prompt) were considered. They treat symptoms without removing the class
of error. The architecturally correct move: **stop asking the LLM to
write the boilerplate**.

## Decision

Introduce a structured `MechanismSpec` contract between Phase 1d
(MechanismExtractor) and Phase 2 (Codegen). MechanismExtractor produces
two artefacts:

  - `mechanism_spec.md` — free-form pseudocode (human audit trail; what
    Phase 1d always produced)
  - `mechanism_spec.json` — strict structured spec matching the
    `MechanismSpec` dataclass (new — Layer 3)

A new `abm_auto.codegen.template_generator` module emits 5 boilerplate
files deterministically from the JSON spec, with no LLM involvement:

| File | Owner before | Owner after |
|---|---|---|
| `core/model.py` | LLM | **TemplateGenerator** |
| `core/scenario.py` | LLM | **TemplateGenerator** |
| `core/data_collector.py` | LLM | **TemplateGenerator** |
| `main.py` | LLM | **TemplateGenerator** |
| `data/input/SimulatorScenarios.csv` | LLM | **TemplateGenerator** |
| `core/agent.py` | LLM | LLM (unchanged — mechanism body) |
| `core/environment.py` | LLM | LLM (unchanged — mechanism body) |

CoderAgent's surface area narrows ~70%: it only writes the two files
that contain genuinely mechanism-specific logic. Topology call,
Scenario class fields, DataCollector property registration, Config
wiring, CSV column names — all become uncopyable-by-LLM.

## Two-stage extraction (refinement of the decision)

The first implementation (commit 6e65abe) tried to get MechanismSpec
JSON out of a single LLM call along with the markdown pseudocode.
3 consecutive dogfoods all produced markdown without the JSON block,
even after strengthening the prompt with a "CRITICAL OUTPUT REQUIREMENT"
callout at the top.

Root cause: reasoner-class models spend their budget on whichever
output the prompt emphasizes most; multi-output prompts get the trailing
output dropped. Single-prompt-for-two-outputs is architecturally hostile
to JSON emission.

Refinement (commit 421883b): split into TWO LLM calls:

  - Stage 1 (`prompts/mechanism_spec.md`) → produces ONLY markdown
    pseudocode. Unchanged behavior.
  - Stage 2 (`prompts/mechanism_spec_json.md`) → reads Stage 1's
    markdown + DESIGN.md, produces ONLY a fenced ```json``` block
    matching `MechanismSpec`. Strict JSON-extractor system prompt.

One retry permitted on parse failure (feeds error back as feedback).
On second failure, returns None and pipeline falls back gracefully
to legacy whole-file codegen.

`MechanismExtractor._extract_json_spec()` orchestrates Stage 2;
`_parse_mechanism_json()` extracts the JSON block (fenced or bare {…}
fallback) and validates against `MechanismSpec.validate()`.

## Consequences

### Wins

1. **Topology API confusion eliminated** for the 5 boilerplate files.
   No LLM can write `topologies.watts_strogatz(n=150)` because LLM
   doesn't write that file.
2. **CoderAgent's job shrinks** — 13 post-hoc fixup functions in
   `coder.py` only need to operate on 2 files instead of 7. Fewer
   patterns of failure to chase. Sets up future CoderAgent
   decomposition (Item 5 of the Layer-3 follow-up backlog).
3. **Schema is the single source of truth** — `scenario_params` declared
   once in `mechanism_spec.json` flows to `Scenario` class fields,
   `SimulatorScenarios.csv` columns, and `DataCollector` properties
   without manual sync. Eliminates the entire class of
   "calibration_param_specs declared but CSV column missing" bugs.
4. **Templates are testable** — `tests/test_template_generator.py`
   (20 unit tests) asserts generated Python parses + topology call
   shape (`n=` MUST NOT appear). Anti-regression on the very class of
   bug Layer 3 was designed to eliminate.
5. **Graceful degradation** — if MechanismExtractor's JSON parse
   fails, pipeline falls back to legacy codegen. No new failure mode.

### Costs

1. **+1 LLM call per pipeline run** (Stage 2 JSON extraction).
   ~$0.005 at DeepSeek pricing. Negligible.
2. **MechanismSpec dataclass is a new dependency** for every codegen
   path. Schema changes need migrations.
3. **TemplateGenerator can't capture every model** — agent.py and
   environment.py are still LLM-written. Templates only solve the
   boilerplate class of failure, not mechanism-body failure.

### Trade-offs explicitly rejected

- **Reverting Topology callable API to old `network_type=str` form**
  would have eliminated the immediate dogfood breakage but lost the
  ability to express NetLogo-faithful topologies (commit 276c1a9's
  whole reason for existing).
- **Schema-driven for ALL files including agent.py / environment.py**
  is the long-term aspiration but would require the schema to capture
  arbitrary algorithm pseudocode, which is what we left to the LLM in
  the first place. Not viable as a Layer-3 MVP.

## Empirical evidence

Dogfood progression on the virus-on-a-network SIR story (2026-05-29):

| Run | Codegen path | Calibration MSE | best_params |
|---|---|---|---|
| pre-fix #1 | crashed in codegen | — | none |
| pre-fix #2 | fell back to optimizer | — | out-of-range |
| post-Fix-#1-#5 | legacy codegen + calibrator | 257.3 | within 67% of truth |
| post-Item-1 | two-stage extraction + dtype fix | **23.3** | within 22% of truth |

The MSE drop from 257 to 23 came primarily from the calibrator dtype
fix (commit 35adc7d) — schema-driven codegen and two-stage extraction
work as designed and provide a clean foundation for future improvements,
but the user-facing value gain on this story was actually delivered by
the dtype fix.

Layer 3's value is **forward-looking insurance**: ensures the boilerplate
breakage class can't return when other architectural changes happen.

## Open questions

- **Stage-2 JSON still failing intermittently** — observed in the
  first two-stage dogfood: reasoner returned empty output both attempts.
  Mitigation: bumped max_tokens 2048→4096. If still flaky, fallback to
  using `deepseek-chat` (non-reasoning) for the JSON extraction call.
- **Agent.py / Environment.py template hooks** — `_render_initial_setup`
  emits an LLM-FILL marker followed by `pass`, but no mechanism in
  CodegenPhase reads the marker. The placeholder is essentially dead
  code in the current pipeline.
- **Template schema migration** — adding fields to `MechanismSpec`
  requires updating every workspace's `mechanism_spec.json` if we want
  re-running an existing workspace to benefit. Acceptable for now;
  revisit if schema changes accelerate.

## Related

- ADR-006 — calibration recovery (this ADR follows the same dogfood-
  driven empirical-fix discipline)
- Topology seam — commit 276c1a9 (introduced the API that LLMs couldn't
  write, which is what motivated Layer 3)
- Anti-pattern validator — `abm_auto/codegen/anti_patterns.py` (Layer 2
  symptom treatment, complementary to Layer 3's root-cause fix)
