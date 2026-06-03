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

## Run 3 (generalization sweep) — pre-registered NEGATIVE. All MISS.

P_G ∈ {.5,.9} × lr ∈ {.02,.08}, N=50, gen=150, 16 reps. Final repertoire:

| cell          | P_S | P_SL | P_G | lr   | repertoire | max_level |
|---------------|-----|------|-----|------|-----------|-----------|
| random        | 0   | 0    | 0   | .05  | 11.8 ± 1.2 | 5.2 |
| social        | 0   | .9   | 0   | .05  | **31.2 ± 4.4** | **8.4** |
| sem_g0        | .9  | 0    | 0   | .05  | 10.1 ± 1.5 | 4.3 |
| sem_g5_lo     | .9  | 0    | .5  | .02  | 8.9 ± 0.8 | 3.8 |
| sem_g9_lo     | .9  | 0    | .9  | .02  | 7.9 ± 0.5 | 3.1 |
| sem_g5_hi     | .9  | 0    | .5  | .08  | 9.4 ± 1.0 | 4.1 |
| sem_g9_hi     | .9  | 0    | .9  | .08  | 8.2 ± 0.4 | 3.2 |
| semsoc_g9_lo  | .9  | .9   | .9  | .02  | 14.1 ± 7.9 | 5.3 |
| semsoc_g9_hi  | .9  | .9   | .9  | .08  | 12.9 ± 6.7 | 5.0 |

- **P-E (generalization rescues solo): MISS.** Best solo gen cell (9.4) is
  BELOW random (11.8). Generalization makes semantic-solo WORSE.
- **P-F (generalization > predict): MISS.** 9.4 < sem_g0 10.1.
- **P-G (generalization+social synergy): MISS.** semsoc 14.1 ≪ social 31.2.

More generalization is monotonically WORSE (P_G .5→.9 lowers repertoire),
and semantic agents converge SHALLOW (max_level 3-4 vs random 5.2, social
8.4). The deterministic `nearest` collapses generalization into a narrow
neighbourhood of the same few known recipes (the same failure mode as
argmax), and the per-agent M starves for training data solo.

## Overall conclusion (runs 1-3): MECHANICS reproduce, SEMANTIC BENEFIT does not

What reproduces, from the REAL recipe tree + SI algorithms + the W2 operator:
- the Totem task and crafting dynamics;
- **social learning robustly increases the cultural repertoire and depth
  (31.2, level 8.4) — faithful to the paper's Fig 2A** and the single
  largest effect here.

What does NOT reproduce: **the paper's headline novel claim — that semantic
knowledge guides innovation and synergises with social learning.** Across
runs 1-3, EVERY semantic configuration (predict-chain at lr∈{.001,.05,.2};
generalization at P_G∈{.5,.9}×lr∈{.02,.08}) UNDERPERFORMS uniform random,
and adding semantics to social learning HURTS rather than helps. No tested
configuration shows a semantic benefit.

This is an honest negative, and it is the disciplined process working: an
earlier version of this project fabricated a successful method-transfer
result; here, locking predictions and reading real output before believing
the story caught two of my own premature "reproductions" (run-2's artifact
synergy; the lr non-application) and produced a truthful negative instead
of a manufactured HIT.

**Most likely cause: the SI pseudocode under-specifies the productive
semantic mechanism** (the paper repeatedly defers to "the code provided
with the paper", which is ABSENT from OSF — the ABM/ and script/ folders
are empty). The Predict/generalization details that make semantic guidance
*exploratory rather than exploitative* are not in the text we have. Named
candidate gaps (pre-registered): deterministic `nearest`/argmax collapse,
the owned-only restriction on Predict, the independent-draw reading of
P_S/P_G, and per-agent training-data starvation for M. Closing them is
speculative re-implementation, not reproduction, without the released code.

**Status: faithful partial reproduction.** Mechanics + social-learning
effect reproduced from real data; semantic-guidance claim not reproducible
from the public artifacts. Recorded as-is.

## Run 4 (stochastic soft-nearest) — P-H MISS. The negative is now robust.

The last named gap: deterministic `nearest` was replaced with a stochastic
soft-nearest (p ∝ exp(−dist/mean_dist)) — the same argmax→sampling fix that
helped the predict-chain. One bounded test, no temperature sweep.

| cell          | repertoire | max_level |
|---------------|-----------|-----------|
| random        | 11.8 ± 1.2 | 5.2 |
| social        | 31.2 ± 4.4 | 8.4 |
| sem_g9_lo     | 8.4 ± 0.6 | 3.3 |
| sem_g9_hi     | 8.6 ± 0.9 | 3.4 |
| semsoc_g9_lo  | 17.4 ± 10.2 | 5.6 |
| semsoc_g9_hi  | 14.9 ± 9.2 | 5.2 |

**P-H MISS.** Best semantic-solo (8.6) is still BELOW random (11.8), still
shallow (level 3.3-3.4). Stochastic nearest did not help. **Determinism was
not the blocker.** Per the pre-registered falsification, tuning stops here.

## FINAL VERDICT (runs 1-4)

The semantic-guidance benefit does NOT reproduce under ANY mechanism
variant tried:
- predict-chain: argmax (run 1, harmful) and sampling (run 2, neutral),
  across lr ∈ {.001, .05, .2};
- generalization: deterministic nearest (run 3, harmful) and stochastic
  nearest (run 4, harmful), across P_G ∈ {.5, .9} × lr ∈ {.02, .08}.

In every case semantic agents underperform uniform random and converge
shallow (level 3-4 vs random 5.2, social 8.4): the semantic model becomes
an exploitation bias that suppresses exploration. Pure social learning is
the robust winner (31.2, level 8.4), faithful to the paper's Fig 2A.

**This is a faithful PARTIAL reproduction**: the Totem task, crafting
dynamics, and social-learning effect reproduce from the real recipe tree +
SI algorithms + the W2 operator; the paper's headline semantic-guidance
claim is NOT reproducible from the public artifacts. The most likely cause
is that the SI under-specifies the productive semantic mechanism and the
released ABM code is absent from OSF (empty folders). Recovering it (the
authors' GitHub, or contacting them) is the only path to a TRUE test of the
semantic claim; everything beyond run 4 would be speculative re-
implementation, which is not reproduction.

The process is the result: locking predictions and reading real output
turned what an earlier (fabricating) version of this project would have
called a "successful reproduction" into an honest, well-evidenced negative
— and caught two of my own premature conclusions along the way. That is the
Gate/Harness discipline (ADR-012/013) doing exactly its job.
