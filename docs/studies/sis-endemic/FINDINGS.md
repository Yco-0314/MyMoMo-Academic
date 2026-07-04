# SIS Endemic Threshold — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
person is an autonomous `PersonAgent` with a two-state (S/I) machine, applying the
mass-action infection rule and the memoryless recovery rule under an `AgentSet`
scheduler + `DataCollector` (not a god-loop). Code: `abm_auto/classics/sis.py`;
experiment: `examples/repro_sis_endemic/run.py`.

This is a **genuinely agent-based** model (agents carry state and step), per the
batch-4 design's honesty note (SIS and Voter are the genuine agent-stepping members of
the wave).

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| population | well-mixed (mass-action), **N = 10,000** |
| states | **S / I only** (no R — recovery returns straight to Susceptible; no immunity) |
| recovery prob/tick gamma | **0.1** |
| infection rule | each S -> I w.p. 1 - (1 - beta/N)^{I_count} (start-of-tick I_count) |
| recovery rule | each I -> S w.p. gamma |
| R0 control | beta varied at fixed gamma so **R0 = beta/gamma** |
| seed | **i0 = 10** infectives |
| run length | **500 ticks** (synchronous update) |
| prevalence window | mean I/N over the **last 50 ticks** |
| seeds per R0 | **20** (deterministic ensemble, seeds 0..19) |
| R0-grid | **0.8, 1.0, 1.5, 2.0, 3.0** |
| analytic anchor | endemic prevalence **i\* = 1 - 1/R0** (R0>1; 0 otherwise), at the LOCKED R0 |

Update is synchronous: the force of infection is frozen from the start-of-tick I_count,
every agent stages its next state, then all states commit at once -> order-independent ->
deterministic given the seed. I = 0 is absorbing (no reintroduction), so a seed that
stochastically dies out stays at prevalence 0 — reported honestly, not patched over.

## Measured endemic prevalence per R0 (mean over the last 50 ticks, over 20 seeds)

| R0 | mean prevalence | std | min | max | i\* = 1-1/R0 | \|dev\| | extinct (of 20) |
|---|---|---|---|---|---|---|---|
| 0.8 | **0.0000** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 20/20 |
| 1.0 | 0.0004 | 0.0013 | 0.0000 | 0.0057 | 0.0000 | 0.0004 | 18/20 |
| 1.5 | 0.3164 | 0.0073 | 0.3007 | 0.3333 | 0.3333 | 0.0169 | 0/20 |
| 2.0 | 0.4761 | 0.0029 | 0.4715 | 0.4816 | 0.5000 | 0.0239 | 0/20 |
| 3.0 | 0.6330 | 0.0027 | 0.6274 | 0.6391 | 0.6667 | 0.0337 | 0/20 |

Monotone non-decreasing across the R0-grid: **yes** (0.0000 <= 0.0004 <= 0.3164 <= 0.4761
<= 0.6330).

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Endemic threshold at R0=1 (prevalence < 0.02 at R0=0.8 AND > 0.30 at R0=2.0) | **REPRO** | prev(0.8)=0.0000 < 0.02; prev(2.0)=0.4761 > 0.30 |
| P2 | Endemic prevalence i\*=1-1/R0 within +/-0.05 at R0 in {1.5,2.0,3.0} | **REPRO** | devs: 0.0169, 0.0239, 0.0337 — all <= 0.05 (worst at R0=3.0) |
| P3 | Monotone in R0, ~0 below 1 (< 0.02 at R0=0.8) | **REPRO** | monotone = yes; prev(0.8)=0.0000 < 0.02 |

**3/3 testable clauses REPRO.** The reproduction recovers the SIS central result: a
sharp endemic threshold at R0=1 (prevalence pinned at 0 below, a sizeable endemic
plateau above) and an endemic prevalence that tracks i\* = 1 - 1/R0.

## Honest caveats

- **Systematic downward bias vs i\* (well within tolerance).** Measured prevalence sits
  slightly *below* the continuous mean-field i\* at every R0>1, and the gap *grows* with
  R0 (0.017 -> 0.024 -> 0.034). This is expected, not a bug: (i) the discrete-time
  synchronous map with gamma=0.1 and the 1-(1-beta/N)^I hazard departs mildly from the
  continuous-time mean field, and (ii) finite-N demographic stochasticity depresses the
  quasi-stationary mean below the deterministic fixed point. The agreement is still
  comfortably inside the locked +/-0.05 band. We did NOT tune gamma, N, the window, or
  the run length to shrink it.
- **Near-threshold stochastic die-out (R0~1) reported honestly.** At R0=0.8 every one
  of the 20 seeds went extinct (prevalence exactly 0). At R0=1.0 **18 of 20** seeds died
  out and the surviving 2 left only a tiny residue (mean 0.0004, max 0.0057): exactly
  the critical SIS regime, where a finite population started from 10 infectives almost
  always fades because the mean-field equilibrium itself is 0 at R0=1. The mean is a
  mix of (mostly) extinct and (rarely) lingering runs — the genuine behaviour of a
  stochastic SIS at criticality, not a measurement artifact, and the locked clauses
  only assert ~0 below threshold (which holds).
- **Absorbing extinction.** With no reintroduction, I=0 is absorbing. For R0>=1.5 no seed
  went extinct within 500 ticks, so the endemic plateau is measured cleanly; the late
  window is firmly in steady state (std <= 0.007 across seeds).
- **Scope.** Faithful reproduction of a published synthetic model (well-mixed SIS); no
  real-world data. The contribution is whether the harness + lock-first discipline
  reproduce the endemic threshold and the i\* = 1 - 1/R0 law, and would catch an
  artifact — not a claim about any real epidemic.
