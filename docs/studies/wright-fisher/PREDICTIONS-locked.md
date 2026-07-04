# Wright-Fisher Neutral Drift — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is the classic Wright-Fisher neutral result,
not tuned. Genuine agent-based.

**Model:** N=100 haploid allele agents (A/a), initial A-fraction p0. Each generation: sample
N parents WITH replacement uniformly (neutral). Run to fixation. Outcome = fixation prob of A
(≥2000 runs per p0) + heterozygosity H=2p(1−p) decay. Sweep p0∈{0.2,0.5,0.8}.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Fixation prob = initial frequency. | fixation prob of A within ±0.05 of p0 for each p0 |
| P2 | Heterozygosity decays ~(1−1/2N)/gen. | measured per-gen H decay factor in [1−2/N, 1−1/(4N)] (report vs the 1/N law) |
| P3 | Neutral drift (no selection bias). | mean A-fraction across runs ≈ p0 until absorption (E[Δp]≈0) |

**Discipline:** N, p0 grid, run count FIXED + metric locked; no tuning. Falsified → MISS.
