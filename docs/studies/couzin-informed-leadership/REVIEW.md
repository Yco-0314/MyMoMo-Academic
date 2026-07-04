# Couzin et al. informed leadership (2005) — review

**tier: deep (adversarially verified)** — 2/3 REPRO + 1 honest MISS (density-confounded size comparison). genuine-agent (disclosed).

## Cheap checks + adversarial verification
- numeric-provenance: **pass** — bundle (P1 acc 0.92 at p=0.10, P2 fraction 0.033/0.300, P3 offset 84.8deg) matches results; FINDINGS.md sha256 fingerprinted in the bundle (docs.findings), L3 gate satisfied.
- fair-control: **pass** — P1 sweeps informed fraction at fixed N; P3 is a clean small-theta vs large-theta A/B on the same two-subgroup setup.
- no-post-lock-drift: **pass** — graded vs lock ed6fe16 BEFORE run; bundle fingerprints predictions_locked + findings + design_spec.
- mechanism-aliveness / adversarial: **pass** — independent probe at a FIXED informed fraction p=0.10 shows accuracy FALLS with group size (N=30 -> 0.964, N=100 -> 0.836, N=200 -> 0.821), directly confirming the P2 density confound (see below). P1 (few leaders steer) and P3 (averaging->commitment) are alive and non-degenerate.
- framing-disclosure: **pass** — zonal SPP with informed minorities, disclosed.

## The honest MISS (P2 leader economy)
P2 required the informed fraction needed to reach accuracy 0.9 to be STRICTLY SMALLER for N=200 than N=30.
Observed the opposite (0.300 at N=200 vs 0.033 at N=30). Adversarially-confirmed cause: the zone radii were held
FIXED across N, so the larger group is sparser and less cohesive — at a matched fraction p=0.10 accuracy
monotonically DROPS with N (0.964/0.836/0.821 for N=30/100/200). Couzin 2005's 1/N leader-economy holds at
constant DENSITY (radii/domain scaled with N); the locked P2 did not control density, so it falsifies. A design
subtlety in the locked experiment, NOT a model bug and NOT tuning. Reported honestly as MISS.

## Verdict: SOUND. 2/3 REPRO + 1 honest (density-confounded) MISS.
P1 a small informed minority steers a large group (accuracy 0.92 at 10% informed); P3 the group averages small
directional conflicts (offset 15deg at theta=40) but commits on large ones (offset 85deg at theta=150). The
size-scaling leader economy (P2) does not reproduce under fixed-radius (non-density-controlled) size comparison.
25 tests. No tuning.
REVIEW COMPLETE (deep tier, adversarially verified)
