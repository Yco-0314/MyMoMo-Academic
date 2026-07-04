# Nowak & May 1992 Spatial Prisoner's Dilemma — FINDINGS

**Reproduction run 2026-06-29, AFTER predictions were locked** (see
`PREDICTIONS-locked.md`). Genuine agent-based model on the neutral platform
(`abm_auto._platform`): a 99×99 toroidal lattice of autonomous `PDAgent`s, each a pure
cooperator (C) or defector (D), playing every Moore-8 neighbour **and itself**, then
synchronously adopting the strategy of the highest-scoring agent in its neighbourhood.
Model: `abm_auto/classics/nowak_may_pd.py`. Runner: `examples/repro_nowak_may_pd/run.py`.

Source: Nowak, M.A. & May, R.M. (1992) "Evolutionary games and spatial chaos",
Nature 359:826–829.

## Configuration (FIXED before the run, not tuned)

| Parameter | Value |
|---|---|
| Lattice | 99×99, **periodic** (toroidal) boundaries |
| Strategies | pure C / pure D |
| Payoff (per partner) | T=b=1.85, R=1, P=0, S=0 |
| Neighbourhood | Moore-8 |
| **Self-interaction** | **YES** (each agent also plays itself — Nowak-May convention) |
| Update | **synchronous** best-response imitation (copy highest-scoring of {self + Moore-8}) |
| Init | random 50/50 C/D (init_coop_fraction = 0.5) |
| Ticks | 200; steady state = mean over the **last 50** ticks |
| Seeds | 0,1,2,3,4 (5 seeds) |
| Well-mixed control | N=9801, 8 random partners **re-drawn every tick** (structure destroyed) |

The RNG seed touches ONLY the initial C/D placement; the dynamics themselves are
deterministic (no RNG), so a given seed reproduces an identical cooperator-fraction
series.

## Measured results (steady-state cooperator fraction, mean over last 50 ticks)

**Spatial lattice (b=1.85):** mean = **0.3167**, range **[0.3141, 0.3210]** over 5 seeds.

| seed | steady-state | final (t=200) |
|---|---|---|
| 0 | 0.3182 | 0.3296 |
| 1 | 0.3141 | 0.3180 |
| 2 | 0.3158 | 0.3093 |
| 3 | 0.3210 | 0.2981 |
| 4 | 0.3143 | 0.3301 |

**⚠ Correction (adversarial review 2026-06-29) — the original well-mixed control was
UNFAIR, and P2/P3 are corrected to MISS.** The first version graded P2/P3 against a
control that turned self-interaction OFF while the spatial arm had it ON — a two-variable
change (structure destroyed AND the self-game removed), which conflated two effects and
inflated the contrast to ~7,700×. The **fair, apples-to-apples control** keeps
`self_interaction=True` (matched to the spatial arm) and only destroys structure
(8 random partners re-drawn each tick).

**FAIR well-mixed control (self-interaction=True, b=1.85):** mean = **0.0834**, range
[0.0824, 0.0846] over 5 seeds. Cooperation is suppressed but NOT extinct.
**Diagnostic — self-interaction-OFF control (NOT graded):** mean = **0.0000410** (the
original unfair number; collapses harder because removing the self-game also hurts).

**Contrast (fair):** spatial / fair-well-mixed = 0.3167 / 0.0834 ≈ **3.8×** — spatial
structure clearly helps cooperation (directionally), but the effect is ~3.8×, not the
inflated 7,700×.

## Verdicts (honest REPRO / MISS per locked clause — CORRECTED)

| # | Clause | Result | Salient number |
|---|---|---|---|
| P1 | spatial steady-state cooperator fraction > 0.10 | **REPRO** | 0.3167 (> 0.10) |
| P2 | (FAIR) well-mixed cooperator fraction < 0.02 | **MISS** | 0.0834 (need < 0.02) |
| P3 | spatial ≫ well-mixed (ratio ≥ 5× OR sp>0.1 & wm<0.02) | **MISS** | ratio 3.8 (need ≥ 5) |

**1/3 locked clauses REPRO** (was over-claimed as 3/3). The solid, faithful result is
**P1 + the canonical-matching spatial fraction (0.317 ≈ 0.31)**: spatial structure
sustains cooperation. The *contrast* (P2/P3) holds in DIRECTION but does not meet the
locked thresholds (<0.02, ≥5×) under a fair self-interaction-matched control — the locked
thresholds were only met by the unfair control. No dynamics were re-tuned; the fix makes
the verdicts stricter, not looser. (b=1.85, lattice, Moore-8+self, synchronous update,
50/50 init were fixed in `PREDICTIONS-locked.md` before the run.)

## The headline (stated plainly)

On a 2-D lattice (with self-interaction, the paper's convention), cooperators in compact
clusters protect each other: interior cooperators out-score the defectors nibbling at the
cluster edge, so clusters persist and regrow, and the population settles at ≈**0.32
cooperators** indefinitely (the measured 0.317 ≈ canonical ~0.31). In a **fair**
well-mixed population (same payoffs + same imitation + self-game, only structure
destroyed) cooperation is suppressed to ≈**0.083** — clearly LOWER than the spatial 0.32,
so spatial structure does help cooperation directionally. But the suppression is ~3.8×,
not to extinction: the locked P2/P3 thresholds (well-mixed <0.02, ratio ≥5×) are NOT met
by a fair control (they were only met by the unfair self-interaction-off control). So
Nowak & May's qualitative claim "structure helps cooperation" reproduces directionally,
but the strong "mixing kills it entirely" form is an artifact of the unfair control here.

## How the measured fraction compares to canonical 0.31

The measured spatial steady-state fraction (0.317, range 0.314–0.321) lands within ~2% of
Nowak & May's reported ~0.31 at b=1.85. The small excess and the seed-to-seed variation
are expected: the published value is itself an average over a chaotically fluctuating
spatial pattern and depends on lattice size, boundary handling, and the averaging window.
The agreement is strong evidence the rule set (especially the self-interaction convention)
is faithful, not merely "cooperation didn't die."

## Honest caveats

- **Self-interaction is load-bearing — at b=1.85 it is the difference between persistence
  and EXTINCTION.** We measured the counterfactual: with self-play OFF (otherwise
  identical config), the spatial steady-state cooperator fraction is **0.0** across seeds
  — cooperation dies completely. So the ≈0.31 attractor is not robust to dropping the
  Nowak-May self-interaction convention; the self-game's R=1 bonus to interior cooperators
  is exactly what lets cluster interiors out-score the high-T defector edge at b=1.85.
  This is why the convention is documented in the module, pinned by the tests
  (`tests/classics/test_nowak_may_pd.py`), and FIXED at `self_interaction=True` — it is
  the convention that reproduces the paper's figures, not a knob turned to pass.
- **Init density is NOT load-bearing for the steady state.** We measured a 0.9 cooperator
  start (self-play ON, otherwise identical): steady-state fraction = **0.316**, essentially
  identical to the 0.5-start 0.317. The attractor is governed by the cluster dynamics, not
  the initial fraction; we fixed 50/50 for a clean, neutral start.
- **Sensitivity to b.** b=1.85 is the canonical value and sits inside the regime that
  produces the dynamic, fluctuating C/D patterns. Other b in (1,2) give different stable
  fractions and qualitatively different patterns (frozen vs chaotic); b was fixed at the
  paper's value, not chosen to hit 0.31.
- **The well-mixed collapse DOES depend on the self-interaction choice (corrected).**
  Earlier wording claimed the collapse was self-interaction-independent — that is FALSE.
  Re-drawing 8 random partners every tick destroys the spatial correlation, but the
  *magnitude* of suppression depends on whether the self-game is kept: with a FAIR control
  (self-interaction=True, matched to the spatial arm) well-mixed settles at ≈**0.083**
  (not ~0); only the unfair self-interaction-OFF control collapses to ~0. P2/P3 are
  therefore graded on the fair control (and MISS — see the verdict table). The spatial
  result itself (P1, 0.317 ≈ canonical) is unaffected.
- **This is a faithful reproduction of a published synthetic model**, not real-world
  prediction. The 1992 deterministic lattice formulation is reproduced; stochastic-update
  or continuous-strategy variants are out of scope.
- **Determinism.** Given a seed (initial placement only), the run is exactly reproducible;
  the payoff matrix, self-interaction, Moore-8 periodic neighbourhood, synchronous
  order-independence, and the single-defector invasion are all pinned by the faithfulness
  tests.
- **Bundle `code_commit` provenance:** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed together with the code, so it points to the parent
  commit, not the one carrying the bundle). Reproduction integrity is anchored on the
  content-addressed **sha256** of the docs/data artifacts (all `replay: strong`), not on
  the commit pointer.
