# Axelrod 1997 Dissemination of Culture — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`):
each lattice site is an autonomous `CultureAgent` enacting the Axelrod activation rule
under an `AgentSet` + `DataCollector` (not a god-loop). Code:
`abm_auto/classics/axelrod_culture.py`; experiment:
`examples/repro_axelrod_culture/run.py`.

**Headline: more traits → more polarization.** At F=5 the absorbing configuration goes
from a single monocultural region at small q (q∈{2,5} → exactly 1 region) to a strongly
polarized landscape at large q (q=15 → ~17.5 regions). Adding *features* does the
opposite: at fixed q=10, doubling F from 5 to 10 collapses the map from ~2.6 regions back
toward monoculture (~1.1). This is Axelrod's central "local convergence, global
polarization" result.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| grid | **L = 10** (10×10 = 100 sites) |
| neighbourhood | **von-Neumann-4** (N/S/E/W), bounded lattice, **no wrap** (Axelrod's original) |
| culture | F integer features, each a trait in [0, q) |
| activation event | pick random site + random neighbour; interact w.p. = cultural similarity; on interaction copy one random **differing** feature's trait |
| stop rule | **absorbing state**: no adjacent pair has 0 < similarity < 1 |
| outcome | **#stable regions** = connected components of identical-culture neighbours (von-Neumann adjacency) |
| seeds per cell | **10** (seeds 0–9) |
| q-grid (at F=5) | **2, 5, 10, 15** |
| F-grid (at q=10) | **5, 10** |

Update is one uniformly-random activation per model step (Axelrod's event-driven
schedule). Runs are deterministic given the seed and halt exactly at absorption (an
O(n) absorbing-state test is amortised every n=100 steps and re-checked exactly at the
end). **Every cell reached a true absorbing state** (`all_absorbed = True` everywhere).

## Measured #regions vs number of traits q (F=5), mean over 10 seeds

| q | mean #regions | min | max | largest-region fraction | absorbed |
|---|---|---|---|---|---|
| 2 | **1.0** | 1 | 1 | 1.00 | yes |
| 5 | **1.0** | 1 | 1 | 1.00 | yes |
| 10 | **2.6** | 1 | 6 | 0.95 | yes |
| 15 | **17.5** | 10 | 32 | 0.54 | yes |

Monotone increasing in q. The jump between q=10 and q=15 is the onset of the polarized
regime: at q=15 the largest region covers only ~54% of the grid, vs a full monoculture
at q≤5.

## Measured #regions vs number of features F (q=10), mean over 10 seeds

| F | mean #regions | min | max | largest-region fraction | absorbed |
|---|---|---|---|---|---|
| 5 | **2.6** | 1 | 6 | 0.95 | yes |
| 10 | **1.1** | 1 | 2 | 1.00 | yes |

Decreasing in F: more features → more chance two neighbours share *something* →
interaction probability stays positive longer → convergence wins → fewer surviving
regions. (At q=10, F=5 the q-sweep and F-sweep agree — same cell, mean 2.6.)

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | #regions increases with q: #regions(q=15) > #regions(q=5) at F=5 | **REPRO** | 17.5 > 1.0 |
| P2 | #regions decreases with F: #regions(F=10) < #regions(F=5) at q=10 | **REPRO** | 1.1 < 2.6 |
| P3 | Monoculture limit: small q (2–5, F=5) → ≤ ~3 regions | **REPRO** | worst small-q mean = 1.0 ≤ 3 |

**3/3 testable clauses REPRO.** The reproduction recovers Axelrod's qualitative
signature: cultural diversity (region count) rises with the number of traits and falls
with the number of features, with a clean monocultural limit at small q.

## Honest caveats

- **Does q=2 fully monoculture? Yes — and so does q=5.** At F=5 every one of the 10 seeds
  collapsed to a *single* region (min=max=1, largest-region fraction 1.00) for both q=2
  and q=5. The near-monoculture regime is therefore *exact* monoculture here, not merely
  "≤3 regions". This is even stronger than the locked clause requires.
- **P1's effect lives between q=10 and q=15.** At F=5 the region count is essentially 1
  up to q=5, only 2.6 at q=10, then jumps to 17.5 at q=15. The locked P1 (q=15 vs q=5) is
  comfortably cleared, but the transition is sharp — a coarser q-grid that skipped q=15
  could miss the polarized regime. The grid was fixed before running.
- **High variance at q=15.** The per-seed region count at q=15 ranges 10–32 (mean 17.5).
  Ten seeds pin the *direction* unambiguously (every seed ≫ the q=5 value of 1) but the
  mean has wide spread; more seeds would tighten it. We did not add seeds after seeing the
  spread (that would be post-hoc).
- **Region vs distinct-culture distinction.** The outcome is *spatial* connected
  components, not the number of distinct culture vectors. `results.json` also records
  per-seed `distinct_cultures` as a diagnostic; for the absorbing configurations here the
  two coincide closely because like-cultured sites end up spatially contiguous, but the
  reported metric is the connected-component count (Axelrod's "regions").
- **Neighbourhood = von-Neumann-4, bounded (no wrap).** This matches Axelrod 1997. A
  Moore-8 or toroidal lattice would shift the absolute counts but not the two
  directions; we fixed the choice before running and did not explore alternatives to
  move a number.
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed together with the code, so it points to the parent
  commit). Reproduction integrity is anchored on the content-addressed **sha256** of the
  docs/data artifacts (all `replay: strong`), not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* model — no real-world data.
  The contribution is that the harness + lock-first discipline reproduce Axelrod's
  traits→polarization result and would surface an artifact (a refutation gate, not a
  truth certificate).
