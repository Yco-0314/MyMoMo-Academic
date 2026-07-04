# Watts 2002 Global Cascades — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running any reproduction.** Predictions are Watts' (2002)
published claims, not tuned to our implementation. Source: PNAS 99(9):5766–5771
(open: https://pmc.ncbi.nlm.nih.gov/articles/PMC122850/).

**Model (faithful):** ER random graph, n=10,000, mean degree z. Uniform threshold
φ=0.18. Node adopts state 1 iff fraction of active neighbors ≥ φ (degree-0 nodes
vulnerable). Single random seed, run to fixed point. Global cascade = final active
fraction ≥ 0.10 (bimodal sizes → cutoff robust). Frequency over ≥100 random seeds per z.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Cascade frequency is **non-monotonic** in z: an interior window (≈0 at low z, a peak at intermediate z, ≈0 at high z). | freq(low z)≈0 AND freq(mid z)>0 AND freq(high z)≈0 |
| P2 | Lower window boundary near the ER giant-component / connectivity onset (z≈1). | first z with freq>0 is in [~0.8, ~2] |
| P3 | Upper window boundary is a finite z (canonical ≈5.8 for φ=0.18); above it cascades vanish because vulnerable vertices (k≤K=⌊1/φ⌋=5) stop percolating. | last z with freq>0 is in [4, 7] |
| P4 | Cascade-size distribution is **bimodal** (tiny local vs system-spanning global). | within the window, sizes split into a small-O(1/n) mode and a large-O(1) mode |

**Discipline:** φ=0.18, n=10000, cutoff 0.10, seed count fixed BEFORE the run; no tuning
to make a window appear. A falsified clause is reported MISS. Measured boundaries are
reported as-is and compared to the canonical ~[1, 5.8].
