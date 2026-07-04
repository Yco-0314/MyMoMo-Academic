# Buhl et al. marching locusts (2006) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Buhl et al. 2006 (Science 312:1402), not tuned.
**Genuine-agent (disclosed): self-propelled particles in a 1D ring arena.** Verified; gate-checked.

**Model:** N self-propelled agents on a periodic 1D ring (the Czirók 1D alignment variant of the locust
experiment). Each agent has position and a ±1 heading; each step it aligns its heading toward the average
heading of neighbours within a range, plus noise, and moves at fixed speed. Control parameter = DENSITY
(agents per ring length). Order parameter = mean normalized alignment |⟨v⟩| (0 = disordered, 1 = all marching
one way). Sweep density; at each density run long and record alignment and the sign of the net direction over
time.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Density-driven order/disorder crossover. | mean |⟨v⟩| is low (< 0.3) at low density and high (> 0.7) at high density — a clear collective-marching onset as density rises. |
| P2 | Intermittent direction reversals near threshold. | at an intermediate density the sign of the net marching direction flips at least once over a long run (switching rate > 0), whereas at high density it never flips (rate ≈ 0) — the empirical signature of near-critical locust bands. |
| P3 | Monotone ordering in density. | mean |⟨v⟩| is non-decreasing in density across the swept grid (tolerance 0.05 on each step). |

**Discipline:** N, ring length grid (⇒ density), interaction range, noise, speed, seeds, run length FIXED;
metrics locked; no tuning. Falsified → MISS. gate_design_check: P2 (intermittent switching) is the honest
MISS-risk clause — it requires the run to be long enough to observe reversals at the near-critical density but
not so noisy that the high-density case also flips; P1/P3 are the robust density-crossover signatures.
**Distinctness (keep):** the 1D ring-arena density-driven transition with spontaneous global-direction
reversals — vicsek_flocking locks a NOISE-driven transition at fixed density on a 2D torus, not a DENSITY
threshold nor 1D intermittent switching.
