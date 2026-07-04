# Sneppen interface depinning (1992, model A) — review

**tier: deep** — 2/3 REPRO + 1 honest MISS from a mis-specified locked sign. CA (disclosed).

## Cheap checks + verification
- numeric-provenance: **pass** — bundle (chi=0.654, avalanches 4.97 decades, slope-corr +0.260) matches results.
- fair-control: **pass** — one extremal-update interface; roughness/avalanches/correlation from the same run family.
- no-post-lock-drift: **pass** — graded vs lock d7599ab BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness: **pass** — self-affine interface with fitted roughness chi=0.654 in [0.5,0.75] (P1) and scale-free avalanches spanning ~5 decades (P2); 23 faithfulness tests pass.
- framing-disclosure: **pass** — extremal-dynamics interface CA in a quenched random medium, disclosed.

## The honest MISS (P3) — a mis-specified locked clause, not a model failure
P3 locked "nearest-neighbour interface-height increments are ANTICORRELATED (correlation < 0)". Measured =
+0.260 (POSITIVE). This is expected PHYSICS that my lock got wrong: a self-affine surface with roughness
exponent chi = 0.654 > 1/2 is PERSISTENT, i.e. its increments are positively correlated; anticorrelation
(anti-persistence) would require chi < 1/2. Since P1 independently measured chi=0.654 > 0.5, a positive slope
correlation is the CORRECT behaviour and the locked "< 0" was a physics mis-specification on my part. The model
is right; the clause was wrong. Builder reported the MISS honestly rather than flip the metric sign.

## Verdict: SOUND. 2/3 REPRO + 1 honest MISS (my mis-specified anticorrelation sign).
P1 self-affine roughness chi=0.654; P2 scale-free avalanches. P3 fails only because a chi>1/2 surface is
persistent (positively correlated), contradicting the anticorrelation I wrongly locked. 23 tests. No tuning.
REVIEW COMPLETE (deep tier)
