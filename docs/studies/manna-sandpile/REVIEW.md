# Manna stochastic sandpile (1991) — review

**tier: minimal+ (adversarially verified)** — 3/3 REPRO. CA / SOC (disclosed).

## Cheap checks + adversarial verification
- numeric-provenance: **pass** — bundle (tau=1.262, heavy tail 4.57 decades, occupancy 0.699) matches results.
- fair-control: **pass** — single stochastic two-grain toppling rule; exponent/tail/occupancy from one avalanche ensemble.
- no-post-lock-drift: **pass** — graded vs lock d7599ab BEFORE run; L3 gate fingerprints FINDINGS+lock+spec.
- mechanism-aliveness / adversarial: **pass** — verifier re-ran exact config (L=64) reproducing tau=1.262 bit-for-bit; robust across seeds/L (tau=1.273, 1.276 at L=48, dead on Manna 2D ~1.27); MLE cross-checked against an independent grid-search on planted power-law data (both 1.24, so the estimator is not a rigged constant); log-binned histogram spans ~5 decades with real counts in every decade; stationary occupancy 0.699 (neither frozen ~2 nor drained ~0).
- framing-disclosure: **pass** — stochastic SOC CA, disclosed.

## Verdict: SOUND. 3/3 REPRO (adversarially verified).
Manna-class exponent tau=1.262 (distinct from BTW), genuine heavy tail, finite critical active density. 18 tests. No tuning.
REVIEW COMPLETE (minimal+, adversarially verified)
