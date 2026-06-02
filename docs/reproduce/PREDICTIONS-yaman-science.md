# Pre-registered predictions — Yaman et al. science reproduction (Path 2)

**Committed BEFORE the experimental run.** This is the anti-fabrication gate
(ADR-012): the predictions and falsification conditions are locked to git
first; results are read from real tool output afterward and scored honestly,
misses recorded as misses.

## What is being reproduced

The headline scientific claims of Yaman, Tian & Lindström, *"Semantic
knowledge guides innovation and drives cultural evolution"* (PNAS 2026 /
arXiv 2510.12837), in the agent-based model:

1. Semantic knowledge (a trained distributional model that predicts which
   items combine) guides exploration toward productive combinations.
2. It **interacts synergistically with social learning** to amplify
   cultural accumulation.
3. **Without semantic knowledge, agents do no better than random — even
   with social learning.**

This is a reproduction of the **phenomenon** (the qualitative ordering and
the sign of the interaction), not of the paper's exact repertoire numbers:
the recipe tree and ANN are real (OSF `rules_tidied.csv`; FeedforwardLearner
matches the SI ANN), but max-generations / per-generation training epochs /
exact score base are documented assumptions (the PDF defers them to "the
code provided with the paper", which is absent from OSF). See
`SPEC-yaman-semantic-innovation.md`.

## Locked design

- Model: `examples/reproduce_yaman_semantic_innovation/handcrafted_model/`
- 2x2 cells, `P_generalize = 0`:

  | label    | P_semantic | P_social |
  |----------|-----------|----------|
  | random   | 0.0       | 0.0      |
  | social   | 0.0       | 0.9      |
  | semantic | 0.9       | 0.0      |
  | sem+soc  | 0.9       | 0.9      |

- N = 50, n_attempts = 10, generations = 150, embed=hidden=16, lr=0.001,
  train_epochs = 5. REPS = 16 (seeds 0..15). DV = **repertoire_size** =
  distinct non-base items the population holds at the final generation
  (max possible 178). Secondary DV = `max_level` reached.
- Runner: `run_experiment.py` → `results/experiment_results.csv`.

Let R(s, l) = mean final repertoire_size over 16 reps at P_semantic=s,
P_social=l.

## Predictions

- **P-A — semantic knowledge helps.** R(0.9, 0) > R(0, 0) AND
  R(0.9, 0.9) > R(0, 0.9). Semantic guidance raises discovery in both
  the solitary and the social setting.

- **P-B — synergy (super-additive interaction).** The 2x2 interaction is
  positive:  R(0.9,0.9) − R(0.9,0) − R(0,0.9) + R(0,0) > 0. Social
  learning adds MORE when semantic knowledge is present than when it is
  absent.

- **P-C — no semantic ⇒ no better than random, even with social.** The
  social-only lift is small next to the semantic lift:
  R(0,0.9) − R(0,0)  ≪  R(0.9,0) − R(0,0). (Copying spreads existing
  items but discovers few new ones without semantic guidance, so the
  *distinct*-items DV stays near the random baseline.)

- **P-D — semantic + social is best and deepest.** R(0.9,0.9) is the
  largest of the four cells, and sem+soc reaches the highest mean
  `max_level`.

## Falsification conditions (pre-registered)

- P-A refuted if either semantic cell ≤ its non-semantic counterpart
  (means within noise, or reversed).
- P-B refuted if the interaction term ≤ 0 (social adds no more, or less,
  under semantic knowledge).
- P-C refuted if R(0,0.9) approaches the semantic cells, i.e. social
  learning alone substantially closes the gap to semantic.
- P-D refuted if sem+soc is not the top cell on repertoire_size.

## Scoring

After the run: read `results/experiment_results.csv`, compute the four
cell means (+ a spread), score each prediction hit/miss against the
condition above, and write the scorecard. A refuted prediction is
reported as refuted — that is a real result about either the model
faithfulness or the phenomenon, not a defect to paper over.
