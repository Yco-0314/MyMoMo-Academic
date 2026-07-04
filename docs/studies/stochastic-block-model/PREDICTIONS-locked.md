# Stochastic Block Model — Detectability Threshold — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Decelle, Krzakala, Moore & Zdeborová 2011 (PRE
84:066106), not tuned. **Network-generation + community inference (disclosed).** Verified; gate-checked.

**Model:** q=2 equal groups, N ≥ 5000. Average degree c = 3; within/between edge rates c_in/N, c_out/N
with c_in + c_out = 2c, parameterized by ε = c_out/c_in. Detectability threshold: c_in − c_out = 2√c
(ε_c = (√c − 1)/(√c + 1) = 0.268 at c=3). A community detector (belief propagation OR a
non-backtracking / normalized-Laplacian spectral method) recovers the planted partition; measure the
OVERLAP Q = (accuracy − 1/q)/(1 − 1/q) after the optimal label permutation. ≥10 realizations.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Deep-detectable recovery (ε=0.1, well below ε_c). | mean overlap Q ≥ 0.5 (≥75% of nodes correctly labelled); a matched Erdős-Rényi graph (same degree) gives Q ≤ 0.1. |
| P2 | Deep-UNDETECTABLE failure (ε=0.5, well above ε_c). | mean overlap Q ≤ 0.15 (indistinguishable from the 50% chance baseline) AND not statistically separable from a matched ER graph's Q. |
| P3 | Monotone detectability sweep across the threshold. | sweep ε ∈ {0.05,0.10,0.15,0.20,0.35,0.50}: Q(ε=0.05) − Q(ε=0.50) ≥ 0.4; Q at ε≤0.10 is ≥0.5 while Q at ε=0.50 is ≤0.15. (Do NOT require the empirical crossover to sit exactly at 0.268 — finite N smears it.) |

**Discipline:** q, N, c, ε grid, detector, realizations FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep-with-gate):** no built model has planted community structure OR a detectability
phase transition; the information-theoretic threshold (structure exists but is UNDETECTABLE below 2√c) is
a property ER/WS/BA/config-model cannot exhibit — the matched-ER control (Q≈0) is the gate.
