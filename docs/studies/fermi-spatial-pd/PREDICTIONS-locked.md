# Fermi-Rule Spatial Prisoner's Dilemma (Szabó-Tőke 1998) — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Szabó & Tőke 1998 (Phys. Rev. E 58:69), not tuned.
Genuine agent-based (stochastic pairwise-comparison update). Verified; gate-checked.

**Model:** square lattice, von Neumann (z=4) neighbourhood WITH self-interaction (the 1998 primary
model). Weak PD: R=1, P=S=0, T=b (b>1). Random-sequential FERMI update: focal x picks ONE random
neighbour y and adopts y's strategy w.p. W = 1/(1+exp(−(E_y−E_x)/K)), K = selection noise. L≥400
(≥500 near criticality), periodic BC, random 50/50 init. Stationary cooperator density c averaged over
≥20 MC sweeps after transient.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Cooperators survive above b=1 (stochastic + spatial reciprocity). | at K=0.1: c(b=1.4) ∈ [0.35, 0.65] (paper 0.515) AND c(b=1.9) = 0 (all-D absorbing above b_c2≈1.85). A deterministic best-takes-over rerun cannot produce this smooth intermediate density. |
| P2 | The C→extinction transition is CONTINUOUS (not a discrete step). | at K=0.5, near b_c2≈1.66: c(b) is monotone + smooth with no single-Δb=0.02 jump > 0.20 in the coexistence interior; the fitted exponent c ∝ (b_c2−b)^β gives β ∈ [0.45, 0.75] (directed-percolation β≈0.58; paper 0.59). |
| P3 | Noise NON-MONOTONICITY: an optimal intermediate K. | **on the no-self-interaction von Neumann spec** (where the effect is clean): the survival threshold b_cr(K) is peaked — b_cr(K≈0.32) − b_cr(K≈0.05) ≥ 0.10, peak K ∈ [0.2, 0.5], b_cr → ~1 as K→0.05 and K→1.5. *(Do NOT lock this on a Moore neighbourhood — monotone-decreasing there. If only the self-interaction model is used, weaken to: at fixed b=1.7, c(K=0.5)>0 while c is lower/0 at much-smaller and much-larger K.)* |

**Discipline:** lattice/neighbourhood, payoffs, K grid, L, sweeps FIXED + metrics locked; no tuning.
Falsified → MISS. **Distinctness (keep):** nowak_may_pd is the SAME spatial PD but with DETERMINISTIC
best-takes-over updating — the Fermi stochastic pairwise-comparison rule, the K-noise dependence, the
CONTINUOUS (DP-class) transition, and the optimal-intermediate-K effect are all properties the
deterministic model does not have.
