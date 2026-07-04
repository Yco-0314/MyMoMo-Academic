# Turing Diffusion-Driven Instability (Gierer-Meinhardt 1972 / Turing 1952) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Grid-PDE reproduction on NumPy (explicit forward
Euler, 5-point periodic Laplacian). **Framing (disclosed honestly): this is a two-species
reaction-diffusion PARTIAL-DIFFERENTIAL-EQUATION integrated on a grid — a CELLULAR /
grid-PDE model, NOT an agent-stepping ABM** (no agents that perceive/decide/act, no
scheduler over a roster, no per-agent step). Disclosed exactly as the `gray_scott` /
`game_of_life` reproductions disclose they are cellular / grid-PDE models. Predictions were
locked BEFORE running (`PREDICTIONS-locked.md`); the config below was fixed before the run
and was NOT tuned to make any clause pass.

## What was built

The Gierer-Meinhardt activator-inhibitor kinetics on a 128x128 **periodic** grid:

    da/dt = rho*(a^2/h - a) + Du*lap(a)          (activator: short-range, self-enhancing)
    dh/dt = rho*(a^2   - h) + Dv*lap(h)          (inhibitor: long-range, produced by a)

integrated with explicit forward Euler and the 5-point `np.roll` periodic Laplacian. The
kinetics have a single non-trivial homogeneous steady state **a* = h* = 1**. The initial
condition is that steady state plus small seeded Gaussian noise (amplitude 0.01) — the
standard "small random perturbation of the uniform state" — and the fields are floored at a
tiny positive value each step to keep the `a^2/h` kinetics well defined. The run is
deterministic given the seed (the noise draw is the only randomness).

**The diffusion-driven instability (Turing's central result), derived not fitted.**
Linearising about (1, 1) gives the reaction Jacobian J = rho*[[1, -1], [2, -1]]. Without
diffusion the homogeneous state does not grow (trace J = 0, det J = rho^2 > 0: a neutral
centre; the saturating `a^2/h` nonlinearity then holds it exactly flat, which the **control**
confirms). With **unequal** diffusion, the growth rate of a spatial mode q is the larger
eigenvalue of J - q^2*diag(Du, Dv); it turns positive over a finite band once the diffusion
ratio d = Dv/Du exceeds the critical ratio **d_c = 3 + 2*sqrt(2) ~= 5.828** (the classic
Gierer-Meinhardt value, computed in closed form from the Jacobian). The fastest-growing
angular wavenumber **q*** is `argmax_q` of that growth rate, scanned from the dispersion
relation. We compare the emergent dominant wavenumber against this q* — never fitted.

**Two arms, differing ONLY by Dv (a fair control):**
- **CONTROL** — d = Dv/Du = **1** (equal diffusion): no unstable band, stays homogeneous.
- **TURING** — d = **1.5*d_c ~= 8.74** (well inside the regime): a stationary periodic pattern.

The three locked metrics: the spatial **coefficient of variation** CoV = std(a)/mean(a)
(P1), the **dominant wavenumber** from the radially-averaged 2-D power-spectrum peak,
returned as an angular wavenumber k = 2*pi*m/(N*dx) to match q* (P2), and the **amplitude
series** std(a) over the run, whose last 20% must be flat (P3).

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| grid | 128x128 (periodic), dx = 1.0 |
| rho (reaction rate) | 1.0 |
| Du (activator diffusion) | 0.5 |
| Dv control / Turing | 0.5 (d=1) / 4.3713 (d = 1.5*d_c) |
| critical ratio d_c | 3 + 2*sqrt(2) = 5.8284 |
| dt (explicit Euler) | 0.005 (< diffusion limit dx^2/(4*max(Du,Dv)) ~= 0.057) |
| IC noise about (1,1) | 0.01 |
| seeds | 0, 1, 2 (3 seeds) |
| steps | 30 000 |

## Results (per seed; raw)

| Arm | final CoV (per seed) | mean CoV | k_meas (per seed) |
|---|---|---|---|
| **CONTROL (d=1)** | 0.00016, 0.00027, 0.00026 | **0.00023** | — |
| **TURING (d=1.5 d_c)** | 1.0682, 1.0488, 1.0621 | **1.0597** | 0.8836, 0.8836, 0.8345 |

Linear-theory **q* = 0.8289** (rad per grid unit); unstable band **(0.5603, 1.2072)**.
Measured **mean k = 0.8672**, mean relative error to q* = **0.046**. The Turing-arm
amplitude climbs from the ~0.01 seeded noise, saturates near std(a) ~= 0.67 by the mid-run,
and is flat thereafter: worst last-20% change **0.0005 per 1000 steps**.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Diffusion-driven instability gate | control CoV < 0.05 **and** Turing CoV >> 0.05 | control **0.0002**, Turing **1.06** | **REPRO** |
| **P2** | Wavelength matches linear dispersion | k_meas in band **and** \|k-q*\|/q* <= 0.35 | mean rel-err **0.046**, all in-band | **REPRO** |
| **P3** | Stationary, non-oscillatory pattern | last-20% amplitude change < 5% / 1000 steps | worst **0.05%** | **REPRO** |

## Honest interpretation

- **The instability is genuinely diffusion-DRIVEN.** With equal diffusion (d = 1) the exact
  same kinetics, IC and seeds leave the field homogeneous to five decimal places
  (CoV ~= 2e-4): the reaction alone cannot pattern. Only when the inhibitor diffuses fast
  enough relative to the activator (d = 1.5*d_c) does a finite-amplitude periodic pattern
  emerge (CoV ~= 1.06 — a >4000x jump). That contrast, holding everything but Dv fixed, *is*
  Turing's morphogenesis result and isolates differential diffusion as its cause.

- **The emergent wavelength matches the linear theory closely.** The dominant wavenumber the
  simulation selects (mean k ~= 0.867 rad/unit, i.e. mode ~17-18 on the 128 grid) sits inside
  the linear-theory unstable band (0.560, 1.207) and within **4.6%** of the fastest-growing
  mode q* = 0.829 derived from the Gierer-Meinhardt Jacobian — comfortably under the locked
  35% tolerance. The wavelength is *predicted*, not fitted: q* comes from the dispersion
  relation of the linearised kinetics, computed before the pattern is seen. (The small
  positive bias of k_meas above q* is expected: nonlinear mode competition on a finite
  periodic grid quantises the pattern to an integer mode near, and slightly above, the
  linear optimum.)

- **The pattern is stationary, not a travelling/oscillating wave.** Over the last 20% of the
  run the amplitude changes by at most 0.05% per 1000 steps for every seed — the pattern has
  locked into a fixed Turing configuration, exactly the "stationary, non-oscillatory"
  distinctness the lock demanded (this is a Turing instability, not a Hopf/wave instability).

- **Framing caveat (kept honest).** This is a grid PDE, not an agent model. The scientific
  content — stable-without-diffusion, patterned-with-it, at the dispersion-relation
  wavelength — is faithful to Turing 1952 / Gierer-Meinhardt 1972, and the harness would
  catch an artifact (a d = 1 run that spuriously patterned, or a k_meas outside the band,
  would fail P1 / P2). The trace-0 marginality of the homogeneous state at q = 0 (a known
  knife-edge of the pure GM form) is handled by the saturating nonlinearity and does not
  produce spurious growth: the control stays flat.

**Bottom line:** the reproduction cleanly demonstrates Turing's diffusion-driven instability
end to end — homogeneous without differential diffusion, a finite-amplitude **stationary**
periodic pattern with it, at the wavelength the linear **dispersion relation predicts** —
and all three locked clauses REPRO with wide margins.

## Source

Turing, A. M. (1952). *The chemical basis of morphogenesis.* Philosophical Transactions of
the Royal Society of London B 237(641):37-72. doi:10.1098/rstb.1952.0012. Activator-inhibitor
kinetics: Gierer, A. & Meinhardt, H. (1972). *A theory of biological pattern formation.*
Kybernetik 12(1):30-39. doi:10.1007/BF00289234.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce Turing's
diffusion-driven instability, match the dispersion-relation wavelength, and would catch an
artifact.
