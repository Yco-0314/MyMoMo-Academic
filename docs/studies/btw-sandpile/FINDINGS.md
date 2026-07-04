# BTW Sandpile (SOC) — FINDINGS

**Run date:** 2026-06-30. **Verdict:** 3/3 locked clauses REPRO.
**Predictions were LOCKED before the run** (see `PREDICTIONS-locked.md`); L, the drive,
the toppling rule, the transient cutoff, the fit method, and `kmin` were all FIXED before
running and were **not** tuned to hit τ≈1.2.

## What this is — and what it is NOT (honesty, read first)

This is a **CELLULAR AUTOMATON / self-organized-criticality (SOC) model, NOT an
agent-stepping ABM.** There are no agents that perceive, decide, and act; there is no
scheduler over an agent roster and no per-agent step. The model is a deterministic
*toppling rule* applied to an L×L grid of integer heights until the grid is stable. We
disclose this in exactly the same way the Erdős–Rényi and Watts–Strogatz reproductions
disclose that they are network-*generation* models rather than agent-based simulations.
The lock-first + honest-verdict + L3-bundle discipline applies unchanged.

The reproduced result is a **physics/complexity** claim: Bak, Tang & Wiesenfeld (1987)
showed that this simple driven-dissipative rule *self-organizes* — with no parameter
tuning — to a critical state whose avalanche sizes follow a power law, the canonical
signature of SOC.

## Model (faithful to BTW 1987)

- L×L grid, **L = 50**, integer heights (grains per cell), starting empty.
- **Drive:** add one grain at a uniformly random cell.
- **Topple** (relaxation): while any cell has height ≥ 4, every unstable cell loses 4 and
  gives 1 grain to each of its 4 von-Neumann neighbours; grains pushed past the grid
  boundary are **lost** (open boundary / dissipation). Repeat until stable.
- **Avalanche size s** = total number of individual topplings triggered by that one added
  grain (s = 0 if it caused no toppling).
- The rule is *abelian*: the final configuration and the total toppling count are
  independent of toppling order, so a synchronous sweep gives the canonical avalanche size.
- **Deterministic** given the seed (a single `numpy.random.default_rng(seed)` draws every
  drop location). NumPy vectorizes the sweep; the result is the canonical CA outcome.

## Configuration (FIXED before the run)

| Knob | Value |
|---|---|
| Grid L | 50 |
| Topple threshold | 4 (von-Neumann, open boundary) |
| Transient discarded | 100,000 grains |
| Avalanches recorded | 200,000 |
| Seed | 0 |
| Fit method | **exact** discrete power-law MLE (zeta-likelihood; Clauset et al. 2009) |
| Fit cutoff `kmin` | 1 |

**Fit-method note (decided before the production run).** The locked metric is a discrete
power-law MLE for the tail exponent τ with a fixed `kmin = 1`. The *exact* discrete MLE
maximizes the zeta-distribution log-likelihood
`L(τ) = −n·ln ζ(τ, kmin) − τ·Σ ln sᵢ` (solved numerically). We deliberately do **not** use
the closed-form continuity-correction *approximation* `τ = 1 + n / Σ ln(sᵢ/(kmin−0.5))`
— that approximation is only accurate for `kmin ≳ 6` and is biased **low** by ~0.2–0.8 at
the small `kmin` locked here (verified against synthetic zipf samples in the tests). Zero-
size avalanches are excluded from the tail fit (they are not part of the power law).

## Results (seed 0, deterministic)

| Quantity | Value |
|---|---|
| Fitted tail exponent **τ** | **1.261** (stderr 0.0009; n_tail = 86,636) |
| Stationary mean height | **2.098** (final-state mean 2.106) |
| Avalanches recorded | 200,000 (113,364 of size 0 = 56.7%; 86,636 nonzero) |
| Nonzero sizes span | **3.997 decades** (1 … 9,939) |
| Max / median-nonzero | **414×** (max 9,939; median nonzero 24) |

The avalanche-size distribution is a clean power law over nearly four decades, with τ≈1.26
— consistent with the canonical 2D BTW value of ~1.2. (The literature reports a range of
τ values for the area/size exponent depending on the precise observable and finite-size
corrections; the locked window [0.9, 1.6] is comfortably satisfied.)

## Locked predictions — verdicts

| # | Prediction | Pass clause | Measured | Verdict |
|---|---|---|---|---|
| P1 | Power-law sizes, τ≈1.2 (2D) | τ ∈ [0.9, 1.6] | τ = 1.261 | **REPRO** |
| P2 | Heavy-tailed, not exponential | ≥2 decades AND max ≥ 100× median | 4.0 decades, 414× | **REPRO** |
| P3 | Self-organizes to a critical mean height | mean height ∈ [2.0, 2.2] | 2.098 | **REPRO** |

**3/3 REPRO.** The system self-organizes — without tuning — to a stationary critical state
(mean height ≈ 2.1) whose avalanche sizes are power-law distributed with τ≈1.26: the
defining SOC signature reported by Bak, Tang & Wiesenfeld (1987).

## Caveats / scope

- **Not an ABM.** Disclosed above; this is a CA/SOC reproduction, included for the
  power-law/criticality emergence, not agent decision-making.
- **Single seed for the headline run** (seed 0). The metrics are self-averaging over
  200,000 avalanches on a 50×50 grid; seed-to-seed variation in τ and mean height is small
  (tests confirm determinism per seed and that different seeds give different sequences).
  No seed was selected to hit a target — seed 0 was fixed before running.
- **Finite size.** L = 50 truncates the power law (the largest avalanches are cut off by
  the boundary); the ~4-decade span and τ≈1.26 are finite-size measurements, not the
  thermodynamic-limit exponent. This is expected and does not affect the locked clauses.
- **τ is an *area/size* exponent**, not the avalanche-*duration* or other SOC exponents;
  the locked claim is specifically about the number-of-topplings distribution.
- Faithful reproduction of a published *synthetic* model; **no real-world data**. The
  contribution is whether the harness + discipline reproduce the SOC power law and would
  catch an artifact (a non-power-law distribution, or a wrong critical mean height).

## Sources

- Bak, P., Tang, C. & Wiesenfeld, K. (1987). *Self-organized criticality: An explanation
  of the 1/f noise.* Phys. Rev. Lett. 59:381–384. doi:10.1103/PhysRevLett.59.381.
- Clauset, A., Shalizi, C.R. & Newman, M.E.J. (2009). *Power-law distributions in
  empirical data.* SIAM Review 51(4):661–703 (the discrete-MLE estimator used for τ).
