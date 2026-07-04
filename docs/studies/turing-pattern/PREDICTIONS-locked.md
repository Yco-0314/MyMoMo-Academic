# Turing Diffusion-Driven Instability (Gierer-Meinhardt) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Turing 1952 (Phil Trans R Soc B 237:37) via the
Gierer-Meinhardt activator-inhibitor kinetics, not tuned. **CA / grid PDE (disclosed).** Verified;
gate-checked.

**Model:** activator-inhibitor reaction-diffusion on a grid. Gierer-Meinhardt: da/dt = ρ(a²/h − a) +
Du·∇²a; dh/dt = ρ(a² − h) + Dv·∇²h (activator short-range self-enhancing, inhibitor long-range). The
homogeneous steady state is STABLE without diffusion; adding diffusion with Dv/Du above the critical
ratio d_c makes it UNSTABLE → stationary periodic pattern. Integrate to steady state; small random IC.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Diffusion-driven instability gate. | with d=Dv/Du = 1 (or diffusion off): final spatial coefficient of variation < 0.05 (stays homogeneous); with d ≥ 1.5·d_c (well inside the Turing regime): a finite-amplitude periodic pattern forms (CoV ≫ 0.05). |
| P2 | Wavelength matches the linear dispersion relation. | the measured dominant wavenumber k_meas lies in the unstable band (k₁² < k² < k₂²) AND \|k_meas − k*\|/k* ≤ 0.35 (k* = fastest-growing mode from linear analysis). |
| P3 | Stationary, non-oscillatory pattern (Turing, not a wave). | over the last ~20% of the run the global pattern amplitude is flat (relative change < 5% per 10³ steps); the spatial pattern is fixed (not travelling/oscillating). |

**Discipline:** kinetics, ρ, Du, Dv grid, integrator FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** the diffusion-DRIVEN instability (stable without diffusion, patterned with it,
inhibitor faster than activator) + the dispersion-relation wavelength is unique to reaction-diffusion; no
built model exhibits a Turing instability.
