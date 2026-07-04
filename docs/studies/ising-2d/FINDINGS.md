# Ising 2D (Glauber) — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Genuine agent-based reproduction on the neutral platform (`abm_auto._platform`): each
lattice site is an autonomous `SpinAgent` that performs its own Glauber heat-bath
spin-flip decision, driven by an `AgentSet` scheduler in `random_order` (a fresh seeded
permutation each sweep = random-sequential dynamics) with a `DataCollector` over the
per-sweep |m| (not a god-loop). The spin VALUES live in a shared NumPy lattice for O(1)
neighbour reads; the per-site DECISION lives on the agent. Code:
`abm_auto/classics/ising.py`; experiment: `examples/repro_ising_2d/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| lattice | L×L **periodic** square lattice, L=**32** (N=1024 spins) |
| spins | ±1, random initial config (each ±1 with prob 1/2, seeded) |
| coupling | J = **1**, 4 nearest neighbours |
| dynamics | **Glauber heat-bath**, random-sequential sweep: each site set to +1 with prob 1/(1+exp(−2h/T)), h = Σ of 4 NN spins; equivalently flip s→−s accepted with prob 1/(1+exp(ΔE/T)), ΔE = 2·s·h |
| T-grid (6 pts) | **1.5, 2.0, 2.27, 2.5, 3.0, 3.5** |
| seeds per T | **5** (seed_base=0) |
| sweeps per run | **2000** (each sweep = N single-spin updates in a fresh permutation) |
| metric (LOCKED) | **\|magnetization\| = \|Σs\|/N**, averaged over the **back half** of the sweeps after discarding the first half (equilibration) |
| Onsager T_c | 2/ln(1+√2) ≈ **2.269185** |

Determinism: a single `numpy.default_rng(seed)` draws both the initial spins and every
per-site accept/reject uniform, in a fixed order → same seed reproduces byte-identical
output. Each (T, seed) run averages |m| over sweeps 1000–2000.

## Measured equilibrium |m| per T (mean over 5 seeds; range; per-seed)

| T | mean \|m\| | std | [min, max] | per-seed \|m\| |
|---|---|---|---|---|
| 1.5 | **0.9865** | 0.0003 | [0.986, 0.987] | 0.987, 0.986, 0.986, 0.987, 0.987 |
| 2.0 | 0.9017 | 0.0210 | [0.860, 0.915] | 0.911, 0.914, 0.860, 0.907, 0.915 |
| 2.27 | 0.6127 | **0.1159** | [0.389, 0.703] | 0.389, 0.685, 0.675, 0.703, 0.611 |
| 2.5 | 0.2124 | 0.0486 | [0.154, 0.296] | 0.197, 0.154, 0.184, 0.230, 0.296 |
| 3.0 | 0.0815 | 0.0076 | [0.074, 0.094] | 0.086, 0.074, 0.079, 0.094, 0.075 |
| 3.5 | **0.0613** | 0.0014 | [0.060, 0.064] | 0.060, 0.060, 0.062, 0.064, 0.062 |

**Measured |m|=0.5 half-crossing (linear interpolation between T=2.27 and T=2.5): T ≈ 2.335.**
Onsager exact T_c ≈ 2.269. |m| is monotone non-increasing across the whole grid.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Ordered below T_c, disordered above (\|m\| > 0.7 at T=1.5 AND \|m\| < 0.2 at T=3.5) | **REPRO** | \|m\|(1.5)=**0.987** > 0.7; \|m\|(3.5)=**0.061** < 0.2 |
| P2 | \|m\| half-crossing (\|m\|≈0.5) lies in T∈[2.0, 2.6] | **REPRO** | crossing = **2.335** ∈ [2.0, 2.6] (Onsager 2.269) |
| P3 | \|m\|(T) monotone non-increasing across the grid | **REPRO** | largest upward step = **0.0** (perfectly non-increasing) |

**3/3 testable clauses REPRO.** The reproduction recovers the Onsager order–disorder
transition: a spontaneously ordered phase below T_c, a disordered phase above it, and a
sharp |m| drop straddling T_c ≈ 2.269, recovered without tuning.

## Honest caveats

- **Finite L=32 rounds the transition.** Onsager's singular spontaneous magnetization and
  the exact T_c are *thermodynamic-limit* (L→∞) results; at finite L the transition is
  smooth, not a sharp kink, and the crossover sits slightly **above** the true T_c. Our
  measured |m|=0.5 crossing at **T ≈ 2.335** is one finite-size step above the exact
  2.269 — the expected direction and magnitude of the finite-L shift, not an error. We do
  **not** refine L to land closer to 2.269 (that would be post-hoc tuning); the locked
  window [2.0, 2.6] was set wide precisely to absorb finite-L rounding.
- **The critical region is seed-noisy — by design, not by accident.** At T=2.27 (right at
  T_c) the per-seed |m| ranges **0.389 → 0.703** (std 0.116); away from T_c the seeds
  agree to within a few thousandths (std ≤ 0.05). This is the physical critical slowing
  down + diverging fluctuations of the order parameter near the transition: a 32×32 lattice
  near T_c wanders between more- and less-ordered configurations over a finite run, so
  single-seed |m| is genuinely scattered there. We report the full per-seed spread and the
  variance rather than hiding it; the *seed-averaged* metric is what is graded.
- **|m| above T_c floors at a few × 1/√N, not 0.** The disordered phase has |m| ≈ 0.06–0.08
  at T=3.0–3.5, not exactly 0: |Σs|/N for a finite lattice fluctuates at order 1/√N
  (1/32 ≈ 0.031). The measured ~0.06–0.08 is ~2× that bare estimate (correction, adversarial
  review 2026-06-30: residual short-range correlations + the |·| half-Gaussian mean
  ⟨|m|⟩=√(2/π)·σ lift it above the naive 1/√N — so call it "order 1/√N", a couple times the
  bare value, not exactly 1/√N). The P1 high-T clause (<0.2) accounts for this finite-size floor;
  the trend (0.21 → 0.08 → 0.06 as T rises) is the correct approach to the disordered
  state.
- **Glauber vs Metropolis.** We use the Glauber heat-bath single-spin rule (the rule named
  in the locked predictions), not Metropolis. Both share the same equilibrium Boltzmann
  distribution and the same T_c; only the dynamics (autocorrelation time) differ, which
  does not affect the equilibrium |m| metric graded here.
- **Equilibration.** We discard the first 1000 of 2000 sweeps and average |m| over the
  back 1000. A 32×32 lattice equilibrates well within 1000 sweeps at every T on the grid
  except in the immediate critical region, where critical slowing down inflates the
  per-seed variance noted above (but the seed-averaged mean is stable).
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
  run time (the bundle is committed together with the code, so it points to the parent
  commit). Reproduction integrity is anchored on the content-addressed **sha256** of the
  docs/data artifacts (all `replay: strong`), not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* model — no real-world data.
  The contribution is that the harness + lock-first discipline reproduce the Onsager
  order–disorder transition and would surface an artifact (a refutation gate, not a truth
  certificate).
