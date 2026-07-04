# Drossel–Schwabl Forest Fire (SOC) — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Drossel & Schwabl (1992), not tuned.
**Cellular automaton (SOC), NOT agent-decision** — disclosed in FINDINGS.

**Model:** L×L grid (L=128), cells empty/tree/burning. Each tick: burning→empty; tree with a
burning NN→burning; empty→tree w.p. p=0.05; tree→burning (lightning) w.p. f=p/1000 (scale
separation). Record fire sizes (cells burnt per lightning fire) in the stationary state
(≥10⁴ fires after transient). Fit the fire-size tail exponent τ (method fixed before run).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Power-law fire sizes (SOC). | fitted tail exponent τ ∈ [1.0, 2.5] |
| P2 | Heavy-tailed (scale-free over a range). | spans ≥2 decades; max fire ≥ 100× median nonzero |
| P3 | Self-organizes to a stationary density (init-independent). | stationary tree density converges to the same value from 2 different inits (within ±0.05) |

**Discipline:** L, p, f, fit method, transient FIXED + metric locked; no tuning of kmin/binning.
Honest caveat: forest-fire SOC is only approximately scale-free (known large-size deviations);
report the fit range. Falsified → MISS.
