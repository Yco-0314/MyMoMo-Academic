# Oslo rice-pile model (1996) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Christensen et al. 1996 (Phys Rev Lett 77:107), not tuned.
**CA (disclosed).** Verified; gate-checked.

**Model:** 1D Oslo rice-pile of L sites. Each site i has a local slope z_i = h_i − h_{i+1} and a per-site
critical slope z_c^i drawn randomly in {1, 2}. Drive: add a grain at site 1. Relax: any site with z_i > z_c^i
topples (one grain moves downslope), and after each toppling that site's z_c^i is RE-DRAWN in {1, 2} (the
stochastic threshold — this is what makes a 1D pile genuinely critical, where deterministic 1D BTW is trivial).
Grains leave at the open right boundary. Avalanche size = number of topplings per driving grain, collected at
stationarity after a transient.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Oslo avalanche exponent. | discrete-MLE avalanche-size tail exponent τ lies in [1.4, 1.7] (Oslo 1D ≈ 1.55). |
| P2 | Genuinely critical in 1D. | the avalanche-size distribution spans ≥ 2 decades AND the max avalanche ≥ 100× the median nonzero avalanche — heavy-tailed, unlike a trivial (non-critical) deterministic 1D BTW pile. |
| P3 | Cutoff scales with system size. | mean avalanche size ⟨s⟩ grows monotonically with L across L ∈ {32, 64, 128, 256} (larger L ⇒ larger ⟨s⟩ — finite-size scaling of the cutoff). |

**Discipline:** L grid, threshold set {1,2}, drive, transient/collection windows, seeds FIXED; metrics locked;
no tuning. Falsified → MISS. gate_design_check: τ measured at the largest L over the scaling region via MLE;
P3 is the robust finite-size-scaling control; P1's band is wide around the known ≈ 1.55.
**Distinctness (keep):** 1D with STOCHASTIC per-site critical slopes re-drawn in {1,2} after each toppling —
this makes 1D non-trivially critical (deterministic 1D BTW is not), a different universality class and exponent
(≈ 1.55) from btw_sandpile (≈ 1.2) and forest_fire.
