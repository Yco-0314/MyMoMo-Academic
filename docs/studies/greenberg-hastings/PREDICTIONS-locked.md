# Greenberg-Hastings excitable media (1978) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Greenberg & Hastings 1978 (SIAM J Appl Math 34:515),
not tuned. **CA (disclosed).** Verified; gate-checked.

**Model:** 3-state excitable cellular automaton on a 2D grid. Each cell is quiescent (0), excited (1), or
in one of `r` refractory states. Update rule: a quiescent cell becomes excited iff ≥1 excited von-Neumann
neighbour; an excited cell enters refractory; refractory cells count down deterministically back to
quiescent. Total cycle length T = 1 (excited) + r (refractory). Seeded with a broken wavefront (a
half-plane excitation with a cut) to nucleate a rotating spiral.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Rotating spiral with a fixed rotation period. | seeded from a broken wavefront the medium forms a persistent rotating spiral; the global activity (excited-cell count) is periodic with period equal to the cycle length T = 1+r, stable to ±1 step over ≥ 20 successive rotations. |
| P2 | Colliding wavefronts annihilate (no pass-through). | two excitation fronts launched head-on annihilate on collision — after they meet the excited-cell count in the collision region returns to 0 within one refractory period and NO transmitted front continues past the collision line. |
| P3 | Refractory-set critical size for sustained re-entry. | there is a critical linear domain size L_c: below L_c all activity dies within < 5 cycles, at/above L_c the spiral persists > 100 cycles; L_c is finite and increases monotonically with the refractory length r (larger r ⇒ larger L_c). |

**Discipline:** grid, neighbourhood, refractory length r, seeds, and the broken-wavefront IC FIXED; metrics
locked; no tuning. Falsified → MISS. gate_design_check: period measured as the return period of the global
excited count (robust); L_c graded qualitatively (dies-vs-persists) + monotone-in-r, not a strict linear fit.
**Distinctness (keep):** a 3-state excitable CA with annihilating wavefronts, a fixed spiral rotation period,
and a refractory-set re-entry size threshold — none of these exist in game_of_life (binary totalistic) or
forest_fire (transient burn, no rotating re-entry).
