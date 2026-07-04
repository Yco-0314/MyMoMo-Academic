# Tag-Based Cooperation (Riolo-Cohen-Axelrod 2001) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Genuine agent-based reproduction on `abm_auto._platform`.
Predictions locked BEFORE running (`PREDICTIONS-locked.md`); config fixed, not tuned.

## What was built
N=100 agents, each with a heritable continuous tag τ∈[0,1] and heritable tolerance T≥0. Each
generation, each agent is a potential DONOR to P=3 randomly-chosen partners (with replacement) and
donates (cost c=0.1, benefit b=1.0) iff |τ_partner − τ_self| ≤ T_self. Reproduction is by tournament
(compare to one random other, copy the fitter) with Gaussian mutation of τ and T (rate 0.1, σ=0.01,
T truncated at 0). This is WELL-MIXED (random pairing, no space), the distinctive feature vs the
built spatial ethnocentrism model. Cooperation is sustained WITHOUT reciprocity, reputation, memory,
or space — purely by tag similarity.

## Locked config (fixed before run)
N=100, P=3, c=0.1, b=1.0, mutation rate/σ = 0.1/0.01, 30,000 generations, 10 seeds, burn-in 100,
CV window 200.

## Results (10 seeds; tight)
- mean donation rate = **0.6133** (range [0.603, 0.618], std 0.005) — paper reports 0.736; our
  generation-averaged rate over the full run (incl. birth/growth/collapse waves) lands in the broad
  faithful band.
- mean modal-tag-cluster share = **0.9104** (|τ − modal τ| ≤ 0.01; min 0.906) — a dominant tag group.
- mean within-run CV of the donation rate = **0.3232** (min 0.312); a crash-and-recover event
  occurred in **10/10 seeds** — cooperation is intermittent (waves of tolerance), not a plateau.

## Verdicts (refutation tier) — 3/3 REPRO
- **P1 REPRO** — tag-similarity donation sustains cooperation: mean donation rate 0.6133 ∈ [0.55, 0.85].
- **P2 REPRO** — a dominant tag cluster forms: modal-cluster share 0.9104 ≥ 0.60.
- **P3 REPRO** — cooperation is INTERMITTENT: within-run CV 0.3232 ≥ 0.10 AND crash-and-recover in
  10/10 seeds (the tolerance up-drift → intolerant-mutant-invasion waves).

No honest MISS. The Riolo-Cohen-Axelrod headline — cooperation without reciprocity via tag similarity,
occurring in recurrent waves — reproduces. (Experiment authored + run centrally after the builder
wrote the code but its process hit an API error before completing the run.)
