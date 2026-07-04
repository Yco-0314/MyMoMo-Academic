# Dragulescu-Yakovenko statistical mechanics of money — review

**tier: minimal** (all-REPRO 3/3, textbook-perfect margins; no MISS). Genuine agent-based.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (R²=0.99998, Gini=0.49994, |ΔM|/M=4.7e-16) matches bundle/results.
- fair-control: **pass** — P1 compares the exponential AIC vs a fitted power-law (exponential wins by 2e5); the tests also verify a shape-3 saving-propensity Gamma FAILS P1 (R²≈0.91, interior mode) — the falsification gate.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; no saving propensity added; bundle fingerprints FINDINGS+lock.
- mechanism-aliveness: **pass** — conserved kinetic exchange thermalizes to the exact Boltzmann-Gibbs fixed point (Gini 0.4999, CV 0.9998); a truncated-exponential MLE underflow bug was caught + fixed (load-bearing for the AIC clause).
- framing-disclosure: **pass** — genuine agent-based money exchange, disclosed.

## Verdict: SOUND. 3/3 REPRO, textbook-exact.
P1 exponential shape R²=0.99998 (mode at m→0, AIC beats power-law by 2e5); P2 Gini=0.49994, CV=0.99983
(the exact exponential fixed point); P3 money conserved to 4.7e-16, T within 0.06% of ⟨m⟩. The
interior-peak FAIL gate is verified (a Gamma saving-propensity distribution fails), so this is a genuine
exponential, not a mislabeled peaked distribution. Distinctness: conserved kinetic exchange → universal
exponential (Gini exactly 0.5), which sugarscape (landscape-set Gini) and ZI (efficiency) cannot produce.
21 tests. No tuning.

REVIEW COMPLETE
