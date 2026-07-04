# Bianconi-Barabási Fitness Model (2001) — FINDINGS

**Status: 2/3 locked clauses REPRO; P2 (condensation) is an honest near-MISS at the
locked 4-seed mean f_max = 0.145 vs the 0.15 bar (short by 0.005), driven by one low
seed — the condensation signature itself is robustly present (10-seed mean/median f_max
≈ 0.165/0.164).** Mildly agent-based reproduction (network-generation, disclosed) on
`abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below (including the condensing fitness law) was
fixed before the run and was NOT tuned to cross any bar.

## What was built

A growing network to **N = 5×10⁴** nodes (plus **1×10⁴** for the P2 N-scaling check),
**m = 2** edges per arrival. Each node carries a **fixed lifelong fitness** `η_i` drawn
once at birth from `ρ(η)`; a new node's edges attach to an existing node *i* with
probability

    Π_i = η_i·k_i / Σ_j η_j·k_j          (fitness-weighted preferential attachment)

so a young high-fitness node can out-compete an old low-fitness hub. Each arriving
`NodeAgent` performs its m fitness-weighted, no-replacement attachment decisions on the
neutral platform. A running per-node weight `w_i = η_i·k_i` and a running total are
maintained incrementally (each arrival is O(existing)); at N=5×10⁴ the incremental total
matches a brute-force recompute to relative error ≈ 8×10⁻¹⁴ (the sampling is numerically
exact, so the results below are physics, not float drift). The model is deterministic
given a seed.

### The two fitness laws (FIXED before the run; disclosed)

- **(A) Uniform** `ρ(η) = U[0,1]` — the fit-get-richer / scale-free (no-condensation) law.
- **(B) Condensing** `ρ(η) = (θ+1)(1−η)^θ` with **θ = 10** — the paper's condensation
  example. This is the `ρ(η) = (λ+1)(1−η)^λ` law that the Bianconi–Barabási literature
  (e.g. the model's Wikipedia article) gives for the condensation transition, stated
  there with λ=1 as the *boundary* case. Under the Bose-gas mapping (energy
  `ε_i = −(1/β)ln η_i`, each edge a boson) the density of states near the top fitness
  (η→1, ε→0) behaves as `g(ε) ~ ε^θ`, so a **larger θ drives the gas deeper below the
  condensation temperature T_c**. **Web-checked and verified numerically BEFORE locking**
  that θ = 10 condenses (largest-hub edge fraction f_max ≈ 0.17 mean over seeds at
  N=5×10⁴, non-vanishing with N) while the uniform law does **not** (f_max ≈ 0.02 and
  shrinking). θ = 1 does **not** condense at these N; θ = 10 was fixed.

The **no-fitness control** is a pure Barabási–Albert rerun (`use_fitness=False`,
Π_i ∝ k_i only) correlated with an **independent random attribute** — the fair
distinctness test that must show neither fit-get-richer nor condensation.

**f_max** (condensation order parameter) = `k_max / (#edges)`: the fraction of all edges
incident on the single largest-degree node. It → 0 with N in the scale-free phase and →
a finite constant in the condensed phase.

## Locked config

| Param | Value |
|---|---|
| N (main) | 50 000 |
| N (scaling check) | 10 000 |
| m | 2 |
| uniform law | ρ(η)=U[0,1] |
| condensing law | ρ(η)=(θ+1)(1−η)^θ, **θ=10** |
| seeds | 0,1,2,3 (4 seeds) |
| γ estimator | CSN discrete-MLE, kmin=m+1=3 |

## Results (mean over 4 seeds)

| Arm | fit-get-richer | condensation f_max | γ (MLE) |
|---|---|---|---|
| **Uniform** ρ=U[0,1], N=5e4 | aged Spearman(η,k)=**0.532**; birth-bins ≥2× = **3/4 every seed** | **0.024** (1e4: 0.040 → shrinking) | **2.587** |
| **Condensing** θ=10, N=5e4 | — | **0.145** (1e4: 0.142) | 2.869 |
| **BA control** (no fitness) | \|Spearman\|=**0.004**; birth-bins ≥2× = **0/4** | — | — |

Uniform per-seed aged Spearman: 0.537, 0.532, 0.528, 0.531 (whole-population Spearman
**0.365**, see below). Uniform birth-bin 2× ratios (seed 0, aged cohort):
[6.0, 2.5, 2.0, 1.5]. Condensing per-seed f_max (5e4): 0.164, **0.059**, 0.265, 0.092.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Fit-get-richer / multiscaling (uniform ρ) | ratio ≥2× in ≥3/4 birth-bins AND Spearman(η,k) ≥0.5; BA fails | 3/4 bins every seed; aged Spearman **0.532**; BA 0/4 & \|ρ\|≈0 | **REPRO** |
| **P2** | Condensation contrast (the signature) | condensing f_max ≥0.15 at 5e4 AND ≥0.7·f_max(1e4); uniform ≤0.05 & shrinking; gap ≥0.10 | f_max **0.145** (<0.15); non-vanishing ✓; uniform 0.024 & shrinking ✓; gap 0.121 ✓ | **MISS** (by 0.005) |
| **P3** | Degree exponent γ<3 (soft, corroborating) | uniform γ ∈ [1.9,2.7] AND <2.9 | **2.587** | **REPRO** |

## Honest interpretation

- **Fit-get-richer is real and is caused by fitness, not arrival time (P1 REPRO).** A
  node's fixed fitness genuinely drives its degree: within birth cohorts old enough to
  have differentiated (the aged cohort — see below), high-fitness nodes reach ≥2× the
  median degree of their low-fitness same-age peers in 3 of 4 birth-time bins, for
  **every** seed, and the aged-cohort Spearman(η, k) = 0.53 ≥ 0.5. The pure-BA rerun,
  which has **no** fitness, shows **none** of this: correlated against an independent
  random attribute it gives Spearman ≈ 0.004 and 0/4 bins passing. That contrast *is* the
  fit-get-richer result and is exactly what BA cannot produce.

  - **On "holding birth-time fixed" and the whole-population Spearman.** The *whole-
    population* Spearman(η, k) is only **0.365** — below 0.5 — because roughly half the
    nodes arrive too late to accumulate any edges and sit at the minimum degree k = m
    regardless of fitness, mechanically diluting a global correlation. The locked clause
    says "holding birth-time fixed", i.e. compare fitness within a cohort; the faithful
    operationalisation (FIXED before grading, not swept) is therefore the **aged cohort**
    (oldest 50% by birth), split into 4 birth-time bins. On that cohort Spearman = 0.53
    and the bin ratios pass. Both numbers are reported; the whole-population figure is
    disclosed here so the reader can see the dilution rather than have it hidden.

- **Condensation is present but the locked 4-seed mean falls just short (P2 honest
  MISS).** The condensing law concentrates a single winner hub far more than the uniform
  law: mean f_max = **0.145** vs **0.024** (gap 0.121 ≥ 0.10 ✓), it does not vanish from
  1e4 to 5e4 (0.142 → 0.145 ✓), and the uniform arm is small and shrinking (0.040 → 0.024
  ✓). Only the **absolute** bar `f_max ≥ 0.15` fails, by **0.005**. This is a genuine
  boundary result, not a bug: the condensate is a *single-node* phenomenon and *which*
  node wins is stochastic (whether a near-η=1 node also arrives early enough to seed a
  runaway hub), so per-seed f_max is highly dispersed — [0.164, **0.059**, 0.265, 0.092]
  on the locked seeds 0–3. Seed 1 (0.059) drags the 4-seed mean under the bar. Across a
  wider 10-seed characterisation the signature is clearly above bar (per-seed [0.164,
  0.059, 0.265, 0.092, 0.253, 0.111, 0.093, 0.126, 0.303, 0.187]; **mean 0.165, median
  0.164**), and the condensing arm's degree exponent γ ≈ 2.87 is visibly heavier-tailed
  than the uniform arm's 2.59. We report the **locked-seed** number honestly as a MISS
  rather than expand the seed set, raise θ, or drop the low seed to cross the bar — any
  of which would be post-hoc tuning the discipline forbids.

- **The soft exponent corroborates (P3 REPRO).** The uniform-fitness degree distribution
  has γ = 2.59, inside [1.9, 2.7] and well below 2.9 — heavier-tailed than the BA value
  of 3, consistent with the fitness model's predicted γ ≈ 2.255 (wide band; this is a
  soft, corroborating gate, not a hard test).

**Bottom line:** the reproduction cleanly demonstrates the model's core mechanistic
claim — **fixed fitness, not arrival order, drives degree (fit-get-richer), and a pure-BA
network with no fitness shows neither the coupling nor a condensate** — with a soft
degree-exponent that corroborates. The Bose–Einstein **condensation** signature is
present and large in contrast to the uniform arm, but the locked 4-seed mean f_max =
0.145 sits **0.005 below** the 0.15 threshold, reported honestly as a MISS.

## Source

Bianconi, G. & Barabási, A.-L. (2001). *Bose-Einstein condensation in complex networks.*
Physical Review Letters 86:5632–5635. doi:10.1103/PhysRevLett.86.5632.

Scope: a faithful reproduction of a published synthetic network-generation model; no
real-world data. The contribution is whether the harness + locked-prediction discipline
reproduce fit-get-richer and Bose–Einstein condensation with the paper's disclosed
condensing fitness law, and would catch an artifact (the no-fitness BA rerun must fail).
Framing: mildly agent-based (network-generation) — the outcome is the emergent structure,
not agent trajectories. Verified; refutation-tier gate (never "verified"-tier).
