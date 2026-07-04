# Maki-Thompson rumor — review

**tier: minimal** (all-REPRO 3/3, comfortable margins; no MISS). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (i_∞=0.2020, peak 0.3106) matches bundle/results.
- fair-control: **pass** — P2's rate sweep {0.5,2,4} varies ONLY the absolute contact rate (single variable).
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; integrity gate ok.
- mechanism-aliveness: **pass** — the "spreader ages out on contact with the informed" rule produces the rate-INVARIANT 0.203 constant (P2 max|Δ|=0.0) and peak 0.307 — the load-bearing distinction from SIR.
- framing-disclosure: **pass** — hybrid (well-mixed CTMC, directed pairwise contacts), disclosed.

## Verdict: SOUND. 3/3 REPRO. i_∞=0.2020 (root of θ=e^(−2(1−θ))=0.2032), rate-invariant, peak 1−ln2.
Distinctness confirmed: the rate-invariant never-hear constant is a property the built SIR (rate-dependent
final size) cannot show. No tuning, no fabrication. 16 tests.

REVIEW COMPLETE
