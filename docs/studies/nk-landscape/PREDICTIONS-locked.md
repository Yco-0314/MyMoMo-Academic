# Kauffman NK Landscape — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Kauffman & Levin (1987), not tuned.
Adaptive-walker agents on a tunably-rugged landscape.

**Model:** N=15 binary loci; fitness = mean of N per-locus contributions, each depending on its
locus + K others (random tables). Sweep K∈{0,2,4,8,14}. Count local optima (enumerate 2^15;
a genotype fitter than all N single-flip neighbours) + adaptive-walk length (greedy hill-climb
from random starts). Mean over ≥5 random landscapes per K.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Ruggedness grows with K. | mean #local optima increases monotonically with K |
| P2 | K=0 is single-peaked. | K=0 → exactly 1 local optimum |
| P3 | Adaptive walks shorten with K. | mean greedy-walk length decreases monotonically with K |

**Discipline:** N, K grid, #landscapes, enumeration FIXED + metric locked; no tuning. Falsified → MISS.
