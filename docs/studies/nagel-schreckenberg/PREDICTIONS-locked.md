# Nagel–Schreckenberg Traffic — PREDICTIONS (locked)

**Locked 2026-06-30, BEFORE running.** Claim is Nagel & Schreckenberg (1992), not tuned.
Genuine agent-based (car agents).

**Model:** 1D ring of L=1000 cells, cars with integer velocity 0..vmax=5, slowdown prob
p=0.3. Each tick (parallel over cars): (1) v←min(v+1,vmax); (2) v←min(v, gap); (3) w.p. p
v←max(v−1,0); (4) move x←x+v. Outcome = flow = ρ·⟨v⟩ and mean velocity vs density ρ; jam =
fraction of cars with v=0. Sweep ρ. Measure after transient. Mean over ≥10 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Fundamental diagram has an interior flow maximum. | argmax flow(ρ) is at an interior ρ (≈0.1), not at the smallest/largest ρ |
| P2 | Free-flow at low density, congested at high. | mean v ≥ 3 at ρ=0.05 AND mean v ≤ 2 at ρ=0.5 |
| P3 | Spontaneous jams emerge (p>0). | stopped-car fraction (v=0) ≫ 0 (≥ 0.1) at a high density (ρ=0.5), no obstacle present |

**Discipline:** L, vmax, p, ρ-grid, seeds FIXED + metrics locked before run; no tuning.
Falsified → MISS.
