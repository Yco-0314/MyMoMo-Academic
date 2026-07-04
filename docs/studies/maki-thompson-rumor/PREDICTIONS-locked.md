# Maki-Thompson Rumor Model — PREDICTIONS (locked)

**Locked 2026-07-01, BEFORE running.** Claim is Maki & Thompson 1973 (variant of Daley-Kendall
1965), not tuned. **Well-mixed stochastic compartment process (hybrid: agent states, directed
pairwise contacts, CTMC) — disclosed, not autonomous per-agent scheduling.** Verified.

**Model:** N agents, 3 states — Ignorant (I, never heard), Spreader (S), Stifler (R, heard, no
longer spreading). Directed-contact rules: (1) S→I makes the I a Spreader; (2) S→S converts the
INITIATING spreader to Stifler; (3) S→R converts the initiating S to Stifler. I.e. a spreader
"ages out" (becomes a stifler) the moment it directs a contact at anyone already informed. Seed: 1
spreader, N−1 ignorants. Single contact rate (symmetric ratio ρ = λ/α = 1 for the canonical run).
Gillespie/CTMC to absorption (no spreaders left). N=1e4 (sweep {1e3,1e4,1e5}); ≥50 runs,
conditioned on outbreak.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Canonical never-hear constant. | symmetric single-rate (ρ=1): mean final ignorant fraction `i_∞` ∈ [0.195, 0.211] (root of θ=e^(−2(1−θ)) = 0.2032), final stifler fraction ∈ [0.789, 0.805], \|mean i_∞ − 0.2032\| < 0.008 over ≥50 runs at N=1e4. |
| P2 | Rate-INDEPENDENCE (the discriminating signature vs SIR). | scaling the absolute contact rate by {0.5, 2, 4} leaves i_∞ unchanged: max pairwise \|i_∞(rate_i) − i_∞(rate_j)\| < 0.01 — whereas an SIR final size visibly increases with rate (MT's plateau is rate-invariant because the rate only rescales time). |
| P3 | Peak spreader fraction + finite-size convergence. | mean peak spreader fraction ∈ [0.29, 0.32] (target 1−ln2 = 0.3069); and \|mean i_∞(N) − 0.2032\| decreases monotonically across N ∈ {1e3,1e4,1e5}, N=1e5 within 0.004 of 0.2032. |

**Discipline:** N, seed, rate grid, ρ, run count FIXED + metrics locked; no tuning. Falsified → MISS.
The 0.203 constant is canonical ONLY for ρ=1 (general fixed point θ=e^(−(1+ρ)(1−θ))); we lock the
symmetric model and treat ρ as a controlled knob. **Distinctness (keep-with-gate):** nearest built
is sir-threshold — MT's final never-hear fraction is a rate-INVARIANT constant (0.203), while SIR
final size strictly increases with R0; the "ages out on contact with the informed" rule (not
spontaneous recovery) fixes the constant, which a sir-threshold rerun cannot reproduce.
