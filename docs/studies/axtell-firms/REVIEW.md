# Axtell Model of Firms (Zipf sizes) — adversarial review

**tier: deep** (trigger: 2 honest MISSes). Reviewed vs the verified claim + lock. The builder
consulted the primary Axtell 1999 text and REJECTED two unfaithful variants that would cross P2/P3.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (slope −1.28, Gini 0.47, kurtosis 0.59) matches bundle/results.
- fair-control: **n/a** — single-population stationary study; mechanism faithfulness verified vs the primary source (lazy per-agent effort, {stay, singleton, 2 fixed-friend firms}, ν=2 fixed network, equal sharing).
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; the builder explicitly rejected eager re-optimization + fresh-sampled candidates (which would cross P2/P3) as UNFAITHFUL — the opposite of tuning.
- mechanism-aliveness: **pass** — endogenous firm formation is alive: Zipf slope −1.28 (exactly Axtell's base-case µ=1.28), mean firm size 2.67, max ~83, ~1872 firms; the effort FOC quadratic was re-derived + verified vs a line search.
- framing-disclosure: **pass** — genuine agent-based, disclosed.

## Verdict: model FAITHFUL; P2 + P3 are HONEST MISSes (empirical bars vs faithful accessible-N base case).
- **P1 REPRO** — Zipf firm sizes: rank-size log-log slope = −1.28 ∈ [−1.5,−0.7], MATCHING Axtell's own base-case exponent µ=1.28. The headline power-law reproduces exactly.
- **P2 MISS** — firm-size Gini 0.47 vs the locked 0.60. Strongly right-skewed but the FAITHFUL base case concentrates less than the empirical ~0.89. **The 0.60 bar was calibrated to empirical data; the accessible-N base-case simulation does not reach it** — and the two variants that would (contribution-based sharing, eager re-opt) are unfaithful to Axtell's base case, so the builder correctly declined them.
- **P3 MISS** — log-growth excess kurtosis 0.59 vs 1.5. The sign is correct (leptokurtic) and σ-vs-size slope −0.078 < 0 (Stanley scaling holds directionally, matching Axtell's γ≈0.17), but not Laplace-strength at N=5000.

## Discipline check: PASS — one of the strongest of the session.
1/3 REPRO honestly; the builder REFUSED two bar-crossing shortcuts because they are unfaithful (the ideal
of the no-tuning discipline). The Zipf signature (P1) reproduces exactly; the Gini/kurtosis MAGNITUDES were
locked at empirical/large-N values the faithful accessible-N base case does not reach. 20 tests.

REVIEW COMPLETE

## Addendum (peer-verifier flags on the LOCKED bars, post-commit — honest record)
A consultant agent checked the locked P2/P3 bars against the primary Axtell 1999 text and flagged that
**MY LOCK mis-specified them** (a gate-design failure on my side, documented here — the committed verdict is
NOT changed, only clarified):
1. **P2's Gini ≥ 0.60 has NO basis in Axtell 1999.** The paper reports no Gini/Lorenz; its concentration
   claim IS the power-law exponent µ=1.28 — which P1 REPRODUCED exactly. The 0.89 figure is empirical US
   firm-size data from Axtell 2001 (Science), not a 1999 base-case model prediction. So the P2 "MISS vs 0.60"
   is against an unsourced bar; the paper's actual concentration claim is reproduced.
2. **P3's Stanley slope −0.078 vs Axtell's γ=0.174** is likely a pooling/binning artifact — Axtell fit γ
   AFTER dropping firm sizes 1–3; including the small-size rise + sparse tail biases the slope toward zero.
   A same-window refit may recover ~0.15–0.17; if it stays ~0.08 it is a legitimate miss.
**Net:** the headline is unchanged — P1 (Zipf µ=1.28) solid, mechanism faithful, no tuning. But P2's bar
should have been the power-law exponent (REPRO), not an unsourced Gini; this is the recurring pre-lock
gate-design lesson (verify each bar is the PAPER's claim, not an empirical figure) in its sharpest form.
