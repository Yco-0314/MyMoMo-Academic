# Price cumulative-advantage citation model — adversarial review

**tier: deep** (trigger: 1 honest MISS). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (p_0=0.571, γ̂=2.21, m=1 contrast 2.74, k_max≈2734) matches bundle/results.
- fair-control: **pass** — P3's m=1 vs m=3 contrast varies only m (the a/m knob); the BA comparison is the distinctness gate.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; L3 gate ok; a self-citation bug was caught + fixed in tests.
- mechanism-aliveness: **pass** — cumulative advantage is vividly alive: constant out-degree 3, in/out variance ratio ~2.6e5, p_0=4/7, and a heavy γ<3 tail.
- framing-disclosure: **pass** — network-generation (directed growth), disclosed.

## Verdict: model FAITHFUL; P1 is an HONEST MISS from a MIS-CALIBRATED bar (not a bug — the model OVER-produces hubs).
- **P2 REPRO** — never-cited mass p_0 = 0.571 = 4/7 exactly (analytic (m+1)/(2m+1)); BA structurally gives 0.
- **P3 REPRO** — tunable tail: γ̂=2.21 (m=3, decisively <3) and the m=1 contrast rises to 2.74 (~0.53 gap), directly exhibiting γ=2+a/m tunability that fixed-γ=3 BA cannot show.
- **P1 MISS** — two of three conjuncts pass overwhelmingly (out-degree exactly 3, Var(in)/Var(out)≈2.6e5 ≫ 50); the failing conjunct is the locked `k_max ∈ [40,400]`: at the mandated N≥50k the hub is k_max≈2734, ~7× over the ceiling. **The [40,400] upper band was mis-calibrated (it corresponds to N≈1–2k), while the same P1 clause pins N≥50k where k_max is far larger.** The hub OVERSHOOTS (a heavier tail = MORE Price-like), so the mechanism is correct; the bar's upper bound was wrong. The builder did NOT shrink N to slip under (discipline forbids it). Honest MISS.

## Discipline check: PASS. Recurring bar-calibration lesson.
2/3 REPRO reported honestly; no tuning. The distinctness from BA is fully established (directed DAG, constant
out-degree, p_0=4/7, tunable γ<3 — all REPRO). The single MISS is a lock upper-bound that should have been
open-above (k_max grows with N), the same class of pre-lock bar-calibration gap seen across recent batches.
19 tests.

REVIEW COMPLETE
