# Bass 1969 Diffusion — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
consumer is an autonomous `AdopterAgent` applying the Bass adoption hazard under an
`AgentSet` scheduler + `DataCollector` (not a god-loop). Code:
`abm_auto/classics/bass_diffusion.py`; experiment: `examples/repro_bass_diffusion/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| N (agents) | **10,000** (all non-adopters at t=0) |
| p (coefficient of innovation) | **0.03** (meta-analytic) |
| q (coefficient of imitation) | **0.38** (meta-analytic) |
| seeds | **20** (seed_base 0..19) |
| stop | run until cumulative adoption **>= 0.99** |
| hazard | non-adopter adopts each tick with prob **clamp(p + q*F, 0, 1)** |
| update | **synchronous**: F frozen at start-of-tick; all non-adopters decide against the same F; adoptions committed at tick end |

**Synchronous-update note.** Per tick, the adopter fraction `F` is computed ONCE from
the start-of-tick state, then every non-adopter decides against that frozen `F`
(decisions within a tick do not see each other's new adoptions). This is the discrete
agent-level analogue of Bass' continuous hazard `f(t)/(1-F(t)) = p + q*F(t)`. Update is
order-independent -> deterministic given the seed.

## Analytic anchor (computed from the LOCKED p,q — NOT fit to the run)

t* = ln(q/p)/(p+q) = ln(0.38/0.03)/(0.41) = **6.1926** (CONTINUOUS time).

## Measured (seed-mean over 20 seeds)

| quantity | value |
|---|---|
| final cumulative fraction | **0.9927** |
| measured peak tick (argmax of seed-mean per-tick rate curve) | **8** |
| mean per-seed peak tick | **7.65** (per-seed peaks: eight 7s, eleven 8s, one 9; min 7, max 9) |
| S-curve | monotone=True, interior inflection at tick 7 |
| peak offset vs continuous t* (mean curve) | **+29.2%** |
| peak offset vs continuous t* (per-seed mean) | **+23.5%** |

Seed-mean per-tick new-adoption fraction (q>0): rises 0.030 -> 0.041 -> 0.053 -> 0.068 ->
0.082 -> 0.098 -> **0.108 (t=7) -> 0.111 (t=8, peak) -> 0.105** -> 0.090 -> 0.071 -> ... — a
clean interior bell.

**q=0 control (pure innovation):** rate argmax = **tick 1** (the first real tick; index 0
after dropping the t=0 baseline), monotonically decreasing thereafter (no interior peak),
final fraction 0.9902. The expected control rate is `p*(1-p)^k`, strictly decaying — the
realized seed-mean matches (0.0301, 0.0298, 0.0281, 0.0272, 0.0265, ...).

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Cumulative adoption is sigmoid and reaches near-full adoption (>= 0.98, monotone, interior inflection) | **REPRO** | final = **0.9927** >= 0.98; monotone; interior inflection at tick 7 |
| P2 | Measured peak tick within +-15% of continuous t* = ln(q/p)/(p+q) | **MISS** | measured peak tick **8** vs t* **6.19**: offset **+29.2%** (> +-15%) |
| P3 | q>p => interior bell peak; q=0 => rate monotonically decreasing (no interior peak) | **REPRO** | q>p peak at tick 8 (interior); q=0 argmax = first tick, no interior inflection |

**2/3 testable clauses REPRO; P2 is an honest MISS** (NOT tuned to pass).

## P2 MISS — the discrete-vs-continuous subtlety (the headline finding)

P2 fails because the measured peak tick (8) lags the **continuous** analytic
t* = 6.19 by +29%, outside the +-15% tolerance. This is **not finite-N noise and not a
bug** — it is the well-understood **forward-difference (Euler, dt=1) lag** of the discrete
Bass map relative to the continuous ODE:

- The discrete recursion is `F_{t+1} = F_t + (1-F_t)(p + q*F_t)`, a forward-Euler step
  with unit step size on dynamics whose characteristic time `1/(p+q) ~ 2.4` ticks is only
  ~2x the step — so the discretization error is non-negligible and biases the peak LATER.
- **Verified directly:** the *deterministic* mean-field discrete map (N->inf, no
  stochasticity) peaks at **tick 8**, identical to the stochastic agent runs; a fine-dt
  numerical integration of the continuous ODE peaks at **6.193**, matching the analytic
  t*. So the entire +29% gap is the dt=1 discretization, reproduced exactly by the agent
  model — the agents faithfully realize the discrete dynamics.
- The agent model is therefore a faithful *discrete-time* Bass model. The MISS is against
  a *continuous-time* anchor, and is reported honestly rather than dissolved by (a)
  shrinking dt / sub-stepping, (b) re-indexing the peak, or (c) widening the tolerance —
  any of which would be post-hoc tuning. The locked clause used the continuous t* with a
  fixed +-15% window; the discrete peak does not fit it, so P2 is MISS.

## Honest caveats

- **Peak is broad/flat-topped.** Ticks 7 (0.1084) and 8 (0.1106) differ by <2%, so the
  argmax is a near-tie between 7 and 8; the per-seed mean (7.65) sits between them. Even
  charitably reading the peak as 7 the offset is +13% (would pass), but the seed-mean
  argmax is unambiguously 8 (+29%) and the per-seed mean is +23.5% — both > 15%. We report
  the seed-mean argmax (8) as the primary measured peak; we do **not** cherry-pick tick 7.
- **t\* computed from the locked p,q, never fit.** ln(q/p)/(p+q) uses the pre-registered
  coefficients only.
- **Determinism.** Each seed's run is byte-reproducible (one seeded RNG chain on the
  model); curves of unequal length are right-padded (cumulative with the plateau value,
  rate with 0) before averaging.
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed together with the code, so it points to the parent
  commit). Reproduction integrity is anchored on the content-addressed **sha256** of the
  docs/data artifacts (all `replay: strong`), not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* model — no real-world data.
  The contribution is that the harness + lock-first discipline reproduce the Bass S-curve
  and bell-shaped adoption rate, and would surface an artifact: here it surfaced a genuine
  modelling subtlety (discrete vs continuous peak timing) as a clean, defensible MISS
  rather than laundering it into a pass.

## Citation

Bass, F.M. (1969). A New Product Growth for Model Consumer Durables.
*Management Science* 15(5):215-227. doi:10.1287/mnsc.15.5.215.
