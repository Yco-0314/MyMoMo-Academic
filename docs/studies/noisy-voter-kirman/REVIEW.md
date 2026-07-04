# noisy-voter / Kirman — adversarial review

**tier: deep** (trigger: 2 honest MISSes in the bundle). Reviewed against the verified canonical
claim (Carro, Toral & San Miguel 2016, Sci. Rep. 6:24775; a_c = h/N on the complete graph).

## Mandatory cheap checks
- numeric-provenance: **pass** — headline numbers match results.json.
- fair-control: **pass** — regimes differ only in (N, a); the P2/P3 contrasts are single-variable within their design.
- no-post-lock-drift: **pass** — graded metrics match PREDICTIONS-locked.md; no post-result tuning.
- mechanism-aliveness: **pass** — spontaneous flip (rate a) and random-neighbour copy are both wired in (update(): `spontaneous = rng.random() < a`); random-neighbour copy correctly equals adopting opinion with probability = population fraction (the h·n/k normalization is right).
- framing-disclosure: **pass** — genuine binary agents, asynchronous updates; disclosed.

## Verdict: model plausibly FAITHFUL; the two MISSes trace to UNDER-EQUILIBRATION at weak noise.

- **P1 MISS (weak edge−center = −0.131; expected > 0 bimodal).** WEAK = {N=400, a=0.001} → a·N = 0.4,
  genuinely sub-critical (should be bimodal). But BURN_IN=20000 updates at a=0.001 is only ~20 spontaneous
  flips; from the m=0.5 (center) start the slow weak-noise mixing has **not relaxed to the bimodal
  stationary distribution**, so mass remains near the center where it started. The verified subtlety warned
  of exactly this ("bimodality requires true stationary sampling; under-equilibrated runs"). **Cause:
  burn-in too short for weak-noise mixing**, not a model defect.
- **P3 MISS (matched a·N ratio diff 4.718 vs 0.35).** MATCHED_SMALL {100, 0.004} and MATCHED_LARGE
  {400, 0.001} are both a·N = 0.4, but N=100 mixes far faster than N=400, so under a fixed BURN_IN the
  small system reaches the bimodal stationary state while the large one does not → the ratios diverge.
  **Same root cause (size-dependent under-equilibration), not a violation of the a_c = h/N scaling.**
- **P2 REPRO (strong noise unimodal, |mean m| ≤ 0.15).** Strong noise mixes fast, equilibrates, passes.

## Discipline check: PASS
1/3 REPRO reported honestly; no tuning of a, burn-in, samples, or bars to flip a verdict. The MISSes are an
honest under-equilibration artifact. Principled fix (result-independent): scale BURN_IN/SAMPLES to the
weak-noise mixing time (≫ 1/a updates; e.g. burn-in ~ 1e6 at a=0.001), or start each seed from a random
near-consensus state and verify stationarity by a forward/backward-window match. A re-lock with adequate
equilibration would confirm the diagnosis and is not tuning-to-pass.

REVIEW COMPLETE
