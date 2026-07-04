# Burridge-Knopoff earthquake fault (1989) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Carlson & Langer 1989 (Phys Rev Lett 62:2632), after
Burridge & Knopoff 1967. Not tuned. **Genuine-agent (disclosed): a mechanical spring-block chain.**
Verified; gate-checked.

**Model:** 1D chain of N blocks (the agents). Each block carries continuous position and velocity STATE and
obeys Newton's law: it is pulled by a loader plate at constant slow rate, coupled to its two neighbours by
springs (stiffness ratio ℓ) and to the plate by a spring, and held by a velocity-WEAKENING friction law (static
threshold, force drops as the block slips faster). Integrate the equations of motion (inertia included). A
slip event = a burst where one or more blocks exceed the static threshold and slide; its moment = total slip
summed over participating blocks. Collect event moments after a transient.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Gutenberg-Richter power law for small events. | discrete/continuous-MLE slip-moment exponent over the small-event scaling region lies in [1.5, 2.5] (the GR b ≈ 1 region), i.e. a genuine power law, not a single characteristic scale. |
| P2 | Heavy-tailed moments. | the event-moment distribution spans ≥ 2 decades AND the max event moment ≥ 100× the median nonzero event — broad scale-free small events, NOT exponential. |
| P3 | Stiffness controls the scaling. | increasing the spring stiffness ratio ℓ shrinks the power-law range and sharpens the large-event peak: the mean event moment DECREASES as ℓ increases (stiffer coupling ⇒ smaller, more frequent events). |

**Discipline:** N, stiffness grid ℓ, friction-law parameters, loader rate, integrator + timestep, transient/
collection windows, seeds FIXED; metrics locked; no tuning. Falsified → MISS. gate_design_check: this is the
high-difficulty genuine-mechanical model — ALL three clauses are honest MISS-risk (the GR range and the
characteristic bump are parameter-sensitive); the integrator must be energy-stable and the CFL-like timestep
small enough that events are physical, not numerical.
**Distinctness (keep):** a genuine MECHANICAL agent model — each block integrates Newtonian equations with
inertia and a velocity-weakening friction nonlinearity — unlike olami_feder_christensen (a discrete CA
caricature of B-K with instantaneous threshold-redistribution and no inertia). Inertia + friction nonlinearity
drive the characteristic-earthquake bump absent from OFC.
