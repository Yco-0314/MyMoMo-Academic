# Keller-Segel Chemotaxis / Aggregation (1970) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Keller & Segel 1970 (J Theor Biol 26:399), not tuned.
**CA / grid PDE (disclosed).** Verified; gate-checked.

**Model:** two fields on a 2D periodic grid — cell density ρ and chemoattractant c. dρ/dt = D_ρ·∇²ρ −
χ·∇·(ρ·∇c); dc/dt = D_c·∇²c + a·ρ − b·c. Cells diffuse AND climb the gradient of the attractant they
secrete. A dimensionless sensitivity S combines χ, mean density, and the diffusion/decay rates. Small
random IC around a uniform mean ρ₀. ≥5 seeds.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | AGGREGATION above threshold. | at strongly super-critical S ≥ 3: max(ρ)/ρ₀ ≥ 3.0 AND final std(ρ)/mean(ρ) ≥ 5× its initial value (spontaneous clumping into dense peaks). |
| P2 | UNIFORM below threshold (a real instability threshold). | at sub-critical S ≤ 0.5: max(ρ)/ρ₀ ≤ 1.5 AND std(ρ)/mean(ρ) does not grow (final ≤ initial noise) — diffusion keeps cells uniform. |
| P3 | Long-wavelength dispersion sign check. | the leading low-q Fourier mode of ρ GROWS early (positive slope) when S ≥ 3 and does NOT grow when S ≤ 0.5 (the instability is long-wavelength, as the linear analysis predicts). |

**Discipline:** D_ρ, D_c, χ/S grid, a, b, ρ₀, seeds FIXED + metrics locked; no tuning. Falsified → MISS.
**Distinctness (keep):** chemotactic self-aggregation (cells climbing a self-secreted gradient → collapse
above a sensitivity threshold) is unique to this model; schelling relocates by neighbour-preference (no
diffusing signal field), and no built model has a chemoattractant PDE or a chemotactic-collapse threshold.
