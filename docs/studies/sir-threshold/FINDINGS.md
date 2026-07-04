# SIR Epidemic Threshold — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`):
each person is an autonomous `PersonAgent(Agent)` carrying an S/I/R state, driven by an
`AgentSet` scheduler + `DataCollector` (the S/I/R count series) — not a god-loop. Code:
`abm_auto/classics/sir.py`; experiment: `examples/repro_sir_threshold/run.py`.

## Model (faithful, well-mixed / mass-action SIR)

N agents in states S/I/R. Each tick is a **synchronous** update:

1. Read `I_count` at the **start** of the tick.
2. Each S becomes I with prob `1 − (1 − β/N)^{I_count}` (the discrete force of
   infection: the hazard of meeting at least one of the `I_count` infectives, each
   transmitting with per-contact prob β/N; for small βI/N this is ≈ βI/N — the textbook
   mass-action term).
3. Each I recovers (I → R) with prob γ. R is absorbing.
4. Both transitions are decided from the **start-of-tick** state and committed at the
   **end** of the tick (a newly-infected S does not also recover the same tick; a
   freshly-recovered I does not infect after recovering). Synchronous ⇒ scheduler-order
   independent ⇒ deterministic given the seed.

Run until I = 0. Outcome = **final attack rate = 1 − S_final/N** (the LOCKED metric).
R0 = β/γ; β is set as `β = R0·γ` to hit each target R0.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| N | **10,000** |
| γ (recovery prob/tick) | **0.1** |
| seed infecteds i0 | **10** |
| β rule | **β = R0·γ** (vary β at fixed γ) |
| R0 grid | **0.8, 1.0, 1.5, 2.0, 3.0** |
| seeds per R0 | **20** (seed_base 0 → seeds 0..19) |
| take-off cutoff | attack rate **≥ 0.05** |
| metric | **final attack rate = 1 − S_final/N** |

## Measured attack rate per R0 (mean over 20 seeds; range; take-off split)

| R0 | β | mean attack | [min, max] | var | take-off | mean \| take-off |
|---|---|---|---|---|---|---|
| 0.8 | 0.080 | **0.0061** | [0.0013, 0.0212] | 3.1e-05 | 0/20 | — |
| 1.0 | 0.100 | 0.0238 | [0.0015, 0.1098] | 7.5e-04 | 2/20 | 0.0969 |
| 1.5 | 0.150 | 0.5751 | [0.5138, 0.6231] | 5.4e-04 | 20/20 | 0.5751 |
| 2.0 | 0.200 | **0.7952** | [0.7773, 0.8068] | 5.8e-05 | 20/20 | 0.7952 |
| 3.0 | 0.300 | 0.9413 | [0.9340, 0.9492] | 1.8e-05 | 20/20 | 0.9413 |

## The threshold at R0 = 1

The attack rate is **negligible below R0 = 1** (0.0061 at R0 = 0.8 — just the original
10 seeds plus a handful of secondary cases that die out) and **substantial above it**
(0.5751 at R0 = 1.5, 0.7952 at R0 = 2.0, 0.9413 at R0 = 3.0). This is the classic
Kermack–McKendrick epidemic threshold: a large outbreak occurs iff R0 > 1. The
transition is sharp around R0 = 1, exactly where the deterministic theory places it.

## Final-size relation at R0 = 2.0 (analytic, NOT fit)

Solving the locked final-size relation `ln(S0/S∞) = R0(1 − S∞/N)` with S0 ≈ N — i.e.
the attack rate `a` solves `a = 1 − exp(−R0·a)` — gives, for R0 = 2.0, **a\* = 0.7968**.
The measured mean attack rate at R0 = 2.0 is **0.7952**, a **relative offset of 0.21%**,
far inside the ±10% band. The analytic value is computed from the LOCKED R0, not fit to
the run.

## Verdicts (locked metric = final attack rate)

| # | Prediction | Result | Number |
|---|---|---|---|
| P1 | threshold at R0=1 (attack<0.05 at R0=0.8 AND >0.30 at R0=2.0) | **REPRO** | 0.0061 < 0.05 ✓; 0.7952 > 0.30 ✓ |
| P2 | R0=2.0 within ±10% of analytic final-size relation | **REPRO** | offset 0.0021 ≤ 0.10 ✓ |
| P3 | monotone non-decreasing in R0; <0.05 at R0=0.8 | **REPRO** | [0.0061, 0.0238, 0.5751, 0.7952, 0.9413] non-decreasing ✓ |

**3 / 3 locked clauses REPRO.**

## Caveats (honest)

- **Near-threshold bimodality.** Around R0 = 1 the stochastic outcome is bimodal: most
  seeds fizzle (small outbreak, only the seeds + a few secondaries), a minority take off
  (large outbreak). At R0 = 1.0 we measured **2/20 seeds taking off** (attack ≥ 0.05;
  mean 0.097 among those) and 18 fizzling — which is exactly the classic
  small-outbreak / large-outbreak split, not a numerical artifact. The **mean** attack
  rate at R0 = 1.0 (0.0238) therefore mixes the two modes and is the wrong thing to
  compare against the deterministic final-size curve; the per-seed range and the
  take-off count are reported so the split is visible.
- **Final-size relation is conditional on take-off.** The deterministic relation
  `ln(S0/S∞)=R0(1−S∞/N)` describes the **large** outbreak — i.e. the trajectory that
  took off. At R0 ≥ 1.5 every seed (20/20) took off, so the unconditional mean and the
  conditional-on-take-off mean coincide and the comparison at the locked R0 = 2.0 is
  unambiguous. At R0 = 1.5 a slight downward pull of the mean below the analytic value
  is expected when some seeds fizzle; here all 20 took off, so the small gap
  (0.5751 measured vs 0.5828 analytic) is finite-N / finite-i0 stochasticity, not a
  fizzle artifact.
- **Scope.** This is a faithful reproduction of a published synthetic model (well-mixed
  mass-action SIR); no real-world data. The contribution is whether the harness +
  discipline reproduce the epidemic-threshold + final-size result and would catch an
  artifact — they do (P1–P3 pass on the locked metric against the analytic anchor).
