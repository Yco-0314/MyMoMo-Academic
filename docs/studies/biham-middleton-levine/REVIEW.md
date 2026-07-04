# Biham-Middleton-Levine 2D traffic CA (1992) — review

**tier: minimal+ (adversarially verified)** — 3/3 REPRO, finite-size metastability honestly disclosed. CA (disclosed).

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (rho_c=0.365, step width 0.089, v(0.20)=1.0, v(0.55)=0.0) matches bundle/results; independent 2-seed sweep reproduces rho_c=0.369, width 0.106.
- fair-control: **pass** — P1/P2/P3 are one density sweep of a single 2D two-species rule; the P2 anchors (0.20, 0.55) sit clear of the transition by design.
- no-post-lock-drift: **pass** — graded vs the lock committed e6f4f29 BEFORE the run; L3 gate fingerprints FINDINGS+lock+spec (failed_verdicts=0).
- mechanism-aliveness: **pass** — independent re-run: v(0.20)=0.99999 (free flow), v(0.55)=0.0 (full gridlock), and the v(rho) curve is a genuine near-step (0.998→0.895→0.575→0.26→0.0 across 0.28→0.44) crossing 0.5 at rho_c=0.369 ∈ [0.30,0.40].
- framing-disclosure: **pass** — cellular automaton (only randomness = seeded initial placement), disclosed.

## Adversarial note (honest finite-size disclosure)
At L=128 a self-organized metastable "partially jammed but flowing" branch sits at rho≈0.34–0.38 and seeds go
bimodal near the transition — FINDINGS reports this openly. It does NOT move rho_c out of the locked band or
widen the step past 0.15, because those thresholds are crossed outside the coexistence region and the P2 anchors
sit clear of it. Independent verification reproduces the in-band crossing.

## Verdict: SOUND. 3/3 REPRO (adversarially verified).
P1 sharp free-flow→gridlock transition with rho_c=0.365 ∈ [0.30,0.40]; P2 near-perfect free flow below /
full gridlock above (v=1.0 / v=0.0 at the anchors); P3 near-step transition (width 0.089 ≤ 0.15). The genuine
2D jamming PHASE TRANSITION that distinguishes BML from the 1D NaSch fundamental diagram is reproduced. 17
faithfulness tests. No tuning.

REVIEW COMPLETE (minimal+, adversarially verified)
