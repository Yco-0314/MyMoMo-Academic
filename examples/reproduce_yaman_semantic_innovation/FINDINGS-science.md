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
