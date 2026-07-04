# Spatial Snowdrift Game (Hauert-Doebeli 2004) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Hauert & Doebeli 2004 (Nature 428:643), not
tuned. Genuine agent-based. Verified.

**Model:** L×L lattice (L=100), periodic, Moore-8 neighbourhood. Two strategies C/D. Snowdrift
payoffs (T>R>S>P): R=b−c/2, T=b, S=b−c, P=0; cost-to-benefit ratio r=c/(2b−c) ∈ (0,1). Payoffs
SUMMED over k neighbours (self excluded). **Update = STOCHASTIC replicator / pairwise imitation**:
focal i picks a random neighbour j, adopts j's strategy w.p. max(0,(P_j−P_i))/(k·Δ). Init ~50% C.
≥1000 generations; f_lat = time-avg C fraction over the last ~200 gens, averaged over ≥20 runs/r;
sweep r in ~0.05 steps. Well-mixed baseline = mean-field replicator (or the analytic line).

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Well-mixed reproduces the interior ESS f=1−r. | \|f_wm(r) − (1−r)\| ≤ 0.03 for r∈{0.2,0.4,0.6,0.8}; slope of f_wm vs r in [−1.1,−0.9]. |
| P2 | Spatial structure INHIBITS cooperation (opposite of spatial PD). | ∃ r*∈[0.3,0.7] with (1−r*) − f_lat(r*) ≥ 0.10, AND f_lat(r) < (1−r) for the majority of tested r∈(0.1,0.9). |
| P3 | High-r extinction on the lattice. | f_lat(r=0.8) ≤ 0.05 while f_wm(r=0.8) ≥ 0.15 (gap ≥ 0.10). |

**GATE (keep-with-gate, load-bearing):** the inhibition REQUIRES the stochastic replicator rule —
a **best-takes-over control** (Nowak-May deterministic imitation) must NOT show the same strong
inhibition. Report both; if best-takes-over also inhibits identically, the effect is mislabeled.
**Discipline:** L, neighbourhood, payoffs, update rule, r grid, runs FIXED + metrics locked; no
tuning. Falsified → MISS. **Distinctness:** nowak_may_pd raises cooperation via compact clusters
(positive assortment); snowdrift LOWERS it via filaments (negative assortment) — the SIGN of the
spatial effect is reversed, which a nowak_may_pd rerun (PD payoffs, best-takes-over) cannot show.
