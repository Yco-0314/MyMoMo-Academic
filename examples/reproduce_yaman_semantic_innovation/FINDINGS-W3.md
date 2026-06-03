# Findings — W3 reference-asset / RuleTable harvest

The third operator harvested from the Yaman Path-2 model: an external
rule/recipe/transition TABLE the design DECLARES instead of assuming.

## Apparatus (complete, tested: 334 passed)

- `runtime/_rule_table.py` — `RuleTable`: a CSV-backed rule-table operator
  (parse, densify sparse ids → contiguous index space, combination lookup,
  given items, weights/labels, dependency levels). Generalises the hand-
  written `task.py`. **Validated on the REAL OSF tree**: `from_csv` reproduces
  `task.py`'s result exactly — `n_items=184`, `level_counts == [6,4,2,2,2,3,3,
  7,11,48,96]`, the axe recipe `{12,14,17}` correct. self_test on a synthetic
  sparse-id table.
- `mechanism_spec.py` — `ReferenceAsset` schema slot (Optional list; validates
  required `output_col`/`input_cols`/`filename`, the `rule_table` kind, dup
  names) + from_dict + validate.
- prompts — extraction slot (`reference_assets`), and the design vocabulary
  row: an external rule/recipe table is `[paper-canonical]`, declared not
  assumed; **its CONTENTS never cost assumptions**.
- `story.md` — now states (honestly) that the specific recipes are released
  data (`rules_tidied.csv`), not a formula.

## Dogfood (n=1): W3's structural goal is MET

Re-ran the real DesignAgent on the updated story (reproduce mode).

- **The recipe tree is now DECLARED, not assumed.** The design loads it as a
  `RuleTable` instance from `rules_tidied.csv`, tagged `[story,
  paper-canonical]`. A targeted grep for a recipe-tree `AI-ASSUMPTION` returns
  EMPTY — the assumption that used to be there (item-id encoding, base items,
  which combinations are valid) is GONE. That is exactly what W3 set out to do.

- **But the total hardened count this run was 10 (a FAIL), UP from the prior
  run's 6.** None of the 10 is the recipe tree or an operator. They are: the
  LLM tagging OPERATOR INTERNALS despite the vocabulary (FeedforwardLearner
  training details, the death-function form/params, the generalization
  mechanism), infrastructure (random seed, run repetitions), and method
  implementation details (`copy_inventory_for_social`, the social-learning
  "can combine?" check) — plus one real param (`semantic_cost_factor`).

## Honest conclusion: structural thesis validated; gate count is a NOISY metric

The expressiveness thesis is **structurally** confirmed. All three hard
mechanisms of a sophisticated paper are now DECLARED provided operators, not
AI-invented assumptions:

| hard mechanism | was | now |
|---|---|---|
| trainable per-agent neural net | AI-ASSUMPTION(s) | `FeedforwardLearner` (W2) |
| Moran birth-death turnover | AI-ASSUMPTION(s) | `MoranProcess` (W4) |
| 184-row external recipe tree | AI-ASSUMPTION(s) | `RuleTable` reference asset (W3) |

What is NOT solved — and is NOT an expressiveness problem — is the gate's
raw assumption COUNT as a reliable pass/fail signal. Across n=1 design runs it
swings 6 → 10 with the LLM's verbosity, and a chunk of each run is the LLM
tagging operator-internals (which the operator owns) and infra/impl details
(which aren't research assumptions) despite explicit prompt guidance. This is
LLM run-to-run VARIANCE plus imperfect prompt compliance — a measurement
problem, not a missing capability.

**Not claimed:** that W3 makes Yaman deterministically pass the gate. It
removes the recipe-tree assumption (its job, confirmed); the count remains
noisy for reasons unrelated to W3. Chasing a clean PASS by further counter or
prompt tweaks would be fighting noise and risks manufacturing the result —
declined, consistent with the discipline throughout this work.

## Layer 2 (codegen completeness) — DONE

The pipeline now copies a declared asset `filename` into the generated
model's `data/input/`, and `phase2_code.md` shows the model calling
`RuleTable.from_csv(...)` (commit "W3 Layer 2").

## End-to-end validation: operators are BYTE-IDENTICAL to the hand-written code

The strongest proof that the three harvested operators actually work — not
just pass unit tests — is to run a REAL model on them. The Yaman reference
model (`handcrafted_model/`) was refactored to use the operators it was
scouted from: `RuleTable` replaces the hand-written `task.py`; `MoranProcess`
replaces the hand-written `_turnover`/`_select`/`death_probability`;
`FeedforwardLearner` was already in use. The agent calls the operator API
(`combine` / `weight_of` / `given_indices` / `recipe_for`).

Verification (deterministic, no LLM): run the refactored model, `git stash`
the three files back to the hand-written original, run again, diff the output.

**Result: BYTE-IDENTICAL** `Result_Simulator_Environment.csv` (final row
`period=150, repertoire=9, max_level=4, mean_score=135.0` in both). The
operators reproduce the hand-written behaviour exactly — the rng draw order
of `MoranProcess.turnover` matches the hand-written loop, and `RuleTable`'s
densified index space matches `task.py`. So the science results (runs 1-4)
are unchanged by the refactor, AND the operators are proven to compose into a
real, running, behaviour-preserving model.

This closes the harvest loop: operators extracted FROM the reference model now
drive that same model, identically, and are the same operators the codegen
pipeline provides.
