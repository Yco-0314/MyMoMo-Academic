# Fermi-rule spatial PD (Szabó-Tőke 1998) — adversarial review

**tier: deep** (trigger: 2 honest MISSes). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (c(1.4)=0.541, β≈1.34, b_cr rise 0.078) matches bundle/results.
- fair-control: **pass** — P1/P2 on the self-interaction von Neumann spec, P3 on the no-self-interaction spec (documented per the lock); each clause varies only b or K.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; the builder self-corrected an initial over-optimistic P2=REPRO draft to the honest MISS and re-fingerprinted the bundle (discipline working).
- mechanism-aliveness: **pass** — the Fermi stochastic reciprocity is alive: cooperators survive above b=1 (c(1.4)=0.541) with a smooth intermediate density a deterministic rule cannot produce; the transition is continuous; the K-peak exists.
- framing-disclosure: **pass** — genuine agent-based stochastic pairwise-comparison update, disclosed.

## Verdict: model FAITHFUL; P2 + P3 are HONEST MISSes on hard quantitative bars (not bugs).
- **P1 REPRO** — c(b=1.4, K=0.1)=0.541 ∈ [0.35,0.65] AND c(b=1.9)=0.0004 (all-D). Spatial+stochastic reciprocity confirmed; the smooth intermediate density distinguishes it from the deterministic nowak_may.
- **P2 MISS** — the transition IS continuous (max Δb=0.02 drop 0.046 ≪ 0.20 ✓) but the fitted DP exponent β≈1.34 is far outside [0.45,0.75]. Extracting the directed-percolation β requires large L + careful finite-size scaling; at the accessible L the fit is off. The QUALITATIVE continuity (the load-bearing distinction from a discrete-step deterministic rule) holds; the exponent VALUE misses.
- **P3 MISS** — the peak-K location is correct (K=0.32 ∈ [0.2,0.5] ✓) but the b_cr rise 0.078 falls just under the locked 0.10 magnitude bar. The non-monotonic optimal-K effect is present; its magnitude at this size is slightly short.

## Discipline check: PASS. Self-corrected + honest.
1/3 REPRO reported honestly; no tuning; the builder caught + retracted its own over-optimistic P2 draft. The
qualitative Szabó-Tőke results (survival above b=1, continuous transition, optimal intermediate K) all
reproduce; the precise critical exponent (β) and threshold-shift magnitude are hard to hit at accessible
lattice sizes — the same class of quantitative-bar difficulty seen across batch-10. 16 tests.

REVIEW COMPLETE
