# Cont-Bouchaud percolation market — review

**tier: light** (all-REPRO 3/3, but P1's ">N× control" ratio has a disclosed ill-definedness — reviewed). Network-generation + trading.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (kurtosis 3.563, P(|r|>3σ)=0.0208, α=3.36) matches bundle/results; re-run byte-identical (deterministic).
- fair-control: **pass** — the critical (c=1, a=0.05) vs control (below-threshold c=0.2 / high-a=0.49) arms differ only by regime; the a-sweep for P3 varies only activity.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; the ratio-handling is disclosed in FINDINGS, not a silent metric change; L3 gate ok.
- mechanism-aliveness: **pass** — fat tails arise from the power-law cluster-size distribution at percolation (kurtosis 3.56 at criticality vs 0.03 below threshold, 108×).
- framing-disclosure: **pass** — network-generation (percolation) + herd trading, disclosed.

## Light-tier check: the disclosed ratio caveat is honest, not a tune.
P1's locked ">5× a near-Gaussian control" is ill-defined because both controls have excess kurtosis ≤ 0
(Gaussian-or-thinner) — you cannot take a clean ratio to a non-positive denominator. The runner handles this
by requiring "critical clears the absolute > 3 bar WHILE the control is ≤ 0", which is the correct reading of
the contrast (critical fat, control not) and reports all raw numbers. This is a sound disclosed interpretation,
not a metric swap to force a pass.

## Verdict: SOUND. 3/3 REPRO.
P1 fat tails at criticality (excess kurtosis 3.56 vs 0.03 control); P2 heavy tails (P(|r|>3σ)=0.0208=7.7×
Gaussian, P(|r|>5σ)=663× Gaussian, α=3.36); P3 activity crossover (kurtosis 3.56→−0.23 monotone). The
percolation-cluster fat tail is the market stylized fact no built model (ER structure, ZI efficiency,
minority-game attendance) produces. 28 tests. No tuning.

REVIEW COMPLETE
