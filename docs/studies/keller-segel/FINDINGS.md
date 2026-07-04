# Keller-Segel Chemotaxis / Slime-Mold Aggregation (1970) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Grid-PDE reproduction (CA / grid PDE — disclosed;
there are no stepping agents). Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and only the
dimensionless sensitivity `S` was dialled (super-critical vs sub-critical). Nothing was
tuned to make a clause pass.

## What was built

Two fields on a 96x96 **periodic** grid — the cell density `rho` and the chemoattractant
concentration `c` — integrated by explicit forward Euler:

    d rho/dt = D_rho * lap(rho)  -  chi * div(rho * grad(c))
    d c  /dt = D_c   * lap(c)    +  a * rho  -  b * c

Cells **diffuse** (`D_rho`) and **climb the gradient of the attractant they themselves
secrete** (the `- chi*div(rho*grad c)` chemotaxis flux — advection of cells UP the
`c`-gradient). The attractant diffuses (`D_c`), is produced by cells at rate `a*rho`, and
decays at `b*c`. This positive feedback — cells make the signal, the signal pulls cells
together, denser clumps make more signal — is the Keller-Segel instability.

**The bifurcation knob** is the dimensionless sensitivity

    S = chi * a * rho0 / (D_rho * b)

(chemotactic pull per unit cell-diffusion, using the quasi-steady attractant response
`c' = (a/b)*rho'`). `S` is the ONLY thing dialled: for a target `S` we back out
`chi = S*D_rho*b/(a*rho0)` with `a, b, D_rho, D_c, rho0` all fixed. The two arms are a
strongly super-critical `S = 5.0` and a sub-critical `S = 0.3` — the **same equations**,
only `S` changed.

**Critical numerics (the delicate part the lock flagged).** The chemotaxis advection
`chi*div(rho*grad c)` is discretised **conservatively with an upwind flux at the cell
faces**: the drift velocity on a face is `chi*(d c across that face)`, and the advected
density is taken from the **upwind** cell (the one the flux flows out of). The divergence of
these face fluxes updates `rho`. Upwinding keeps `rho >= 0` and conserves total mass to
machine precision (each face flux leaves one cell and enters its neighbour), so a growing
`max(rho)` is genuine mass **piling up**, not a numerical oscillation. Diffusion is the
standard 5-point periodic Laplacian. The time step `dt = 5e-4` was chosen small enough that
the advective CFL number stays **below 1 throughout** the aggregation — we record the peak
CFL and the mass drift as numerical-health diagnostics precisely because **a numerical
blow-up is NOT physical aggregation**. (At the larger `dt = 2e-3`, `n = 96`, the
super-critical run diverges to NaN once mass collapses toward a single cell — a real
reminder that the KS finite-time singularity must be integrated carefully; that regime is
excluded.)

The model is deterministic given a seed (the only randomness is the seeded initial density
noise `rho = rho0*(1 + eps*white)`, `eps = 0.01`, around the uniform lawn, with `c` at its
uniform equilibrium `a*rho0/b`).

## Locked config (FIXED before the run; only S dialled)

| Param | Value |
|---|---|
| grid | 96x96 (periodic) |
| domain side | 20.0 (dx ~ 0.208) |
| D_rho, D_c | 1.0, 1.0 |
| a, b (production, decay) | 1.0, 1.0 |
| rho0 (uniform mean density) | 1.0 |
| dt | 5e-4 |
| initial noise eps | 0.01 |
| steps / record every | 30000 / 3000 |
| seeds | 0,1,2,3,4 (5 seeds) |
| super-critical S / sub-critical S | 5.0 / 0.3 |

## Results (mean over 5 seeds; raw)

| Arm | mean peak rho/rho0 | peak range | mean CV growth (final std/mean over initial) | low-q mode grows early |
|---|---|---|---|---|
| **SUPER-CRITICAL (S=5.0)** | **869** | [768, ~960] | **~ 2400x** | **5 / 5 seeds** (mean +1.07) |
| **SUB-CRITICAL (S=0.3)** | **1.00** | [1.00, 1.00] | **0.0x** (CV *shrinks*) | **0 / 5 seeds** (mean -0.16) |

Numerical health (super-critical): peak advective CFL ~ **0.83 (< 1, stable)**, total-mass
relative drift ~ **3e-15** (mass conserved) — the aggregation is genuine piling-up, not a
blow-up. The super-critical density stays a flat lawn through the linear-growth phase (peak
~ 1 for thousands of steps) and then rapidly collapses into a small number of tall
aggregation peaks; the sub-critical density noise simply diffuses away toward a perfectly
uniform field.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Aggregation above threshold (S>=3) | max(rho)/rho0 >= 3.0 **AND** final std/mean >= 5x initial | peak ~ **869x**, CV growth ~ **2400x** | **REPRO** |
| **P2** | Uniform below threshold (S<=0.5) | max(rho)/rho0 <= 1.5 **AND** std/mean does not grow | peak = **1.00x**, CV growth = **0.0x** | **REPRO** |
| **P3** | Long-wavelength dispersion sign check | low-q mode grows early at S>=3, NOT at S<=0.5 | grows **5/5** (super) vs **0/5** (sub) | **REPRO** |

## Honest interpretation

- **The chemotactic-collapse instability threshold is real and sharp.** The *only*
  difference between the two arms is the dimensionless sensitivity `S`. Above threshold
  (`S = 5.0`) an initially flat lawn of cells spontaneously collapses into dense peaks — the
  tallest peak reaches ~**870x the mean density** and the coefficient of variation grows by
  ~**2400x**. Below threshold (`S = 0.3`) the identical equations keep the lawn **perfectly
  uniform**: the peak ratio never leaves 1.00 and the density noise *decays*. That opposite
  response to a single dimensionless knob **is** the Keller-Segel result: aggregation is an
  instability with a genuine threshold, not a gradual response.

- **The instability is long-wavelength, as the linear analysis predicts (P3).** The leading
  (longest-wavelength, `|k| = 1`) Fourier mode of the density grows early in **every**
  super-critical seed (mean early growth +1.07) and grows in **no** sub-critical seed (mean
  -0.16 — it decays). The sign of the low-q dispersion flips exactly across the threshold,
  which is the signature Keller & Segel derived from linearising the uniform state.

- **The aggregation is physical, not numerical.** Under the conservative upwind flux, total
  mass is conserved to ~1e-15 and the advective CFL peaks at ~0.83 (< 1) — so the tall peaks
  are mass genuinely transported up the self-generated gradient, not an explicit-Euler
  oscillation exploding. We deliberately integrate below the CFL limit and record it; the
  larger-`dt` NaN divergence is excluded as the artifact it is.

**Bottom line:** the reproduction cleanly demonstrates the Keller-Segel mechanism — cells
climbing a self-secreted chemoattractant gradient undergo a **threshold** collapse from a
uniform lawn into dense aggregation centres (P1), stay uniform below that threshold (P2),
and do so via a **long-wavelength** instability (P3) — all three locked clauses REPRO, with
mass conservation and a sub-unity CFL confirming the collapse is physical.

## Source

Keller, E. F. & Segel, L. A. (1970). *Initiation of slime mold aggregation viewed as an
instability.* Journal of Theoretical Biology 26(3):399-415.
doi:10.1016/0022-5193(70)90092-5.

Scope: a faithful reproduction of a published synthetic model; no real-world data. Framing:
a two-field chemotaxis PDE integrated on a periodic grid (a cellular / grid-PDE model, not
an agent-stepping ABM) — disclosed exactly as the game-of-life / Gray-Scott reproductions
disclose they are cellular automata. The contribution is whether the harness +
locked-prediction discipline reproduce the chemotactic-collapse threshold and would catch a
numerical artifact.
