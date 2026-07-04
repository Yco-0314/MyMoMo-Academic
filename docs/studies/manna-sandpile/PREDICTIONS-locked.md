# Manna sandpile — stochastic SOC (1991) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Manna 1991 (J Phys A 24:L363), not tuned.
**CA (disclosed).** Verified; gate-checked.

**Model:** two-state stochastic sandpile on a 2D L×L lattice with open boundaries. Each site holds a height;
a site is critical when height ≥ 2. Toppling: a critical site loses 2 grains, each sent to an INDEPENDENTLY,
RANDOMLY chosen nearest neighbour (the stochastic rule — this is what separates Manna from deterministic
BTW). Drive: add 1 grain at a random site, relax to stability (avalanche = number of topplings), record.
Discard a transient, then collect avalanche sizes at stationarity.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Manna-class avalanche exponent. | discrete-MLE tail exponent τ of the avalanche-size distribution lies in [1.20, 1.40] (Manna 2D ≈ 1.27), and differs from a BTW-style deterministic fit only within this band. |
| P2 | Heavy-tailed, not exponential. | the avalanche-size distribution spans ≥ 2 decades AND the max avalanche ≥ 100× the median nonzero avalanche. |
| P3 | Finite stationary active density. | with stochastic toppling the pile reaches a stationary state with finite mean occupancy (grains per site) in [0.6, 0.95] — a genuine critical steady state, not a frozen or fully-drained lattice. |

**Discipline:** L, boundary, drive, transient/collection windows, seeds FIXED; metrics locked; no tuning.
Falsified → MISS. gate_design_check: τ via discrete MLE + lower-cutoff over the scaling region needs many
avalanches (≥ 10⁴); P3 occupancy band is the honest MISS-risk clause; P1/P2 are the load-bearing SOC signatures.
**Distinctness (keep):** RANDOM two-grain redistribution defines a separate (Manna / conserved-directed-
percolation) universality class from btw_sandpile (deterministic, 4 fixed neighbours) and from
olami_feder_christensen (non-conservative continuous forces).
