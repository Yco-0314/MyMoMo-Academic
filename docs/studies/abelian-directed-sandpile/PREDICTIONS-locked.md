# Directed abelian sandpile (1989) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Dhar & Ramaswamy 1989 (Phys Rev Lett 63:1659), not tuned.
**CA (disclosed).** Verified; gate-checked.

**Model:** directed abelian sandpile on a 2D lattice tilted so grains propagate only "downward". A site topples
when its height reaches the threshold, sending its grains to a preferred DOWNSTREAM subset of neighbours (the
anisotropic rule). Drive at the top / random site, relax downward to the open bottom boundary, record the
avalanche size (number of topplings) and its longitudinal (drive-direction) vs transverse spatial extent.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Theory-pinned exponent τ = 4/3. | discrete-MLE avalanche-size tail exponent τ lies in [1.2, 1.5], consistent with the EXACT Dhar-Ramaswamy value 4/3 ≈ 1.333. |
| P2 | Anisotropic avalanche geometry. | avalanches are directionally biased: the mean longitudinal extent (along the drive) exceeds the mean transverse extent by ≥ 2× (directed propagation, unlike isotropic BTW). |
| P3 | Heavy-tailed, exactly-scaling sizes. | the avalanche-size distribution spans ≥ 2 decades AND the max avalanche ≥ 100× the median nonzero avalanche. |

**Discipline:** lattice size, drive, threshold, transient/collection windows, seeds FIXED; metrics locked; no
tuning. Falsified → MISS. gate_design_check: τ over the scaling region via MLE (theory-pinned, tighter than the
BTW prior but still a wide band); anisotropy is a geometric observable measured from each avalanche's bounding box.
**Distinctness (keep):** ANISOTROPIC downward-only toppling makes the model exactly solvable with a distinct,
theory-fixed exponent τ = 4/3 and a measurable directional avalanche anisotropy that isotropic btw_sandpile
(τ ≈ 1.2, no directional bias) cannot exhibit.
