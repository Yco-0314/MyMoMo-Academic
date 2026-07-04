# Bouchaud-Mézard wealth condensation — review

**tier: minimal** (all-REPRO 3/3, all bands hit with room; no MISS). Genuine agent-based (mean-field).

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (Gini 0.66/0.50/0.37/0.27, slope −1.89, Hill 1.78) matches bundle/results.
- fair-control: **pass** — the μ-sweep varies only J/σ² (the redistribution knob); Gini monotonicity across it is the graded contrast.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; the noise-normalization convention (physics ⟨dη²⟩=2σ²·dt) was fixed + documented BEFORE grading so μ=1+J/σ² holds; L3 gate ok.
- mechanism-aliveness: **pass** — multiplicative wealth + redistribution produces a genuine power-law tail (slope −1.89, max/mean 47) whose exponent tracks J; Gini decreases 0.66→0.27 as J rises.
- framing-disclosure: **pass** — genuine WealthAgents, Itô Euler-Maruyama SDE, mean-field, disclosed.

## Verdict: SOUND. 3/3 REPRO, on the exact inverse-gamma theory.
P1 Gini decreases monotonically with redistribution (0.664>0.495>0.374>0.273, all three bands hit); P2
genuine power-law tail at μ=2 (slope −1.89, 99.9pct/mean=20, power-law beats exponential AIC 3/3 seeds);
P3 Hill μ̂ ordering 1.30<1.78<2.44<3.50 tracking μ=1+J/σ². The careful noise-convention handling (physics
2σ²·dt) is a faithfulness feature, not a tune — stationary Gini sits on the analytic inverse-gamma values.
Distinctness: unlike Dragulescu-Yakovenko (conserved → exponential, Gini 0.5), the MULTIPLICATIVE dynamics
give a Pareto power law with a redistribution-tunable exponent. 30 tests. No tuning.

REVIEW COMPLETE
