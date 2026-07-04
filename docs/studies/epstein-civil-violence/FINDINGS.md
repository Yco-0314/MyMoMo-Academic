# Epstein 2002 Civil Violence — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`). Genuine
agent-based model on the neutral platform (`abm_auto._platform`): a 40×40 grid of autonomous
`CitizenAgent`s (hardship H, risk-aversion R, grievance G=H·(1−L)) and `CopAgent`s, each
acting on a LOCAL vision neighbourhood (no global oracle). Model:
`abm_auto/classics/epstein_civil_violence.py`; runner: `examples/repro_epstein_civil_violence/run.py`.
(FINDINGS authored by the orchestrator after the building subagent dropped on a connection
error mid-run; the model + tests + runner it produced are intact — 14 tests pass — and the
numbers below are from re-running that runner unchanged.)

Source: Epstein, J.M. (2002) "Modeling civil violence: an agent-based computational
approach", PNAS 99(suppl 3):7243–7250.

## Rule (faithful, Epstein's Model I)

A citizen goes ACTIVE (rebels) iff `G − R·P > T`, where grievance `G = H·(1−L)` (H~U[0,1]
hardship, L global legitimacy), `P = 1 − exp(−k·floor(C/A)_local)` is the estimated arrest
probability (C cops, A actives incl. self in vision; k=2.3), R~U[0,1] risk-aversion, T=0.1.
Cops move to a random site in vision and arrest a random active there (jail term J~U{1..Jmax}).
All agents move to a random empty cell in vision each tick. Outcome = active fraction over time,
averaged over seeds.

## Verdicts (honest REPRO / MISS per locked clause)

| # | Clause | Result | Salient numbers |
|---|---|---|---|
| P1 | high legitimacy (L=0.9) → calm (mean active < 0.05) | **REPRO** | mean active = 0.0000 (SD 0.0000), peak 0.0000 |
| P2 | low legitimacy (L=0.5) → punctuated bursts (burstiness ≥ 5 OR mean active ≥ 0.10) | **REPRO** | burstiness (peak/mean) = 6.40 (SD 0.31); mean active 0.108, peak 0.688 |
| P3 | deterrence: active fraction monotone non-increasing in cop density | **REPRO** | cop 2%→0.375, 4%→0.108, 6%→0.059 (strictly decreasing) |

**3/3 locked clauses REPRO.** Config (FIXED before run): 40×40 grid, k=2.3, T=0.1, jail term
J~U{1..Jmax}, vision radius per the model, cop densities {2%,4%,6%}, L∈{0.9,0.5}, ≥5 seeds.
Nothing tuned to pass; metrics graded exactly as locked.

## The headline (stated plainly)

Epstein's central result reproduces cleanly:

1. **Legitimacy is the switch.** At high legitimacy (L=0.9) grievance G=H·(1−L) is small, so
   essentially no one rebels — the society stays calm (active fraction ≈ 0). Drop legitimacy to
   L=0.5 and rebellion appears.
2. **Rebellion is PUNCTUATED, not steady.** At L=0.5 the active fraction is not a flat level but
   a series of bursts: mean ≈ 0.11 but peaks reach ≈ 0.69, giving a burstiness (peak/mean) of
   6.4. This is Epstein's "punctuated equilibrium" of civil violence — long quiet periods broken
   by sudden outbreaks, an emergent property of the local cop/active deterrence feedback.
3. **Deterrence works monotonically.** Tripling cop density (2%→6%) at fixed legitimacy cuts the
   mean active fraction ~6× (0.375→0.059): more cops raise each agent's perceived arrest risk
   P, pushing G−R·P below the action threshold.

## Honest caveats

- **Burstiness is a real but metric-sensitive measure.** peak/mean = 6.4 captures the
  punctuation, but the peak depends on run length and seed; SD across seeds (0.31) is reported,
  and the qualitative bursts are robust (every seed shows quiet periods + outbreaks). It was
  graded on the locked metric, not switched.
- **P1's exact 0.0 is regime-driven, not luck.** At L=0.9, max grievance is H·0.1 ≤ 0.1 = T, so
  almost no agent ever clears the threshold even at P=0 — the calm is structural for this L, and
  honestly that makes P1 easy to satisfy (a property of the locked L=0.9, not a tuned outcome).
- **Faithful reproduction of a published synthetic model** (Model I, central-authority variant),
  not real-world prediction; no real unrest data. Refutation tier: REPRO = "not refuted".
