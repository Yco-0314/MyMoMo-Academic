# Reproduction Plan — Demo 2 (Ricci × SIR) + Semantic-Innovation Model

**Status: PLAN. Written 2026-06-01. Both reproductions are wanted (user
decision: "两个都要"). This file separates CONFIRMED facts from
PENDING-verification gaps so no implementation is written on guessed
content — the anti-fabrication discipline.**

## Two tracks, both committed

### Track 1 — Demo 2: Ollivier-Ricci curvature × SIR transmission graph

The literal GeomHerd-for-disease reproduction. Method × existing domain.

**CONFIRMED (from repo inspection 2026-06-01):**
- SIR `environment.step` applies infection `nb.state = 1` and discards
  the event — no edge-level record of "src infected dst at tick t".
  (`examples/calibration_challenge_virus/handcrafted_model/core/environment.py:29`)
- DataCollector has env-level + agent-level collection only; **no
  event-stream**. (`abm_auto/runtime/_data_collector.py`)
- Static Watts-Strogatz contact graph exists; the TIME-VARYING
  transmission graph (edges that actually fired) does not.

**WALL: W1 (data-missing).** Blocked until the transmission graph is
collectable.

**Prerequisite work (real architecture, not a demo hack):**
1. Add an **event-stream collection mode** to DataCollector:
   `record_event(src_id, dst_id, kind, tick)`. Third collection type
   beside env-level and agent-level.
2. Instrument `VirusEnvironment.step` to emit an infection event on each
   successful spread.
3. Rebuild the time-varying transmission graph from the event stream.
4. Implement / depend-on Ollivier-Ricci curvature (needs optimal
   transport / Sinkhorn — heavier than CSD's rolling stats).
5. Apply the surrogate-null guard (degree-preserving rewire) — the
   method-transfer rigor — before claiming any curvature signal.

This prerequisite (event-stream) is exactly what the probe matrix
predicted Type-D/E/G methods need. Demo 2 forces it. It is genuine W7
infrastructure, not throwaway.

### Track 2 — Reproduce Yaman, Tian, Lindström (PNAS 2026 / arXiv 2510.12837)

"Semantic knowledge guides innovation and drives cultural evolution."
Full-model reproduction (closer to the user's original intent than a
method-transfer probe).

**CONFIRMED (from web search 2026-06-01, sources below):**
- Real paper: Anil Yaman, Shen Tian (田申), Björn Lindström, PNAS
  123(22), 2026. Preprint: arXiv 2510.12837 (fetchable → reproducible).
- Combines an **agent-based model** of cultural evolutionary dynamics
  with a **behavioral experiment (N=1,243)**.
- Claim: semantic knowledge (associations linking concepts to properties
  / functions) directs exploration toward meaningful solutions and
  interacts synergistically with social learning to amplify innovation.
- Repo already has `examples/classic_axelrod_culture` — a cultural-
  evolution ABM that may serve as scaffolding or reference.

**CONFIRMED — mechanism (from main-paper PDF text extracted 2026-06-01,
`docs/reproduce/_extract_pdf.py` → /tmp/yaman_clean.txt; every line below
traces to that text, none from memory):**

- **Task: combinatorial innovation.** Each individual holds an
  *inventory of items*. It attempts to combine items into a *recipe*; a
  successful recipe yields a new item — but only if the individual can
  produce it from items already in its inventory. (Same family as the
  combinatorial-innovation task in the paper's ref 10/34, e.g. Little-
  Alchemy-style crafting.)
- **Two exploration channels:** individual innovation (try combinations)
  + social learning (observe others' successful recipes). After
  attempts, individuals update their semantic model from ALL acquired
  recipes (own or observed).
- **Semantic knowledge = a distributional semantic model.** Each item is
  a vector in a high-dimensional space. An item's meaning = its
  functional context (co-occurrence with other items in successful
  recipes). Initially all vectors sit near the origin (no relations). As
  successful innovations are discovered/observed, representations update
  so items in similar functional contexts (e.g. red paint & blue paint,
  both combinable with a log) cluster together. Items never in a
  successful combination keep uninformative vectors. The semantic model
  PREDICTS which combinations are likely to succeed → biases exploration
  toward meaningful solutions.
- **Population dynamics: Moran-style selection.** Some individuals die
  and are replaced by offspring of more-successful individuals
  (overlapping generations). Offspring INHERIT the parent's semantic
  model but start with only the basic inventory — they must rebuild
  specific items via innovation/social-learning while benefiting from
  inherited semantic knowledge. → cultural repertoire + semantic
  knowledge co-evolve.
- **Experimental design (validation against humans):** semantic
  condition (real-world items, prior semantics usable) vs nonsemantic
  condition (abstract symbols, semantics removed); each run individually
  or in groups (groups enable real-time social learning). Human N=1,243.
- **Headline result (confirmed abstract text):** semantic knowledge
  directed exploration toward meaningful solutions, enhanced innovation
  success, enabled generalization from prior discoveries, AND interacted
  *synergistically* with social learning to amplify innovation and
  accelerate cultural evolution.

**CONFIRMED — parameters (SI appendix, re-extracted 2026-06-01 via
`docs/reproduce/_extract_pdf_cid.py`, which decodes the Type0/CID fonts
through their ToUnicode CMaps; the first stdlib extractor failed on
these. Every value below traces to /tmp/yaman_si_cid.txt):**

- **Semantic model = feedforward ANN, single hidden layer, 16 neurons,
  ReLU activation, softmax output over items, cross-entropy loss,
  trained by backpropagation.** It estimates p(y|x): given input item x,
  the conditional distribution over which item completes a successful
  recipe. (SI "Semantic knowledge model".) Item *embeddings* are the
  learned input representations; embedding size is swept in sensitivity
  analysis.
- **Innovation task = "Totem"**: hierarchical, 6 initial items, 11
  innovation levels with item counts 6, 4, 2, 2, 2, 3, 3, 7, 11, 48, 96.
  Combinations limited to ≤3 items (online-adapted). Recipes identical
  across semantic/nonsemantic conditions.
- **Population sizes tested: 25, 50, 100** (baseline 100 individuals).
- **Two behavioral probabilities** (Algorithm 1/2): **PSL** = probability
  of social learning, **PS** = probability of using the semantic model;
  each compared against a uniform random draw to branch behavior.
- **Moran-style loop (Algorithm 1):** probabilistic death per individual
  → Selection of survivors as parents (prob ∝ success) → Reproduction
  (offspring = copies of selected parents) → population = parents +
  offspring → next generation. Max 10 generations referenced in cost
  analysis.
- **Cost parameter:** using the semantic model can carry a cost (baseline
  1 = no extra cost); robustness shown up to 3× cost.
- **Algorithms 1 (population CCE) and 2 (individual innovation)** are
  given as pseudocode in SI — directly portable to a MechanismSpec.
- **Transmission-noise robustness:** Gaussian noise (σ = 0.2 or 2) added
  to NN weights + embeddings (params typically in [−1, 1]).

**CONFIRMED — SI Table 1 (Individual model parameters), extracted
verbatim. These are the SWEEP RANGES; main text states the baseline
hidden-layer size is 16:**

| Parameter | Symbol | Values swept |
|---|---|---|
| Hidden-layer neurons | — | {8, 16, 32} |
| Item embedding size | — | {8, 16, 32} |
| Probability of death | P_D | see Algorithm 1 (age-based) |
| Probability of using semantic model | P_S | {0, 0.1, 0.5, 0.9} |
| Probability of social learning | P_SL | {0, 0.1, 0.5, 0.9} |
| Probability of generalization | P_G | {0, 0.1, 0.5, 0.9} |

- **Death probability is age-based** (Algorithm 1): P_D = exp(a·x) form
  with constants a ≈ 0.0001365, b ≈ 0.2097 and x = individual age (exact
  functional form needs a cleaner pull of the equation — the CID extract
  garbled the superscript).
- There is also a **third behavioral knob P_G (generalization)** — I had
  not seen this before the SI table; it joins P_S and P_SL. Each is
  compared against a uniform random draw to branch behavior.

**STILL PENDING (genuinely not yet pinned — do NOT guess):**
- ⛔ Which value in each {…} set is the bolded BASELINE (bold markup did
  not survive CID extraction; main text fixes hidden=16, the rest need
  the figure or code). Likely P_S=P_SL=0.5-ish but UNCONFIRMED.
- ⛔ Exact death-probability equation (superscript garbled).
- ⛔ Learning rate / epochs per semantic-model update.
- ⛔ Number of innovation attempts per individual per generation (symbol
  shown, value not cleanly pulled).

**Code/data availability:** SI says "see the code provided with the
paper" — a real code artifact exists. The OpenCLIP/Zenodo refs are for
their sentence-embedding baseline, NOT the ABM code. Locating the
paper's own released code would make this a TRUE reproduction (run their
code) vs a re-implementation (rebuild from spec). Worth finding before
Track 2 implementation.

**Mechanism + parameter ranges now confirmed from the real SI via CID
decoding. Remaining gaps are bold-baseline values + two equations,
obtainable from the figures or the released code.**

## Feasibility judgment for Track 2 (honest, post-extraction)

Can abm-auto generate this model today? Partially — with one real wall:

- ✅ Agents + Moran selection + inventory: current runtime can express.
- ✅ Combinatorial recipe task: encodable as a state/action structure.
- ⚠️ **Distributional semantic vector model + online update is NOT a
  standard ABM operator.** It is a learning sub-system embedded in each
  agent (vectors, functional-context updates, similarity-driven
  exploration bias). Whether CoderAgent can generate this correctly is a
  genuine open question — an order of magnitude harder than SIR/Schelling
  mechanism code. This is the Track-2 analogue of Track-1's W1 wall: not
  "data missing" but "**operator missing** — the method needs a learned
  representation the codegen vocabulary doesn't yet cover."
- ⛔ Exact parameters still pending (SI extraction failed).

This makes Track 2 a strong stress test of the codegen/originate path:
it probes whether the architecture can express *agents that learn a
representation*, not just agents with fixed transition rules.

## Sequencing (proposed, user to confirm)

Both tracks share the **event-stream DataCollector** prerequisite
(Track 1 needs it for the transmission graph; Track 2 needs agent-level
innovation + recipe-acquisition history). So:

0. ✅ **DONE** — mechanism extracted from main paper, written above.
1. **补 SI 参数** — re-extract SI with a working decoder (or user
   supplies the Methods params). Deferred until after the reflection
   pass, per user.
2. **Event-stream collection mode** in DataCollector — shared
   infrastructure, unblocks both tracks. Byte-equal gate on existing
   outputs.
3. **Track 1**: instrument SIR + Ricci + guard.
4. **Track 2**: generate semantic-innovation model from the confirmed
   mechanism + (once obtained) SI parameters, via originate/reproduce.

Each step: artifact before conclusion, predictions before runs, real
output read before any writeup. No batch execution unsupervised.

## Sources

- PNAS abstract: https://www.pnas.org/doi/abs/10.1073/pnas.2530750123
- arXiv preprint: https://arxiv.org/abs/2510.12837
- Author note: https://www.anilyaman.com/post/semantic-knowledge-guides-innovation-and-drives-cultural-evolution
