# Findings — Yaman reproduction Path 1 (full codegen), scored vs predictions

**Run**: `workspace/20260603_005144_c0e498`, 2026-06-03, exit 0.
**Verdict**: codegen produced a RUNNABLE but MECHANISM-EMPTY model — the
trainable semantic neural net (the paper's entire point) was silently
dropped; the sim is degenerate (innovation_count constant 3.0, std 0.0
for all 200 ticks). Every claim below traces to the run log or generated
files, read after the run. Predictions were locked in `327dbc3` before it.

## What the pipeline actually generated

- `mechanism_spec.md` (9467 chars): **excellent** — correctly captured the
  full NN (embedding 16, hidden 16, ReLU, softmax, cross-entropy, Adam
  lr=0.001, 1-epoch retrain, nearest-neighbor generalization, Moran loop).
  The free-text extraction understood the paper.
- `mechanism_spec.json` (the typed schema): **NN absent**.
  `agent_state_vars` = [inventory, memory, age, score] — all scalars. No
  weights, no embeddings, no semantic_model. The Stage-2 JSON validator
  rejected `list`/`set` types (only bool/float/int/str allowed) and has
  no concept for "a trained sub-model" at all.
- `agent.py`: imports numpy but contains **no neural net**. The semantic
  strategy collapsed to `if random.random() < self.P_S: add(new_item)` —
  P_S degraded from "use the trained model" into "success probability".
  Generalization (P_G) became "copy a random neighbor item", not
  embedding-space nearest-neighbor. Predict/retrain/embeddings: gone.
- Sim output: degenerate flat trajectory (constant 3.0).

## Prediction scorecard (matches AND misses)

| # | Prediction | Outcome | Verdict |
|---|---|---|---|
| **P1** | full codegen FAILS first attempt (70%); failure DETECTED not silent (90%) | Codegen produced runnable-but-empty code (a failure of fidelity, not a crash). The sanity-checker DID detect it: "ALL numeric columns are constant", logged 4× + recorded as knowledge `innovation_count_zero_std_constant_max`. But GVR "accepted at iter 1/5 — Sanity issues persist, continuing anyway", and exit code was 0. | **P1 MOSTLY RIGHT**: failed (fidelity), detected (sanity-check fired). MISS on severity: detection did NOT halt — it warned and shipped exit 0. The degeneracy was caught but not enforced. |
| **P2** | the learned part (Predict + updateModels) breaks first, not the Moran loop / recipe task | Exactly this. The Moran loop + recipe task survived into the spec; the NN is what got dropped at the spec→json→code stage. | **P2 RIGHT (80%→confirmed).** |
| **P3** | MechanismSpec schema CANNOT cleanly express "an agent that trains a neural net"; will omit the NN or stuff it in opaque free-text | Confirmed, and sharper than predicted: the free-text `mechanism_spec.md` expressed the NN perfectly; the TYPED `mechanism_spec.json` schema could not hold it (only scalar types; list/set rejected; no learned-operator concept). The mechanism was lost precisely at the free-text → typed-schema boundary. | **P3 RIGHT, and located the exact seam**: the loss is at md→json, not in extraction. |
| **P4** | even failure is publishable W2-boundary evidence | Holds: this is a clean, measured characterization of where codegen breaks for learned-representation agents. | **P4 RIGHT.** |
| **P5** | run Path 1 to first failure first (cheap, high info) then Path 2 | Path 1 cost ~one pipeline run and produced precise evidence (the md→json seam). Vindicated. | **P5 RIGHT.** |

## The real architecture finding (the valuable result)

The W2 codegen boundary is **not** "the LLM can't understand the model" —
the free-text `mechanism_spec.md` understood it fully. The boundary is
**the typed `MechanismSpec` schema**: its `agent_state_vars` admit only
scalar types (bool/float/int/str) and have no concept of a *learned
sub-model* (weights + embeddings + a training step). So the mechanism is
expressible in prose, gets extracted correctly, then is **flattened away
when forced through the typed schema** that TemplateGenerator + CoderAgent
consume.

This is the "operator-missing" wall, now located precisely: it is a
**schema-expressiveness** wall at the md→json transition, not an
extraction or reasoning failure. To reach learned-representation agents,
MechanismSpec needs a first-class "learned operator" concept (a sub-model
with state = parameter arrays + a per-step train/predict interface).

## The honest-negative, and a second, separable finding

Beyond the W2 schema wall, the sanity-check **detected the degeneracy but
did not halt** ("continuing anyway", exit 0). This is the same
exit-0-on-broken-output gap the SIR reliability runs showed (§3.4 of the
preprint) — and exactly what the diagnostics-HALT gate (ADR-013
DiagnosticsHaltGate) was built to fix, but that gate guards the
*calibration* path, not the *codegen sanity* path. A second, separable
finding: the codegen sanity-check should be able to escalate an all-
constant trajectory to a HALT, not just a warning.

## Next (Path 2, deferred — this artifact is Path 1 only)

To actually reproduce the science (not just probe W2), hand-write the
reference model with a real per-agent NN (Path 2 from the predictions),
and use abm-auto only for the analysis layer. The Path-1 finding stands
on its own as W2-boundary evidence regardless.
