# BTW Sandpile (SOC) — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Bak-Tang-Wiesenfeld (1987), not tuned.
**Cellular automaton (SOC), NOT agent-decision** — disclosed in FINDINGS.

**Model:** L×L grid (L=50), heights; add 1 grain at a random cell, then topple every cell
with height ≥ 4 (cell −4, +1 to each of 4 neighbours; boundary grains lost) until stable.
Avalanche size s = number of topplings per added grain. Discard transient, collect ≥10⁵
avalanches. Fit tail exponent τ (method fixed before run).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Power-law avalanche sizes, τ≈1.2 (2D). | fitted τ ∈ [0.9, 1.6] |
| P2 | Heavy-tailed (scale-free), not exponential. | spans ≥2 decades; max avalanche ≥ 100× median |
| P3 | Self-organizes to a critical mean height. | stationary mean height ∈ [2.0, 2.2] |

**Discipline:** L, drive, topple rule, fit method, transient cutoff FIXED + metric locked
before run; no tuning of kmin/binning to hit 1.2. Falsified → MISS.
