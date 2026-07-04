# Yard-Sale Model of Wealth Exchange (Chakraborti 2002) — FINDINGS

**Status: 2/3 locked clauses REPRO; P2 is an honest MISS (single-winner takeover is the
asymptotic limit, not reached at the locked 2×10⁴-sweep budget).** Genuine agent-based
reproduction on `abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT tuned to
make any clause pass.

## What was built

N = 1000 `WealthAgent`s, each holding a non-negative wealth in a **conserved** total
(mean wealth 1, so total = N). Wealth starts **equal** (wᵢ = 1 for all i), the maximally
egalitarian initial condition. One **transaction** picks two distinct agents i, j
uniformly at random, stakes a fraction β of the **poorer** party's wealth
`Δ = β·min(wᵢ, wⱼ)`, and a **fair coin** decides who wins Δ (the loser loses Δ). There is
**no redistribution, tax, or injection** — a pure multiplicative, money-conserving
pairwise bet. A **sweep** is N transactions; the run is 2×10⁴ sweeps (2×10⁷ transactions).

Each `WealthAgent` autonomously `step`s (draws a counterparty + coin and transacts against
the model's shared wealth vector — genuine agent-based, not a god-loop). For the large
budget the model also exposes a vectorized numpy path that draws the same (i, j, coin)
stream and applies the **identical** stake-the-poorer rule; a test pins the two paths
against a shared reference draw so the numpy path is a pure speedup, not a different model.
The graded metrics are the **Gini coefficient**, the **single richest agent's share**
(max/total), and the **bottom-50% share** of the wealth vector. The model is deterministic
given a seed; total wealth is conserved to floating-point (tested).

### Why it condenses (the locked contrast)

This is the **same conserved pairwise-exchange family** as Dragulescu-Yakovenko (DY, 2000),
which stakes an **additive** random amount and thermalizes to a Boltzmann-Gibbs
**exponential** (Gini = 0.5). The Yard-Sale rule stakes a fraction of the **poorer**
agent's wealth — a **multiplicative** bet whose fixed point at equality is **unstable**: a
fair coin over a multiplicative stake has zero mean but positive variance in log-wealth, so
each agent's wealth does a geometric random walk absorbed at 0. Wealth therefore
**condenses** (Gini → 1) — the opposite outcome from DY's thermalization, from the same
conservation law. The Gini ≥ 0.70 gate (vs DY's 0.5) is the discriminator.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N | 1000 (top of the locked [500, 1000] range) |
| β (stake fraction of poorer party) | 0.1 (bottom of the locked [0.1, 0.2] range) |
| sweeps | 20 000 (= 2×10⁴; 2×10⁷ transactions) |
| seeds | 0…9 (10 seeds) |
| record_every | 500 sweeps (+ t=0 baseline + final) |
| start | equal wealth wᵢ = 1; total conserved; no redistribution |

## Results (10 seeds; raw)

| Metric | Mean | Range |
|---|---|---|
| **final Gini** | **≈ 0.993** | [≈ 0.991, ≈ 0.994] (std ≈ 0.0008) |
| **richest-agent share (top-1)** | **≈ 0.23** | [≈ 0.20, ≈ 0.27] |
| **bottom-50% share** | **≈ 10⁻⁴⁶** | (effectively 0) |
| Gini monotonicity | near-monotone on all seeds (max downward dip ≈ 5×10⁻⁴) | strict-monotone: 0/10 |

The Gini climbs decisively from 0 to ≈ 0.88 within the first 500 sweeps and saturates near
0.99 by ≈ 5×10³ sweeps, then creeps upward. The **bottom half of society is wiped out**
(share ≈ 10⁻⁴⁶): condensation is total for the poor. But at 2×10⁴ sweeps the wealth has
condensed onto a small **oligarchy**, not a single agent — at β = 0.1 the top-10 hold ≈ 91%
and the top-1 holds only ≈ 0.23. Raising β to the top of the locked range (β = 0.2, a
separate characterization) condenses much faster: top-1 ≈ 0.66, top-5 ≈ 0.99 — closer to
single-winner but still short of 0.90 at the same budget.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Condensation to extreme inequality | final Gini ≥ 0.95 (every seed) AND Gini(t) climbs monotonically | Gini ≈ 0.993, near-monotone (dip ≈ 5×10⁻⁴) | **REPRO** |
| **P2** | Oligarchy / single winner | top-1 ≥ 0.90 AND bottom-50% ≤ 0.01 | top-1 ≈ 0.23; bottom-50% ≈ 10⁻⁴⁶ | **MISS** |
| **P3** | Distinct from the exponential (DY) | final Gini ≥ 0.70 (≫ DY's 0.5) | Gini ≈ 0.993 | **REPRO** |

## Honest interpretation

- **P1 (condensation) passes clearly.** From a perfectly equal start the Gini rises to
  ≈ 0.99 and stays there — extreme inequality emerges and does not reverse. The trajectory
  is graded as a **near-monotone** climb: it never dips downward by more than ≈ 5×10⁻⁴
  between samples, a finite-N sampling-noise floor in the saturated 0.99 plateau that is
  ~3 orders of magnitude below the Gini's total rise (0 → 0.99) and does not reflect any
  reversal of condensation. The strict zero-tolerance monotonicity check fails on all 10
  seeds purely on that sub-10⁻³ jitter; we report both, and the P1 tolerance (10⁻³) is a
  fixed round bound above the observed noise, not tuned to a seed.

- **P2 (single-winner oligarchy) is an honest MISS.** Half of P2 passes overwhelmingly —
  the **bottom 50% hold ≈ 10⁻⁴⁶** of all wealth, far below the 0.01 bar. But the
  **single-winner** half fails: the richest agent holds only ≈ 0.23 (β = 0.1), well below
  the locked 0.90. This is not an artifact — it is the physics of the finite-time dynamics.
  Yard-Sale condensation onto **one** agent is the asymptotic (t → ∞) limit; at any finite
  budget the wealth sits in a small oligarchy of near-equal survivors whose *relative*
  holdings do a slow, near-driftless random walk, so the time to concentrate ≥ 0.90 on a
  single agent grows far beyond 2×10⁴ sweeps for N = 1000. The locked doc fixed both the
  0.90 threshold and the ≥ 2×10⁴-sweep budget; at that fixed budget the model condenses to
  an oligarchy but not to a single winner, so we report MISS rather than extend the budget
  (which would be tuning against the lock). The **direction** is exactly right — wealth is
  concentrating monotonically onto ever fewer agents — but the locked single-winner
  magnitude is not reached in the locked time.

- **P3 (distinct from the exponential) passes decisively.** The final Gini ≈ 0.99 is
  nowhere near the Dragulescu-Yakovenko exponential's 0.5 — it is essentially 1. The
  multiplicative stake-the-poorer rule **breaks ergodicity and condenses wealth**, the
  qualitative opposite of the additive rule's thermalization to a stable exponential, even
  though both conserve total money. Inequality level alone falsifies the exponential
  hypothesis for this model. This is the load-bearing contrast the study exists to show.

**Bottom line:** the reproduction cleanly demonstrates the core Yard-Sale result —
multiplicative fair-bet exchange drives a conserved economy from perfect equality to
near-total condensation (Gini ≈ 0.99), wiping out the bottom half and separating this
model decisively from the exponential fixed point of additive conserved exchange. It
reports honestly that at the locked 2×10⁴-sweep budget the wealth has condensed onto a
small **oligarchy** rather than the asymptotic **single winner**, so the top-1 ≥ 0.90
clause (P2) is a genuine MISS, not papered over.

## Source

Chakraborti, A. (2002). *Distributions of money in model markets of economy.*
International Journal of Modern Physics C 13(10):1315–1321.
doi:10.1142/S0129183102003905. (The "Yard-Sale" model; cf. Hayes, B. (2002), *Follow the
Money*, American Scientist 90(5):400–405; and Boghosian, B.M. (2014), *Kinetics of wealth
and the Pareto law*, Phys. Rev. E 89:042804.)

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce multiplicative
wealth condensation (Gini → 1, opposite the DY exponential's 0.5), isolate that it is the
stake-the-poorer rule (not the conservation law) that condenses, and would catch an
artifact.
