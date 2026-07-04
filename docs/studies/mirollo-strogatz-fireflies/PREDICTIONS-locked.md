# Mirollo-Strogatz pulse-coupled oscillators (1990) — PREDICTIONS (locked)

**Locked 2026-07-02, BEFORE running.** Claim is Mirollo & Strogatz 1990 (SIAM J Appl Math 50:1645), not
tuned. **Genuine-agent (disclosed): integrate-and-fire oscillators.** Verified; gate-checked.

**Model:** N integrate-and-fire oscillators (the agents). Each has a phase φ ∈ [0,1] rising at unit rate; its
"voltage" is a CONCAVE-down charging curve x = f(φ) (e.g. f(φ) = (1/b)·ln(1 + (e^b − 1)·φ), concave for b>0).
When an oscillator reaches φ=1 it FIRES and resets to 0, and pulls every other oscillator's voltage up by ε
(pulse coupling); any oscillator driven to/over threshold by that kick also fires (absorption — firings
coalesce). Random initial phases (seeded). Full synchrony = all oscillators fire together every cycle.

| # | Prediction | Pass clause |
|---|---|---|
| P1 | Universal synchronization (measure-1). | starting from random phases, the system reaches FULL sync (all N in one firing group) for ≥ 95% of random seeds at N=100, ε=0.1, concave curve. |
| P2 | Coupling speeds synchronization. | median cycles-to-sync is strictly smaller at ε=0.2 than at ε=0.05 (stronger pulse coupling ⇒ faster sync), monotone in ε. |
| P3 | Concavity is necessary. | with a LINEAR (non-concave) charging curve, the SAME protocol fails to reach full sync for most seeds (sync fraction < 0.5) — confirming that curve CONCAVITY, not mere pulse coupling, drives the universal result. |

**Discipline:** N, ε grid, curve parameter b, absorption rule, seeds, max-cycles cap FIXED; metrics locked; no
tuning. Falsified → MISS. gate_design_check: sync detected as all-in-one-absorption-group within a max-cycle
cap; P1/P3 are the load-bearing claims (measure-1 sync; concavity-necessity), P2 the monotone control.
**Distinctness (keep):** DISCRETE integrate-and-fire PULSE coupling with state resets + absorption, syncing
for almost-all IC with NO finite coupling threshold and depending on curve CONCAVITY — absent from kuramoto
(continuous sinusoidal coupling, finite critical K_c, no firing/reset, no concavity dependence).
