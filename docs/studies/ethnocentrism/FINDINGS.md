# Hammond & Axelrod 2006 Ethnocentrism — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
site occupant is an autonomous `EthnoAgent` (a tag + a (coop-in, coop-out) strategy) and
the model drives the four Hammond-Axelrod stages over an `AgentSet` scheduler +
`DataCollector` (not a god-loop). Code: `abm_auto/classics/ethnocentrism.py`; experiment:
`examples/repro_ethnocentrism/run.py`.

## Config (FIXED before the run; canonical Hammond-Axelrod values; no tuning)

| param | value |
|---|---|
| grid | **50 x 50** sites, von Neumann (4) neighbourhood, empty sites allowed |
| tags | **4** colours |
| benefit b / cost c | **0.03 / 0.01** (b/c = **3**) — donation game: cooperate = pay c, give b |
| base PTR | **0.12** (potential-to-reproduce floor; payoff adds; PTR clamped to [0,1]) |
| mutation | **0.005** per locus (tag, coop-in bit, coop-out bit; independent) |
| death rate | **0.10** per agent per tick |
| ticks | **2000** |
| tail averaged | last **200** ticks |
| seeds | **5** (0,1,2,3,4) |

Tick order (the paper): (1) **immigration** — one random agent (random tag + random
strategy) to a random empty site; (2) **interaction** — every agent plays a one-shot
donation/PD with each of its occupied von Neumann neighbours (cooperate -> pay c, give b);
each agent's PTR starts at 0.12 and accumulates net payoff; (3) **reproduction** — each
agent reproduces with prob = its PTR into a random empty neighbour, offspring inherits
tag+strategy with per-locus mutation; (4) **death** — each agent dies with prob 0.10.
Deterministic given a seed (verified by the test suite). Mean steady-state population
~= **1519 / 2500** sites (~61% occupancy).

## Measured steady-state outcome (mean over 5 seeds, last 200 ticks)

| strategy (phenotype) | mean share | +/- sd |
|---|---|---|
| **ethnocentric** (C-in, D-out) | **0.688** | 0.025 |
| **humanitarian** (C, C) | **0.185** | 0.047 |
| egoist (D, D) | 0.095 | 0.029 |
| traitorous (D-in, C-out) | 0.033 | 0.010 |

| cooperation rate | mean | +/- sd |
|---|---|---|
| **in-group** (same tag) | **0.885** | 0.035 |
| **out-group** (different tag) | **0.243** | 0.030 |

Per-seed ethnocentric share: 0.659, 0.694, 0.724, 0.691, 0.672 — ethnocentric is the
single largest strategy in **all 5 seeds**, and humanitarian is second in all 5 (its
share, 0.136-0.247, exceeds egoist's 0.059-0.124 in every run).

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Ethnocentric is the MOST common strategy at steady state | **REPRO** | ethnocentric 0.688 > 2nd (humanitarian) 0.185 |
| P2 | Ethnocentric share > 0.40 | **REPRO** | ethnocentric share **0.688** > 0.40 |
| P3 | In-group cooperation rate > out-group cooperation rate | **REPRO** | in-group **0.885** > out-group **0.243** |

**3/3 locked clauses REPRO.** The reproduction recovers Hammond & Axelrod's central
result: in a viscous (spatially clustered) population, the **ethnocentric** strategy —
cooperate with your own tag, withhold from others — dominates (~0.69), the
**humanitarian** strategy is a clear second (~0.19), and realized cooperation is strongly
in-group-biased (0.89 vs 0.24). Ethnocentrics form same-tag clusters whose members each
subsidise their neighbours' reproduction while exploiting (by withholding from) adjacent
out-group agents, so the ethnocentric phenotype out-reproduces both the unconditional
cooperators (humanitarians, who are exploited across tag boundaries) and the defectors
(egoists/traitors, who get no in-group subsidy).

## Honest caveats

- **The result is b/c-sensitive — this is the key parameter, not the metric.** Ethnocentric
  dominance is a property of the **benefit/cost ratio** (here the canonical b/c = 3). When
  the per-act benefit comfortably exceeds the cost, the in-group subsidy ethnocentrics give
  each other pays for itself and clustered cooperation invades; at much lower b/c the
  in-group subsidy no longer covers its cost and ethnocentrism does **not** emerge. We fixed
  b/c at the published value of 3 and did **not** sweep or tune it to obtain the result. A
  reproduction that wanted to *falsify* the claim could lower b toward c and watch
  ethnocentric share collapse — the metric would honestly report MISS, which is the point.
- **Spatial viscosity is load-bearing.** The von Neumann (local) neighbourhood + local
  reproduction into an empty neighbour is what lets same-tag clusters form; a well-mixed
  version of the same payoffs would not favour ethnocentrism. This is faithful to the paper
  (which contrasts its local model against mean-field expectations), not a free parameter.
- **Humanitarian-vs-egoist ordering has the most cross-seed spread.** Ethnocentric (sd 0.025)
  and traitorous (sd 0.010) are tight; humanitarian (sd 0.047) and egoist (sd 0.029) vary
  more. Humanitarian still beats egoist in every one of the 5 seeds, but with a smaller
  margin in seeds 2-4 (e.g. 0.136 vs 0.124 in seed 3) — the "humanitarian 2nd" ordering is
  real here but is the softest part of the picture; only P1/P2/P3 are locked clauses.
- **PTR is clamped to [0,1].** Net payoff plus the 0.12 base can in principle push PTR
  outside [0,1]; we clamp it so it is a valid reproduction probability. With b=0.03 and <=4
  neighbours the realistic range is well inside [0,1], so the clamp essentially never binds
  at these parameters; it is a guard, not a tuning knob.
- **Determinism & seeds.** Every run is reproducible from its seed (pinned by the test
  suite). 5 seeds are averaged; cross-seed sd is reported for every quantity above.
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed with the code, so it points to the parent commit).
  Reproduction integrity is anchored on the content-addressed **sha256** of the docs/data
  artifacts (`replay: strong`), not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* model — no real-world data.
  The contribution is that the harness + lock-first discipline reproduce the
  ethnocentric-dominance result and would surface an artifact (a refutation gate, not a
  truth certificate).
