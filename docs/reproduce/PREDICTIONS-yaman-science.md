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

---

# Run 3 — does similarity-based GENERALIZATION reproduce semantic guidance?

**Committed BEFORE run 3.** Runs 1-2 tested only the predict-chain (P_G=0),
which the correction in `FINDINGS-science.md` showed does not reproduce
semantic guidance at any lr (neutral when undertrained, over-exploiting
when trained). Run 3 tests the paper's actual *similarity-based
generalization* mechanism (the P_G branch): take a known successful recipe,
swap one item for its embedding-nearest owned neighbour — proposing a NOVEL
combination by analogy. lr is swept because it sets whether embeddings are
meaningful (0.001 dead, 0.2 collapsed; test moderate 0.02 / 0.08).

Runner: `run3_generalization.py` → `results/experiment_run3.csv`.
N=50, gen=150, 16 reps. Grid (label, P_S, P_SL, P_G, lr):
random(0,0,0,.05), social(0,.9,0,.05), sem_g0(.9,0,0,.05),
sem_g5_lo(.9,0,.5,.02), sem_g9_lo(.9,0,.9,.02),
sem_g5_hi(.9,0,.5,.08), sem_g9_hi(.9,0,.9,.08),
semsoc_g9_lo(.9,.9,.9,.02), semsoc_g9_hi(.9,.9,.9,.08).

## Predictions

- **P-E — generalization rescues semantic-solo.** The best semantic-solo
  generalization cell (over P_G∈{.5,.9} × lr∈{.02,.08}) exceeds random by
  more than one random-cell SD: max(sem_g*) > random + sd(random).

- **P-F — generalization beats the predict-chain.** That best
  semantic-solo generalization cell > sem_g0 (predict-only, P_G=0).

- **P-G — generalization restores REAL synergy.** semsoc_g9 (best of lo/hi)
  > social AND > the matching sem-solo cell — i.e. generalization + social
  is super-additive, this time driven by a semantic mechanism that
  demonstrably helps solo (unlike run 2's artifact).

## Falsification

- P-E refuted if NO generalization config lifts semantic-solo above
  random+sd. Then similarity-based generalization, as implemented, does
  not reproduce the semantic benefit either — an honest negative result
  pointing to a remaining faithfulness gap (e.g. deterministic `nearest`,
  the owned-only restriction, or the independent-draw P_S/P_G reading).
- P-G refuted if semsoc_g9 ≤ social (no synergy beyond social learning).

A negative run 3 is reported as negative. The goal is to learn what the
implementation actually does, not to manufacture a HIT.
