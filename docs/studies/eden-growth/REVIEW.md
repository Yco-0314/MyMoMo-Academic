# Eden growth (KPZ interface) — review

**tier: minimal** (all-REPRO 3/3, textbook-exact exponents; no MISS). Hybrid particle growth on a grid.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (D=1.97, β=0.346, α=0.549) matches bundle/results.
- fair-control: **pass** — the compact-disk / DLA contrast is the negative control for the bulk-D estimator; the α fit is across a monotone L-sweep.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; KPZ exponent bands not tightened; L3 gate fingerprints FINDINGS.
- mechanism-aliveness: **pass** — the growth mechanism is alive: bulk fills space (D≈2), the interface roughens with the correct KPZ exponents (β 0.346, α 0.549, both R²>0.99).
- framing-disclosure: **pass** — stochastic particle growth on a grid (hybrid), disclosed.

## Verdict: SOUND. 3/3 REPRO, textbook KPZ.
P1 compact bulk D=1.971 (space-filling, the DLA contrast); P2 KPZ growth β=0.346 (1/3, R²=0.996); P3 KPZ
roughness α=0.549 (1/2, R²=0.992), W_sat monotone. The Eden/KPZ universality-class signature reproduces
cleanly — a rough growing interface no built model has. 8 tests. Module written by a builder that stalled;
test + runner authored centrally. No tuning.

REVIEW COMPLETE
