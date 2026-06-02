# Predictions — Yaman semantic-innovation reproduction (BEFORE any run)

**Status: PREDICTIONS ONLY. Written 2026-06-03 before implementing or
running anything. Committed to git so they cannot be edited post-hoc to
match outcomes (ADR-012/013 "artifact before conclusion", applied to
this experiment). Wrong predictions are the target signal — they expose
where my model of the architecture is wrong.**

Source of truth for the model: `SPEC-yaman-semantic-innovation.md`
(every line there traces to extracted PDF text, none from memory).

## The question

Can abm-auto reproduce the Yaman et al. semantic-innovation ABM — whose
core is an **agent that carries and trains a small neural net** (the
distributional semantic model) as part of its per-generation step?

This is the "operator-missing" wall: every prior abm-auto agent has
fixed-rule state (scalars like `self.state: int`). A learned-
representation agent has never been generated.

## Confirmed architectural facts (checked 2026-06-03, not predicted)

- MechanismSpec does NOT restrict imports → an agent CAN `import numpy`.
- runtime Agent `_safe_attr` carries arbitrary state → CAN hold NN
  weights/embeddings as arrays.
- No precedent: all existing example agents carry only scalar state.

So nothing *hard-blocks* this. The open question is whether the codegen
PROCESS (MechanismSpec extraction + TemplateGenerator + CoderAgent +
GVR) can actually produce correct training code, not whether the runtime
could in principle hold it.

## Two execution paths (a decision the spec left open)

**Path 1 — full codegen (originate/reproduce mode).** Feed a story.md
describing the Yaman model; let the pipeline generate it. Tests W2 at its
hardest. Highest information, highest failure risk.

**Path 2 — hand-write the reference model, calibrate/analyze only.**
Build the model by hand (like the SIR handcrafted_model), use abm-auto
only for the calibration/diagnostics layer. Lower risk, tests less.

## PRE-REGISTERED PREDICTIONS

### P1 — Path 1 (full codegen) outcome
**Prediction: codegen FAILS to produce a working semantic model on the
first end-to-end attempt, but the failure is DETECTED, not silent.**
Reasoning: the NN training loop (forward pass + cross-entropy + backprop
+ embedding update) is ~3 nested concerns the LLM must get right in
`environment.step` / agent state; prior codegen handled single
state-transition rules. I expect either (a) MechanismSpec extraction
flattens the NN into a scalar "semantic_score" and loses the mechanism,
or (b) generated code imports numpy but the training math is wrong
(shapes / loss / no actual weight update), caught by a flat-result
diagnostic.
**Confidence: 70% it fails first attempt; 90% that if it fails, a
diagnostic catches it rather than producing a plausible-looking wrong
result.**

### P2 — which sub-mechanism breaks first
**Prediction: the `Predict(model, item)` forward-pass + the
`updateModels` retraining are the breakage point, NOT the Moran loop or
the inventory/recipe task.** The Moran loop and combinatorial task are
fixed-rule (abm-auto has done similar); the *learned* part is the wall.
**Confidence: 80%.**

### P3 — MechanismSpec expressiveness
**Prediction: the current MechanismSpec schema CANNOT cleanly express "an
agent that trains a neural net" — it has fields for scenario_params,
agent_state_vars, topology, targets, but no concept of a per-agent
learned sub-model with a training step.** I predict the spec will either
omit the NN entirely or stuff it into an opaque free-text field that
TemplateGenerator can't act on.
**Confidence: 75%. If TRUE, this is a real architecture finding: W2's
codegen vocabulary needs a "learned-operator" concept to reach this
class of model. If FALSE (it expresses it fine), I've underestimated
the schema.**

### P4 — the honest-negative value
**Prediction: even if Path 1 fails, the failure is publishable evidence
for the W2 boundary** ("LLM codegen handles fixed-rule ABMs but not yet
learned-representation agents") — analogous to the CSD×Deffuant negative.
A clean characterization of WHERE codegen breaks is worth more than
forcing a success.

### P5 — recommended path
**Prediction: the right first move is Path 1 to its first failure (cheap,
~one pipeline run, high information), THEN Path 2 if we want the actual
scientific reproduction.** Running Path 1 first turns the "operator-
missing wall" from a claim into measured evidence.

## What would falsify my model of the architecture

- P1 false: codegen produces a working semantic model first try → I've
  badly underestimated W2; that's a major positive finding.
- P3 false: MechanismSpec expresses the NN cleanly → the schema is more
  general than I think.
- P2 false: something OTHER than the NN breaks first (e.g. the Moran loop)
  → my sense of "what's hard" is miscalibrated.

## Falsification discipline

After running: compare each Pn to the real outcome. Record matches AND
misses. A miss is the valuable result. No prediction edited after a run.

---

## Post-fix prediction (block 1+2+3 shipped, before re-run) — 2026-06-03

After the W2 fix (FeedforwardLearner library + LearnedOperator schema +
prompt guidance), re-running the SAME Yaman story.md:

**P6 — Prediction: the generated agent.py now CONTAINS a real
FeedforwardLearner (imported from runtime, instantiated, .train/.predict
called), NOT a degraded `random()<P_S`.** The mechanism survives because
the LLM now has (a) a schema slot for it and (b) explicit "use the
library, don't implement the NN" guidance.
**Confidence: 55%.** Lower than it sounds — the prompts now PERMIT and
GUIDE it, but Stage-2 must still choose to emit a `learned_operators`
entry, and CoderAgent must wire it. Two LLM decisions can still drop it.

**P7 — Prediction: even if the learner is wired, the FULL Yaman result
(semantic > non-semantic synergy with social learning) will NOT
reproduce in one pipeline run** — the recipe-tree/Totem task + Moran
inheritance + the exact strategy branching are too much for codegen to
get all-correct at once. A wired-but-imperfect model is the likely best
case, and is already strong evidence the W2 wall moved.
**Confidence: 75% it won't fully reproduce the science even if NN wired.**

Falsification: P6 false (NN still dropped) → the wall is deeper than
schema+prompt; the fix needs TemplateGenerator to emit the
instantiation (3A), not just guide the LLM (3B). That would itself be a
finding about where the 3B boundary fails.
