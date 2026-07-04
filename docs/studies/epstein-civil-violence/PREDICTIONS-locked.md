# Epstein 2002 Civil Violence — PREDICTIONS (locked)

**Locked 2026-06-29, BEFORE running.** Claim is Epstein's (2002), not tuned. Source:
PNAS 99(suppl 3):7243–7250.

**Model (faithful):** 40×40 grid. Populace agents: grievance G=H·(1−L), H~U[0,1],
legitimacy L a global parameter; risk-aversion Ri~U[0,1]; estimated arrest prob
P=1−exp(−k·(C/A)_local) over vision (C cops, A actives incl. self; k=2.3). Agent ACTIVE
iff G − Ri·P > threshold T=0.1, else quiescent. Cops move to a random cell in vision and
arrest a random active there (jail term J~U{1..Jmax}). All agents move to a random empty
cell in vision each tick. Outcome = active fraction over time. Average over ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | High legitimacy → calm. | L=0.9: mean active fraction < 0.05 |
| P2 | Low legitimacy → punctuated rebellion bursts. | L=0.5: burstiness (peak active / mean active) ≥ 5 OR mean active ≥ 0.10 |
| P3 | Deterrence: more cops → less rebellion. | active fraction is monotonically non-increasing across cop densities {2%,4%,6%} at fixed L |

**Discipline:** grid, k, threshold, jail term, densities, L values FIXED + the metrics
locked before the run; no tuning. Falsified clause → MISS.
