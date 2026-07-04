# Sugarscape (Epstein & Axtell 1996) — FINDINGS

**Headline:** Strong wealth inequality emerges from a near-uniform start. On a
50×50 toroidal two-peak sugarscape with rule M (von-Neumann move-to-nearest-max-
sugar, harvest, metabolize, die), the Gini coefficient of agent wealth rises from
**0.23 → 0.48** over 150 ticks (mean over 10 seeds). **P1 REPRO, P2 REPRO, P3
MISS.**

This is a *refutation-tier* reproduction: passing a clause means "not refuted by
this run", not "verified true". A falsified clause is reported honestly as MISS.

## Model (faithful, locked before the run)

- **Grid:** 50×50, **toroidal** (wraps both axes).
- **Landscape:** two sugar "mountains" in opposite quadrants (centres at ≈(0.25,
  0.25) and (0.75, 0.75)), capacities in concentric terraces 0..4. Current sugar
  starts at full capacity.
- **Regrow rule:** **G∞ (instant regrow to capacity each tick).** This is the rule
  Epstein & Axtell use for the canonical wealth-distribution result, and it was
  locked as the model choice *before* grading — see "Regrow-rule choice" below for
  the honest comparison with G1 (+1/tick), which we also ran.
- **Agents:** N = 250 (~10% of 2500 cells; the grid is not saturated). Each agent
  draws once at birth: vision v ~ U{1..6}, metabolism m ~ U{1..4}, initial sugar
  w0 ~ U{5..25}.
- **Rule M:** look only along the 4 cardinal directions out to `vision`; move to
  the nearest UNOCCUPIED cell with the MOST sugar (ties → nearest → fixed
  direction order, a deterministic tie-break); harvest ALL its sugar; subtract
  metabolism; die (remove) if sugar < 0.
- **No agent replacement** (basic rule M only; rule R is *not* implemented — this
  matters for P3, see below).
- Built on `abm_auto._platform` (Agent / AgentSet / AgentModel / DataCollector).
  Deterministic given a seed. 10 seeds (0..9); metrics averaged with variance/range
  reported.

## Results (mean over 10 seeds; G∞)

| metric | value |
|---|---|
| initial mean Gini | 0.229 |
| **final mean Gini** | **0.475** (range 0.432–0.503, var 5.3e-4) |
| Δ (final − initial) | 0.246 |
| final mean wealth | 169.98 |
| final median wealth | 162.25 (mean > median in 9/10 seeds) |
| final top-decile share | 0.270 (≥ 0.30 in only 1/10 seeds) |
| final population | 129.3 of 250 (carrying-capacity die-off) |

## Verdicts on the LOCKED clauses

- **P1 — REPRO.** Final mean Gini = **0.475 ≥ 0.40.** Strong inequality emerges.
  Every one of the 10 seeds finishes above 0.40 (min 0.432), so this is not a
  seed-noise artifact.
- **P2 — REPRO.** Δ = 0.475 − 0.229 = **0.246 ≥ 0.15.** Inequality rises far above
  the near-uniform start; the rise is monotone in the Gini series (≈0.23 → ≈0.35 by
  tick 30 → ≈0.47 plateau).
- **P3 — MISS.** The locked clause is an AND: *mean > median* **AND** *top-decile
  share ≥ 0.30*. The first half holds (mean 169.98 > median 162.25; 9/10 seeds),
  but the **top-decile share is only 0.270 and reaches 0.30 in just 1/10 seeds**,
  so the conjunction fails. The distribution is right-skewed but only *moderately*
  concentrated.

  **Why (honest mechanism, not an excuse):** the heavy right tail and 30%+ top-
  decile concentration in Epstein & Axtell's canonical wealth histogram is produced
  by the **agent-replacement rule R** (agents that die or hit a max age are replaced
  by new *poor* agents), which continuously refills the bottom of the distribution
  and lets a stable elite pull far ahead. The locked model here is **basic rule M
  with no replacement**: after the carrying-capacity die-off (250 → ~129 survivors),
  the survivors are the ones who found and held good sugar, and they accumulate
  unbounded wealth at broadly similar rates — so the distribution is right-skewed
  (mean > median) but the top decile holds ~27%, not ≥30%. P3's threshold was set
  for the replacement-driven histogram; the no-replacement model under-shoots it.
  We did **not** add rule R to make P3 pass — that would be introducing an
  unspecified mechanism to clear a locked threshold.

**Score: 2/3 locked clauses REPRO.** Inequality emerges and rises strongly from a
uniform start (P1, P2); the no-replacement model is too mild on the single top-
decile sub-clause to pass P3.

## Regrow-rule choice (transparency)

We ran BOTH faithful regrow rules over the same fixed config and seeds:

| rule | final mean Gini | Δ | mean>median | top-decile |
|---|---|---|---|---|
| **G∞ (locked)** | 0.475 | 0.246 | yes (9/10) | 0.270 |
| G1 (+1/tick) | 0.416 | 0.187 | **no** (mean 158 < median 165) | 0.220 |

G∞ was chosen as the locked rule because (a) it is the regrow rule Epstein & Axtell
use for the canonical wealth-distribution figure, and (b) under G1 the +1/tick
carrying-capacity regime drives a sharper die-off whose *survivors* are
left-skewed (mean < median), which is itself an interesting artifact but is the
less canonical setting for the inequality claim. **Both rules pass P1 and P2; both
miss P3 on the top-decile sub-clause.** So the P3 MISS is a property of the
no-replacement model, not of the regrow choice.

## Caveats

- Refutation tier only: P1/P2 "REPRO" = "not refuted by this run", not proof of
  the published claim.
- Faithful reproduction of a published *synthetic* model; no real-world data. The
  contribution is whether the harness + discipline reproduce the emergent-
  inequality result and would catch an artifact.
- Tie-breaks in rule M are deterministic (nearest, then fixed direction order)
  rather than random, to keep a seeded run byte-reproducible; this does not change
  the aggregate Gini.
- N, grid, landscape, regrow rule, attribute ranges, tick budget, seed set, and the
  Gini metric were all FIXED before the run. Nothing was tuned to reach Gini 0.40.
