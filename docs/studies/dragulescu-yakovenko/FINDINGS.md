# Dragulescu-Yakovenko Statistical Mechanics of Money (2000) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Genuine agent-based reproduction on
`abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT
tuned. NO saving propensity (lambda = 0) was added — doing so would turn the
distribution into a peaked Gamma and would fail P1 by design.

## What was built

5000 `MoneyAgent`s, each holding a non-negative money balance, in a
`MoneyExchangeModel` that owns the conserved money vector (a numpy array, for
speed). The total money `M = sum_i m_i` is conserved for all time. The dynamics
are the **conserved kinetic exchange** of Dragulescu & Yakovenko:

- Repeatedly draw a random ordered pair `(i, j)`, `i != j`.
- Pool their money `s = m_i + m_j`, draw `eps ~ U[0, 1)`.
- Set `m_i = eps*s`, `m_j = (1 - eps)*s` — the **full-repartition (no-saving)**
  rule: the whole pooled amount is randomly reassigned between the pair, with no
  saving propensity held back (lambda = 0).
- A hard **no-debt boundary** rejects any transaction driving a balance below 0.
  (With `eps in [0, 1)` and `s >= 0` this is never actually violated by the
  full-repartition rule; the guard is retained as a faithful boundary.)

The start is a **delta** (every agent begins with exactly `<m> = M/N = 100`;
initial Gini = 0, CV = 0). One **sweep** = N pairwise exchanges. The per-agent
`MoneyAgent` balances are kept in sync with the money vector so the roster is a
faithful view of the same conserved state. The model is deterministic given a
seed (a numpy `default_rng(seed)` drives the exchange).

The stationary money distribution is expected to relax to the **Boltzmann-Gibbs
exponential** `P(m) ~ exp(-m/T)` with money-temperature `T = <m>` — the
maximum-entropy distribution on `m >= 0` at fixed mean, the direct money analogue
of the equilibrium energy distribution of an ideal gas. The exponential has Gini
exactly 1/2 and coefficient of variation exactly 1.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N (agents) | 5000 |
| <m> = T = M/N | 100.0 |
| exchange rule | full-repartition (no saving), random pair, no-debt boundary |
| saving propensity lambda | 0 (none) |
| initial condition | delta (all agents = M/N) |
| seeds | 0..19 (20 seeds) |
| sweeps / burn-in | 5000 / discard first 50% |
| stationary sampling | pool the money vector every 50 post-burn-in sweeps |

Pooled seed+time stationary sample: **5,000,000** balances.

## Results (20 seeds; stationary state)

| Quantity | Measured | Target / meaning |
|---|---|---|
| seed-averaged **Gini** | **0.49994** (std 1.2e-4, range [0.4998, 0.5002]) | 0.50 (exponential fixed point) |
| seed-averaged **CV** = std/mean | **0.99983** (std 4.2e-4) | 1.0 (exponential) |
| log-linear fit **R^2** (ln P vs m on [0.2<m>, 3<m>]) | **0.99998** | >= 0.95 |
| fitted **temperature T** (1/slope) | **100.06** | <m> = 100 (within 0.06%) |
| **mode** of P(m) | **7.5** (7.5% of <m>, lowest bin) | in lowest ~10% bin; NOT interior |
| exponential **AIC** vs power-law AIC | **41,204,032 < 41,422,856** (delta = -218,825) | exp AIC < power-law AIC |
| best-fit power-law alpha (rejected) | 0.5 (pinned at the boundary — no power-law structure) | — |
| **max \|dM\|/M** over all t | **4.7e-16** | < 1e-9 (machine precision) |
| **min money** ever | **4.8e-7 >= 0** | >= 0 (no-debt holds) |

The histogram of P(m) is monotonically decreasing from the lowest bin — density
0.0093 at m ~ 7.5, falling smoothly (0.0080, 0.0069, 0.0059, 0.0051, 0.0044 at
m ~ 22.5 ... 82.5) — the exponential decay, with the peak at m -> 0.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | P(m) is exponential (Boltzmann-Gibbs), not peaked/power-law | loglin R^2 >= 0.95, slope ~ 1/<m>, mode in lowest bin, exp AIC < power-law AIC, NOT interior-peaked | R^2 = 0.99998, T = 100.06, mode = 7.5, exp AIC wins by 2.2e5 | **REPRO** |
| **P2** | Inequality at the exponential fixed point | Gini = 0.50 +- 0.03 AND CV = 1.0 +- 0.1 | Gini = 0.49994, CV = 0.99983 | **REPRO** |
| **P3** | Money conserved; T = mean | \|dM\|/M < 1e-9, min m >= 0, fitted T within 10% of <m> | dM/M = 4.7e-16, min m >= 0, T off by 0.06% | **REPRO** |

## Honest interpretation

- **The universal exponential emerges cleanly and is not an artifact.** From a
  perfectly equal delta start (Gini 0), conservative random exchange drives the
  money distribution to the Boltzmann-Gibbs exponential: the log-linear fit is
  essentially perfect (R^2 = 0.99998) over the locked bulk window, the recovered
  money-temperature (T = 100.06) matches <m> to better than 0.1%, and the mode
  sits in the lowest bin — a monotone-decaying density, not an interior peak.
  This is entropy maximization at fixed total money, exactly the paper's result.

- **Inequality is pinned to the thermal fixed point.** The seed-averaged Gini is
  0.49994 and the CV is 0.99983 — the exact analytic values (Gini = 1/2, CV = 1)
  of the exponential — and both are astonishingly tight across 20 seeds
  (Gini std = 1.2e-4). Inequality here is not a free parameter of the model; it
  is fixed by statistical mechanics.

- **Conservation is exact to machine precision.** Total money drifts by at most
  4.7e-16 (relative) over 5000 sweeps x 20 seeds, and no balance ever goes
  negative — the no-debt boundary and the pooling arithmetic are respected
  exactly. The fitted temperature equalling the mean is the internal
  consistency check the paper's kinetic theory predicts.

- **The gate would catch a saving-propensity artifact.** The one thing that
  would break DY is adding a saving propensity lambda > 0, which produces a
  *peaked* Gamma distribution (interior mode, Gini < 1/2) — the
  Chakraborti-Chakrabarti signature. We deliberately did NOT add it, and the P1
  gate is built to fail on it: the tests confirm that a shape-3 Gamma (mean 100)
  yields log-linear R^2 ~ 0.91 (< 0.95) and a mode ~ 67 (an interior peak
  > 0.3<m>), so either sub-clause alone flags it. The exponential we obtained
  triggers none of those failure modes.

- **Distinctness held.** Unlike Sugarscape (spatial harvesting, non-conserved
  sugar, a landscape-set Gini with no thermal signature) or Zero-Intelligence
  trading (allocative efficiency, no wealth accumulation), here money is strictly
  conserved and the emergent inequality is fixed by statistical mechanics to the
  universal exponential (Gini = 1/2). That thermal/entropy signature is unique to
  this model.

**Bottom line:** the reproduction demonstrates the Dragulescu-Yakovenko result in
full — conserved random money exchange from equality produces the Boltzmann-Gibbs
exponential money distribution with Gini exactly 1/2 and CV exactly 1, money
conserved to machine precision — and the discipline would have caught a
saving-propensity (peaked-Gamma) artifact had one been present.

## Source

Dragulescu, A. & Yakovenko, V.M. (2000). *Statistical mechanics of money.*
European Physical Journal B 17:723-729. doi:10.1007/s100510070114.

Scope: a faithful reproduction of a published synthetic model; no real-world
data. The contribution is whether the harness + locked-prediction discipline
reproduce the universal exponential (Boltzmann-Gibbs) money distribution with
Gini = 1/2, and would catch a saving-propensity (peaked-Gamma) artifact.
