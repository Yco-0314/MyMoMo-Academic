# Huth & Wissel fish schooling (1992) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Huth & Wissel 1992 (J Theor Biol 156:365), not tuned.
**Genuine-agent (disclosed): zonal self-propelled fish in 2D.** Verified; gate-checked.

**Model:** N zonal self-propelled agents in 2D with the standard repulsion / parallel-orientation / attraction
zones and bounded turning + noise. The locked contrast is the INTEGRATION RULE for combining neighbour
influences, with all zonal forces held identical:
  - AVERAGING rule: an agent averages the desired directions induced by ALL relevant neighbours.
  - DECISION rule: an agent picks ONE neighbour (e.g. the highest-priority / a randomly weighted single
    neighbour) and follows only that one.
Order parameters: school polarization p (mean heading alignment) and nearest-neighbour distance (NND) with its
coefficient of variation.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Averaging beats decision on polarization. | mean school polarization under the averaging rule exceeds that under the decision rule by ≥ 0.15 at matched parameters (p_avg − p_dec ≥ 0.15). |
| P2 | Averaging gives tighter cohesion. | the coefficient of variation of nearest-neighbour distance is smaller under averaging than under the decision rule (more tightly regulated spacing). |
| P3 | Both rules still school. | both rules produce a polarized school (p > 0.5) rather than disorder — the effect is a quantitative averaging ADVANTAGE, not averaging-vs-no-schooling. |

**Discipline:** N, zone radii, speed, turning-rate, noise, seeds, run length, and both integration rules FIXED;
metrics locked; no tuning. Falsified → MISS. gate_design_check: p and NND measured after the school
equilibrates, seed-averaged; P1 is the load-bearing averaging-advantage claim, P3 the fair-baseline check that
both rules school.
**Distinctness (keep):** the locked A/B is AVERAGING-many-neighbours vs DECIDING-on-one-neighbour as the
integration rule, both with the same zonal forces — a mechanism comparison boids (always averages;
locks alignment-ON vs OFF) and vicsek_flocking (noise transition) do not contain.
