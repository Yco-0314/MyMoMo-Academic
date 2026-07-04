# Greenberg-Hastings excitable-media CA (1978) — review

**tier: minimal+ (adversarially verified)** — 3/3 REPRO, one honestly-disclosed discreteness nuance. CA (disclosed).

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (spiral period 6 over ~29-37 rotations; annihilation in 4 steps; L_c grows with r) matches bundle/results.
- fair-control: **pass** — P2 is a genuine collision test: an independent probe confirms a SINGLE planar front crosses the whole grid (the medium transmits), while two head-on fronts annihilate (transmitted=False) — annihilation is a real collision outcome, not a propagation failure.
- no-post-lock-drift: **pass** — graded vs the lock committed e6f4f29 BEFORE the run; L3 gate fingerprints FINDINGS+lock+spec (failed_verdicts=0).
- mechanism-aliveness: **pass** — independent re-run: measure_spiral period=6, 29 rotations, 6670 excited cells still active (a live rotating spiral, not decayed); critical_size r=4→8, r=8→8, r=12→12 (finite, non-decreasing in r).
- framing-disclosure: **pass** — deterministic 3-state CA, disclosed.

## Adversarial note (honest discreteness disclosure)
P1's measured spiral rotation period is 6 = T+1 (T=1+r=5), not exactly T, because the discrete rotating arm's
pivot waits one extra tick for the core to finish refractoriness. The locked clause allowed ±1 so it REPROs
honestly, and FINDINGS + bundle state openly that a check demanding EXACTLY T would have wrongly failed it. No
tuning; r=4 is the spec default and the period is always ≥ T across an r-sweep. Independent probe reproduces
period 6.

## Verdict: SOUND. 3/3 REPRO (adversarially verified).
P1 rotating spiral with a fixed period (6 = T+1, within the locked ±1); P2 head-on wavefront annihilation with
confirmed isolated-front transmission; P3 finite refractory-set re-entry size L_c that grows with r. The
excitable-media signatures — annihilating fronts, fixed spiral period, refractory-set critical size — all
reproduce. 20 faithfulness tests. No tuning.

REVIEW COMPLETE (minimal+, adversarially verified)
