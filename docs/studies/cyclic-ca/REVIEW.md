# Cyclic cellular automaton (Fisch-Gravner-Griffeath 1991) — review

**tier: deep** (1 honest MISS on a load-bearing locked design assumption). CA (disclosed).

## Mandatory cheap checks
- numeric-provenance: **pass** — headline/bundle (n=8 change-fraction 1.00, period 8.0; n=16 change 1.00) match results.
- fair-control: **pass** — P1 (n=8) vs P2 (n=16) vs P3 (period) is a clean single-parameter (colour count n) sweep on one rule.
- no-post-lock-drift: **pass** — graded verbatim vs the lock committed at e6f4f29 BEFORE the run; L3 gate fingerprints FINDINGS+lock+spec (doc_hashes_checked=3, failed_verdicts=1).
- mechanism-aliveness: **pass** — the rule genuinely cycles: n=8 gives change-fraction 1.0 AND colour-return period exactly 8, the signature of organised cyclic waves (every cell advances +1 colour/step, returns every n).
- framing-disclosure: **pass** — cellular automaton, disclosed.

## Adversarial verification of the honest MISS (P2)
The locked P2 asserted "n=16 is inside the fixating (debris) regime." An independent colour sweep on THIS
implementation (128×128, 300 steps, tail-mean change-fraction) refutes the *locked assumption*, not the model:

    n=8..20 → change-fraction 1.00 (fully active / spiral)
    n=24    → 0.32 (transitional)
    n=28-32 → 0.04-0.06 (mostly fixating)
    n=36    → 0.00 (fixates)

So under the Moore range-1 / threshold-1 rule actually specified, the spiral→fixation critical colour count
n_c ≈ 24-36 — n=16 is still deep in the SPIRAL phase. The Fisch-Gravner-Griffeath spiral-vs-fixation
dichotomy is reproduced faithfully; my locked n=16 simply sat on the wrong side of a threshold that depends
strongly on neighbourhood range/threshold. This is a **miscalibrated locked bar (my design error), not a model
bug and not a tuning failure** — the builder reported MISS rather than move n to pass. Anti-fabrication core held.

## Verdict: SOUND. 2/3 REPRO + 1 adversarially-confirmed honest MISS.
P1 spiral phase at n=8 (REPRO), P3 colour-return period = n = 8 (REPRO) jointly confirm organised rotating
cyclic waves; P2 (n=16 fixation) is a MISS because the true fixation onset is n_c≈24-36 for this rule, not 16.
The lockable science — a spiral→fixation transition governed by the colour count n — is present and correct;
only the numeric location of the transition in the lock was off. 17 faithfulness tests. No tuning.

REVIEW COMPLETE (deep tier)
