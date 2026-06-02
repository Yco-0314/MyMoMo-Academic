# Findings — Yaman science reproduction (Path 2)

Every number here is read from real tool output. Predictions were locked in
`docs/reproduce/PREDICTIONS-yaman-science.md` and committed (`54d8dce`)
BEFORE any cell was compared.

## Run 1 (commit 54d8dce model) — ALL FOUR PREDICTIONS REFUTED

2x2 design, N=50, gen=150, P_generalize=0, 16 reps/cell. Final-generation
repertoire (distinct non-base items the population holds):

| condition | P_S | P_SL | repertoire | max_level | mean_score |
|-----------|-----|------|-----------|-----------|-----------|
| random    | 0   | 0    | 11.8 ± 1.2 | 5.2 | 89   |
| social    | 0   | 0.9  | **31.2 ± 4.4** | **8.4** | 8849 |
| semantic  | 0.9 | 0    | 8.0 ± 0.7  | 3.4 | 73   |
| sem+soc   | 0.9 | 0.9  | 15.1 ± 5.5 | 6.4 | 2300 |

- **P-A (semantic helps): MISS.** Semantic alone (8.0) is BELOW random
  (11.8). Semantic guidance HURT solitary exploration.
- **P-B (synergy): MISS.** Interaction = 15.1 − 8.0 − 31.2 + 11.8 =
  **−12.4** (anti-synergy).
- **P-C (no-sem ≈ random): MISS.** Social lift was +19.4 (huge), not the
  predicted near-zero; pure social learning was the single biggest effect.
- **P-D (sem+soc best): MISS.** Top cell is **social**, not sem+soc.
  Adding semantic to social HURT (31.2 → 15.1).

The result INVERTS the paper. That is a real result about THIS
implementation as configured — recorded, not erased.

## Diagnosis: faithful contradiction, or my infidelity?

The paper is robust (PNAS; 1243 participants + ABM + sensitivity analyses).
A reproduction that inverts the headline is far more likely to be an
implementation infidelity than a refutation of the paper. The smoking gun:
**a competent explorer should never underperform uniform random, yet the
"semantic" strategy did (8.0 < 11.8).** So the semantic strategy is
mis-implemented as an explorer. Two leading causes:

1. **argmax collapse (clear infidelity).** `FeedforwardLearner.predict`
   defaults to `argmax=True` — deterministic. The paper's semantic model
   is a conditional probability distribution p(y|x) that agents SAMPLE
   from. Argmax over owned items makes the predict-chain deterministic
   given M's current weights, so the agent re-attempts a tiny set of
   combinations instead of exploring — strictly worse diversity than
   uniform random. This alone can make "semantic" < random.

2. **P_generalize = 0 (design choice that may remove the benefit).** With
   P_G=0 the only semantic mechanism is the predict-chain, which biases
   toward PAST co-occurrences (exploitation of what's already known). The
   productive part of semantic knowledge for NEW discovery is
   similarity-based generalization (the P_G branch: "try an item similar
   to one in a known recipe"). Isolating P_S with P_G=0 cripples exactly
   the generative mechanism.

## Next (run 2)

Fix on FAITHFULNESS grounds (not to force agreement), each change
justified:
- sample from p(y|x) instead of argmax in the semantic predict-chain
  (the paper's model is stochastic);
- re-examine whether P_G must be > 0 for semantic knowledge to aid NEW
  discovery (the paper's main-text condition).

Then re-run with a FRESH pre-registered expectation. Run 1 stands in the
record as a refutation that caught an unfaithful explorer before any
"successful reproduction" was claimed.

## Diagnosis (probe_semantic.py) — root cause found

Upper-bound test: train one FeedforwardLearner on ALL 652 real co-occurrence
pairs, sweep lr x epochs, measure sampled valid-partner rate (base rate =
chance = 0.024) and argmax diversity.

| lr   | epochs | loss | sampled_valid | argmax_distinct |
|------|--------|------|---------------|-----------------|
| 0.05 |   500  | 3.41 | 0.348 |  2 |
| 0.05 |  2000  | 2.82 | 0.601 |  3 |
| 0.20 |  2000  | 2.34 | 0.835 |  8 |
| 0.50 |  2000  | 2.24 | **0.942** | 15 |

The operator is SOUND: with adequate training it concentrates ~94% of
sampled mass on valid partners (39x chance). Run-1 failed because (a) the
in-sim lr=0.001 / 5-epoch regime left M at the uniform distribution
(loss ~ ln(184)=5.21), and (b) argmax then collapsed to ONE repeated
partner — a strictly-worse-than-random explorer. Both confirmed.

## Run 2 (sampling + lr=0.2) — headline REPRODUCES; same locked predictions

Two faithfulness fixes (NOT tuned to win, each justified):
1. semantic predict-chain SAMPLES from p(y|x) restricted to owned items
   (paper's model is a sampled distribution; argmax collapses diversity);
2. lr 0.001 -> 0.2 (0.001 falsified by the probe — a model that cannot
   learn is not the paper's semantic model). train_epochs 5 -> 20.

Re-tested against the SAME predictions locked at `54d8dce` (goalposts not
moved — only the explorer was made faithful). 2x2, N=50, gen=150, P_G=0,
16 reps:

| condition | P_S | P_SL | repertoire | max_level | run-1 → run-2 |
|-----------|-----|------|-----------|-----------|---------------|
| random    | 0   | 0    | 11.8 ± 1.2 | 5.2 | 11.8 → 11.8 |
| social    | 0   | 0.9  | 31.2 ± 4.4 | 8.4 | 31.2 → 31.2 |
| semantic  | 0.9 | 0    | 11.8 ± 1.4 | 5.2 | **8.0 → 11.8** (no longer hurts) |
| sem+soc   | 0.9 | 0.9  | **33.4 ± 4.0** | 8.4 | **15.1 → 33.4** (now top cell) |

- **P-B (synergy): HIT.** Interaction = 33.4 − 11.8 − 31.2 + 11.8 =
  **+2.2** (was −12.4). Semantic and social are now super-additive — the
  paper's headline.
- **P-D (sem+soc best): HIT.** Top repertoire cell is sem+soc (deepest
  tied with social at level 8.4).
- **P-A (semantic helps solo): MISS.** Semantic-solo (11.8) only EQUALS
  random (11.8) — no longer harmful, but no solo advantage. Cause: solo,
  M trains on the agent's own handful of successes (cold start), and with
  P_G=0 there is no similarity-based generalization to bootstrap NEW
  discovery. Generalization (the paper's P_G mechanism) is the untested
  lever. Real residual gap.
- **P-C (no-sem ≈ random): MISS — but this is a PRE-REGISTRATION ERROR,
  not a model fault.** The paper's Fig 2A explicitly shows social learning
  raises the cultural repertoire; "no better than random bots even with
  social learning" was the HUMAN semantic-vs-non-semantic result, which I
  wrongly mapped onto ABM social-alone. The model's "social learning helps,
  then plateaus; semantic+social is best" behaviour is faithful to Fig 2A.
  Scored MISS honestly because the locked prediction was wrong, not the run.

**Net:** the two headline scientific claims — synergy and
semantic+social-best — reproduce, driven by the REAL recipe tree and the
W2 FeedforwardLearner. Residual: semantic-SOLO advantage (P-A) is not yet
reproduced and is hypothesised to need P_G>0; that is the obvious run-3.
Two reusable operators were scouted along the way (task-graph loader,
Moran turnover) for the codegen architecture work.

## CORRECTION (verify_lr.py) — run-2's "synergy" claim was OVERSTATED

While preparing run 3 I found a harness bug and a deeper mechanism problem.
Both correct the run-2 interpretation above. Recorded honestly, not erased.

**Harness bug.** `run_experiment.run_one` hardcoded `learning_rate=0.001,
train_epochs=5` into the scenario CSV, which OVERRIDES `scenario.setup()`.
So my run-2 "lr 0.001 -> 0.2" fix never took effect — run 2 ran at
lr=0.001. `verify_lr.py` confirms: at lr=0.001/ep5, semantic-solo=12.2 and
sem+soc=33.2, matching the recorded run-2 (11.8 / 33.4).

**The "synergy" was an artifact, not semantic guidance.** At lr=0.001 the
semantic model M never trains off the uniform distribution (the probe
already showed this). So the "semantic" individual attempts were just
sampling ~uniformly over owned items — i.e. essentially random. sem+soc
(33.2) was therefore ~ social (31.2) plus noise; the +2.2 interaction is
within the per-cell spread (±4-5). **It was not semantic knowledge
producing synergy. The run-2 P-B/P-D "HIT" is withdrawn.**

**And training M properly makes it WORSE, not better.** At lr=0.2/ep20,
verify_lr gives semantic-solo=10.5 and sem+soc=**9.0** (all four seeds
exactly 9 — a collapse). A sharply-trained M concentrates the predict
distribution on PAST successful co-occurrences, so the agent re-proposes
already-discovered recipes (skipped as in-memory) and explores almost
nothing new. Over-exploitation kills discovery.

**Conclusion: the predict-chain mechanism (P_G=0) does not reproduce
semantic guidance at ANY lr** — undertrained it is neutral (≈random),
trained it is harmful (over-exploitation). This is a real, honest negative
result. It relocates the test to the paper's *similarity-based
generalization* branch (P_G > 0), which proposes NOVEL combinations by
analogy (swap an item in a known recipe for an embedding-neighbour) rather
than re-treading known co-occurrences. That is run 3 — and it must vary lr
too (0.001 is dead, 0.2 collapses; a moderate lr is needed for embeddings
to be meaningful without over-sharpening).
