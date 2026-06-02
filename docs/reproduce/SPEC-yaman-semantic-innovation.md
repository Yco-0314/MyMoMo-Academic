# Reproduction Spec — Yaman, Tian, Lindström (PNAS 2026): Semantic Knowledge Guides Innovation

**Source**: main paper + SI, PNAS 123(22) 2026 / arXiv 2510.12837.
Extracted 2026-06-01 via `docs/reproduce/_extract_pdf.py` (main) and
`_extract_pdf_cid.py` (SI, CID-font decode). Every line traces to
/tmp/yaman_clean.txt or /tmp/yaman_si_cid.txt. Items marked ⛔ are
genuine gaps, NOT guessed.

This is the "read the important points fully" artifact for Track 2,
before any implementation.

## Model in one paragraph

A population of agents performs a **combinatorial innovation task**
("Totem"): combine ≤3 items from inventory into a recipe; a valid recipe
yields a new item. Agents explore via three strategies (random /
semantic / generalization), learn a **distributional semantic model** (a
small neural net mapping an item to a distribution over items that
complete a recipe), socially learn recipes from the top scorer, and
undergo **Moran-style** turnover where offspring inherit the parent's
semantic model but not its items. Cultural repertoire + semantic
knowledge co-evolve.

## Algorithm 1 — Cumulative Cultural Evolution loop (verbatim structure)

```
function CCE(P_SL, P_S, ep, ...):
    # ep = number of innovation attempts each individual makes per generation
    # P_D = age-based death probability (see below)
    I ← Initialize individuals()
    g = 0
    while g < max(Gen):
        while each individual i ∈ I performs ep attempts:
            i ← select a random individual from the population
            if rand < P_SL:                      # SOCIAL LEARNING
                access inventory of the highest-score individual
                if there is an item i lacks that i CAN craft from its inventory:
                    randomly pick one such recipe, execute it
                    ep ← ep − 1
                else:
                    IndividualModel(i)            # fall back to Algorithm 2
                    ep ← ep − 1
        I ← updateModels(I)   # retrain semantic models on all successful recipes so far
        for each i ∈ I:
            if rand < P_D:    Reinitialize(i)     # probabilistic death
        K ← Selection(I)      # parents ∝ success
        O ← Reproduction(K)   # offspring = copies of selected parents
        I ← join(K, O)
        g ← g + 1
```

**Death probability** (age-based, Gompertz-like): `P_D = a · e^(b·x)`
with x = individual age, **a ≈ 0.0001365, b ≈ 0.2097** (⛔ exact form's
superscript was garbled in extraction; the two constants are
confirmed-visible).

## Algorithm 2 — Individual innovation (verbatim structure)

```
function IndividualModel(i):
    # P_S = prob of using semantic model; P_G = prob of generalization
    n = randint(1, 2, 3)         # how many items this attempt
    T ← {}
    if rand > P_S:               # (1) RANDOM strategy
        T ← select n items from inventory, uniform, with replacement
    else if rand > P_G:          # (2) SEMANTIC strategy
        item1 ← first item, uniform random from inventory
        if n == 1: T ← {item1}
        if n > 1:  item2 ← Predict(model, item1)      # NN predicts a complement
                   T ← {item1, item2}
        if n == 3: item3 ← Predict(model, item2)
                   T ← {item1, item2, item3}
    else:                        # (3) GENERALIZATION strategy
        T ← one successful recipe from memory, uniform
        pick one item in T; replace it with the item CLOSEST in embedding space
    if T not in memory:
        if T leads to innovation: add innovation to inventory
        AddMemory(T)
```

Note the branch logic uses `rand > P_S` / `rand > P_G` (greater-than),
so high P_S means MORE random. Verify sign at implementation time
against the figures — ⛔ the prose uses `>` but this may be an extraction
artifact of a `<`; the parameter sweep {0,0.1,0.5,0.9} interpretation
depends on it.

## Semantic knowledge model (confirmed)

- Feedforward ANN, **single hidden layer, baseline 16 neurons**
  (swept {8,16,32}), ReLU activation, **softmax** output over items.
- Estimates **p(y | x)**: given input item x, distribution over the item
  y that completes a successful recipe.
- **Item embeddings** are the learned input representations (size swept
  {8,16,32}). Functionally-related items cluster in embedding space.
- Trained by **cross-entropy loss + backpropagation** on all successful
  recipes the agent has acquired (own + socially learned).
- `Predict(model, item)` = forward pass, sample/argmax the complement.
- Generalization uses **nearest-neighbor in embedding space**.

## Parameters — SI Table 1 (confirmed ranges; baselines partly ⛔)

| Parameter | Symbol | Swept values | Baseline |
|---|---|---|---|
| Hidden-layer neurons | — | {8, 16, 32} | **16** (main text) |
| Item embedding size | — | {8, 16, 32} | ⛔ (likely 16) |
| Prob. of death | P_D | age-based eqn | a=0.0001365, b=0.2097 |
| Prob. of using semantic model | P_S | {0, 0.1, 0.5, 0.9} | ⛔ |
| Prob. of social learning | P_SL | {0, 0.1, 0.5, 0.9} | ⛔ |
| Prob. of generalization | P_G | {0, 0.1, 0.5, 0.9} | ⛔ |
| Population size | N | 25, 50, 100 | **100** |
| Max generations | max(Gen) | — | ⛔ (cost analysis references 10) |
| Attempts/individual/gen | ep | — | ⛔ |
| Semantic-model cost | — | 1× … 3× | 1 (baseline) |

⛔ Remaining gaps: bold-baseline of P_S/P_SL/P_G/embedding; exact
max(Gen); ep; learning rate + epochs per `updateModels`; exact death-eqn
functional form. All obtainable from the figures or the **released code**
(SI: "see the code provided with the paper" — a real repo exists; find
it for a TRUE reproduction).

## Totem task structure (confirmed)

- 6 initial items.
- 11 innovation levels, item counts per level: 6, 4, 2, 2, 2, 3, 3, 7,
  11, 48, 96.
- Combinations limited to ≤ 3 items.
- Recipes identical across semantic / non-semantic experimental
  conditions (only the item *depiction* differs for humans; irrelevant
  to the ABM).

## Headline results to reproduce (from main text)

1. Semantic knowledge → directs exploration to meaningful solutions,
   higher innovation success, generalization from prior discoveries.
2. Semantic knowledge **interacts synergistically with social learning**
   to amplify innovation and accelerate cultural evolution.
3. Even at 3× cost, using the semantic model remains advantageous.
4. Effect holds across population sizes 25/50/100.

## abm-auto feasibility (honest)

- ✅ Moran loop, inventory, recipe task, 3-way exploration branch:
  expressible as a MechanismSpec + environment.step.
- ⚠️ **The embedded trainable ANN semantic model is the hard part** — a
  per-agent learned representation updated by backprop each generation.
  This is the "operator-missing" wall: codegen has never been asked to
  produce an agent that *trains a neural net* as part of its step. Real
  test of whether the architecture extends beyond fixed-rule agents.
- The `Predict` + nearest-neighbor-in-embedding operations need the
  agent to carry model weights + embeddings as state → ties to the
  event-stream / agent-level collection prerequisite.

## Next (not done here — spec only)

Find the released code repo (true reproduction vs re-implementation),
then resolve the ⛔ baselines, then implement. No implementation in this
artifact.

---

## UPDATE 2026-06-03 — gap RESOLVED with real data + implemented (Path 2)

The two blockers above are closed.

**The ⛔ recipe-tree gap is resolved with the REAL released data, not a
re-implementation guess.** The paper's OSF repo (osf.io/m642a) was pulled
via its API; `data/empirical/rules_tidied.csv` is the exact 184-item
innovation tree (`c1,c2,c3 -> item`, `given`, real `point` scores,
semantic captions). Saved to
`examples/reproduce_yaman_semantic_innovation/reference_data/`. Loading it
and computing levels reproduces the paper's distribution exactly:
`[6,4,2,2,2,3,3,7,11,48,96]`. Recipe sizes: 4 one-item, 98 two-item,
76 three-item. Items 32 & 35 are hubs feeding all 96 level-10 totems as
`{32,35,X}` — the structural source of similarity-based generalization.

**The ⚠️ trainable-ANN wall is closed by W2.** The SI ANN (1 hidden layer,
16 ReLU, softmax, cross-entropy, backprop — SI lines 380-387) IS
`abm_auto.runtime.FeedforwardLearner`. The agent never implements the net.

**Real algorithms (SI Algorithms 1 & 2), now implemented:**
- Alg 1 (generation): N×n_attempts random-interleaved attempts (each
  w.p. P_SL social-learning, else individual) → updateModels (train each
  agent's M on its successful recipes) → Gompertz death
  `P_D=0.0001365·e^(0.2097·age)` → fitness-proportional Moran rebirth
  (offspring inherits parent's M, resets to base inventory).
- Alg 2 (individual): `rand>P_S` random; else `rand>P_G` semantic
  Predict-chain; else generalization (swap a recipe item for its
  embedding-nearest neighbour).

**Parameters (SI Tables 1 & 2), main-text defaults bolded in paper:**
N∈{25,**50**,100}, n_attempts∈{5,**10**,15}, embed/hidden∈{8,**16**,32},
P_S/P_SL/P_G∈{**0**,0.1,0.5,0.9}, lr=0.001.

**Documented assumptions (PDF defers to code; OSF code folder is empty):**
max generations (we use 150), train_epochs/generation (5), exact Alg-2
rand-draw semantics (we use independent draws for P_S then P_G), and
Predict/nearest restricted to OWNED items (you can only combine items you
hold). Score is NOT assumed — we use the real per-item `point` values.

**Implementation:** `handcrafted_model/` (6-file abm-auto contract +
`task.py` loader + `run_experiment.py`). Pre-registered science
predictions: `PREDICTIONS-yaman-science.md` (committed before the run).
