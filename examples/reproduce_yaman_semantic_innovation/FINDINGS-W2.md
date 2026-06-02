# Findings — W2 wall fix, isolated test (P8 CONFIRMED)

**Question**: does the W2 fix (FeedforwardLearner library + LearnedOperator
schema + prompt guidance) let codegen express a learning-representation
agent — the thing Path 1 proved it could not?

**Verdict: P8 CONFIRMED.** Feeding Path-1's known-good `mechanism_spec.md`
+ `DESIGN.md` (which fully describe the trainable semantic NN) into the
W2-updated Stage-2 extractor produces a clean spec (`status: ok`) carrying
a correct `learned_operators` entry. The SAME input the OLD extractor
flattened into `random() < P_S`.

Every line below traces to the real isolation run
(`isolate_w2.py`, real LLM); P8 was locked in `d599a9c` before it.

## The result

```
Stage-2 status: ok
learned_operators count: 1
  - name='semantic_model' n_items='n_total_items'
    embed_dim=16 hidden_dim=16 lr=0.001
agent_state_vars: [inventory:str, memory:str, successful_memory:str,
                   age:int, score:int]
```

Old extractor (Path 1): the NN was absent from the spec entirely; agent.py
had `if random.random() < self.P_S: add(new_item)`. New extractor: a
FeedforwardLearner-shaped `learned_operators` entry with the paper's
dims (16/16, lr 0.001). The wall — "the typed schema can't hold a trained
sub-model" — is gone at the extraction stage.

## What the isolation surfaced (and we fixed, reading real output)

The first isolation runs did NOT pass clean — two real defects, found by
running, not assumed:

1. **My validation was too strict.** The LLM emitted
   `n_items="scenario.n_total_items"` — the codebase's existing
   `scenario.X` reference convention (topology.params uses it). My
   LearnedOperator validation only accepted a bare identifier and
   rejected the prefixed form. Fixed: both `n_items` validation and the
   spec-level param-existence check now strip the `scenario.` prefix
   (matching topology). This was MY bug, not the LLM's.

2. **The LLM made two recurring spec mistakes** the prompt didn't guard:
   (a) listing `semantic_model` in BOTH `learned_operators` and
   `agent_state_vars` (a duplicate the collision check correctly
   rejected); (b) referencing an `n_items` param without declaring it in
   `scenario_params`; (c) using `"list"`/`"set"` types for inventory.
   Fixed by tightening the Stage-2 prompt with three explicit rules (no
   dup name; declare the n_items param or use a literal; list/set→str
   type with a real init expression). After the prompt fix, Stage-2
   passed clean in ONE call.

## Honest scope of this confirmation

- **Confirmed**: the W2 fix moves the wall at the SPEC EXTRACTION stage —
  a learning-representation agent is now expressible in the typed schema,
  end to end from a NN-describing design to a valid `learned_operators`
  spec.
- **NOT yet confirmed**: full-pipeline codegen producing runnable
  agent.py that instantiates FeedforwardLearner and trains it. That run
  is blocked by an ORTHOGONAL design-phase bug (a re-run produced an empty
  DESIGN.md → Phase 1b crashed), not by W2. The isolation deliberately
  bypassed that to test W2 alone.
- **NOT claimed**: reproducing Yaman's science (P7 stands — the full
  Totem task + Moran + strategy branching is more than one codegen run
  gets right). This probe confirms the OPERATOR is expressible, which was
  the W2 question.

## Prediction scorecard (P6/P7/P8)

- **P8 (isolated): CONFIRMED.** Updated Stage-2 emits a valid
  learned_operators given an NN-describing design.
- **P6 (full pipeline): still UNVERIFIED** — blocked by the design-phase
  bug, not by W2. The isolated confirmation is the stronger evidence
  anyway (it tests the exact md→json transition Path 1 failed at).
- **P7 (full science reproduction): not tested** — out of scope for the
  W2 probe; stands as future Path-2 work.

## Next (deferred)

- Fix the design-phase empty-DESIGN.md fallback bug, then a full-pipeline
  run can confirm P6 (agent.py actually instantiates the learner).
- Path 2 (hand-write the reference model) for the actual scientific
  reproduction.
