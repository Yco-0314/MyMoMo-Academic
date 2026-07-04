# Classic Reproductions - Batch 7 (opinion dynamics beyond voter)

**Date:** 2026-07-01. This batch continues the 51-100 classics roadmap after the suite
reached 50 models. Scope: five opinion-dynamics models that must be distinguishable from
the already-built voter, Sznajd, Galam majority, Deffuant, and Hegselmann-Krause studies.

**Execution split:** design and locked-prediction strategy cover all five models, but
implementation should run in two waves:

- **Wave A:** `q_voter`, `noisy_voter_kirman`, `abrams_strogatz_language`.
- **Wave B:** `coda_continuous_opinions`, `social_impact_theory`.

This split keeps the first implementation wave well-mixed / scalar, and leaves the spatial
domain and distance-weighted influence models for a separate review pass.

## Shared Discipline

- Write `PREDICTIONS-locked.md` for each study before any production run.
- Commit locked predictions before running the reproduction.
- Do not tune parameters after observing verdicts.
- Falsified clauses are reported as **MISS**, not weakened post-hoc.
- Use `abm_auto.repro_bundle` and `Verdict` for all study bundles.
- Add faithful-rule + determinism tests under `tests/classics/`.
- Put model code under `abm_auto/classics/`, runners under `examples/repro_<name>/`, and
  study artifacts under `docs/studies/<name>/`.
- Disclose framing precisely. All five models in this batch are genuine agent-state models,
  but several are model-driven asynchronous processes rather than autonomous per-agent
  scheduler loops. The docstring and FINDINGS should say which unit of action is used.

## Existing Nearest Neighbours

Already built:

- `voter`: well-mixed binary copying, absorbing consensus, linear exit probability.
- `sznajd`: 2D local persuasion by agreeing groups, binary opinions.
- `galam_majority`: random local-majority groups, threshold/minority-spreading effects.
- `deffuant`: pairwise continuous bounded-confidence averaging.
- `hegselmann_krause`: synchronous all-neighbours-within-confidence averaging.

Batch 7 must not reproduce these again under new names. Each model below has a locked
signature that an existing nearest neighbour should fail.

## Sources Used

- Castellano, Munoz & Pastor-Satorras 2009: non-linear q-voter model, q unanimous
  neighbours, noise epsilon, exit probability and ordering regimes.
- Carro, Toral & San Miguel 2016: noisy voter model with random state changes and a
  finite-size noise-induced transition affected by network structure.
- Abrams & Strogatz 2003: language competition with status and volatility; no stable
  coexistence in the two-language model.
- Martins 2008/2009 CODA line: continuous hidden beliefs inferred from observed discrete
  actions; local reinforcement produces extremism.
- Nowak, Szamrej & Latane 1990 dynamic social impact: spatially repeated influence produces
  consolidation, clustering, correlation, and continuing diversity.

## Model 1 - `q_voter`

**Framing:** genuine binary opinion agents; asynchronous model-driven updates.

**Mechanism:** N binary agents on a complete graph. One update picks a target agent and q
neighbours, sampled with replacement as in the mean-field q-voter formulation. If the q
neighbours are unanimous, the target adopts that opinion. If they are not unanimous, the
target flips with noise probability `epsilon`. For q=1 and `epsilon=0`, this should reduce
to the linear voter copying process.

**Why distinct:** the built voter has linear exit probability and no nonlinear q-panel
agreement. q-voter must show a q-dependent nonlinear exit probability / ordering response.

**Locked run shape:**

- N around 400-800 for exit-probability sweeps, with enough seeds to reduce binomial noise.
- Initial up-fraction grid: `{0.2, 0.3, 0.5, 0.7, 0.8}`.
- Use a max-step cap and report capped runs honestly.
- For q=1, `epsilon=0`, compare fixation probability against initial up-fraction.
- For q=2 or q=4, compare against q=1 on the same grid.

**Lockable predictions:**

- P1: q=1 reduces to linear voter: fixation probability to all-up is within +/-0.07 of
  initial up-fraction at x in `{0.2, 0.5, 0.8}`.
- P2: q>1 is nonlinear: the exit-probability curve differs from the q=1 straight line by
  at least 0.08 at one off-centre point, while symmetry keeps E(0.5) within +/-0.08 of 0.5.
- P3: noise weakens ordered fixation: at fixed q=4 and x=0.7, increasing `epsilon` reduces
  the all-up fixation probability or increases mixed/capped outcomes compared with
  `epsilon=0`.

**Risks:** published hysteresis claims are sensitive to mean-field formulation, system size,
and epsilon convention. Phase 1 should lock coarse exit-probability signatures, not claim a
precise critical epsilon.

## Model 2 - `noisy_voter_kirman`

**Framing:** genuine binary opinion agents; asynchronous model-driven updates.

**Mechanism:** N binary agents. Each update picks a target. With spontaneous flip rate `a`,
the target flips state independent of neighbours. Otherwise it copies a random other agent,
as in the voter model. This removes absorbing states and produces an ergodic stationary
magnetization distribution.

**Why distinct:** the built voter has absorbing all-0/all-1 states. Noisy voter should never
stay absorbing under `a>0` and should show a finite-size transition in the stationary
distribution controlled by `a*N`.

**Locked run shape:**

- Simulate long stationary traces after burn-in, recording magnetization.
- Compare weak noise `a*N < 1` and strong noise `a*N > 1`.
- Sweep N in `{100, 400, 1600}` only if runtime is acceptable; otherwise use N `{100, 400}`
  and mark scaling as coarse.

**Lockable predictions:**

- P1: Weak noise has herding / bimodality: for `a*N < 1`, stationary magnetization has more
  mass near `|m| > 0.6` than near `|m| < 0.2`.
- P2: Strong noise is centred / unimodal: for `a*N > 1`, stationary magnetization has more
  mass near `|m| < 0.2` than near `|m| > 0.6`, and mean magnetization is near 0.
- P3: finite-size scaling is visible: the crossover occurs at approximately constant
  `a*N`, so runs with matched `a*N` at different N have similar edge-vs-centre mass ratios
  within a broad tolerance.

**Risks:** exact stationary distribution depends on update convention and complete-graph vs
network topology. Phase 1 should use complete graph and lock distribution-shape gates, not a
precise critical point.

## Model 3 - `abrams_strogatz_language`

**Framing:** genuine language-state agents with model-driven stochastic transitions.

**Mechanism:** N agents choose language A or B. A speaker switches with probability
proportional to the status of the other language and the current fraction of speakers of the
other language raised to volatility exponent `alpha`. For status `s_A > 0.5`, language A
has a larger basin. The deterministic mean-field model has unstable coexistence and stable
monolingual endpoints.

**Why distinct:** voter/Sznajd/Galam are symmetric binary opinion models. Abrams-Strogatz
adds status asymmetry and nonlinear attractiveness, producing basin-boundary behaviour and
language death.

**Locked run shape:**

- Use complete-graph / well-mixed stochastic transitions with N large enough to reduce
  demographic noise.
- Sweep initial A-share around the theoretical unstable fixed point.
- Run enough seeds per initial share to estimate A-survival probability.

**Lockable predictions:**

- P1: no stable coexistence: with unequal status, late A-share is usually near 0 or 1
  rather than near the interior, with interior-late fraction below 0.15.
- P2: higher-status language has the larger basin: for `s_A > 0.5`, A wins for initial
  shares above the predicted basin boundary and loses below it, with measured boundary
  within +/-0.08 of the mean-field value.
- P3: equal status is symmetric: with `s_A = 0.5` and initial A-share 0.5, A-win fraction
  is within +/-0.10 of 0.5.

**Risks:** stochastic finite populations can drift across basin boundaries. Gates should use
seed-averaged basin classification rather than single runs.

## Model 4 - `coda_continuous_opinions`

**Framing:** genuine spatial opinion agents; model-driven local interaction.

**Mechanism:** Agents live on a 2D periodic lattice. Each has a hidden continuous belief
represented as log-odds, but externally expresses only a discrete action/sign. A local
interaction observes a neighbour's discrete action and updates hidden log-odds by a fixed
Bayesian increment toward that action. The observable action is the sign of the hidden
log-odds.

**Why distinct:** Deffuant/HK average continuous opinions toward moderation. CODA exchanges
discrete actions and reinforces hidden beliefs, so it produces extremism and stable domains.

**Locked run shape:**

- Lattice around 40x40 or 50x50.
- Random near-neutral initial log-odds with random actions.
- Run several seeds for enough sweeps to see local reinforcement.
- Record median absolute log-odds, like-neighbour fraction, and connected action domains.

**Lockable predictions:**

- P1: hidden opinions extremize: median `|log_odds|` exceeds 5 after the late window for a
  majority of seeds.
- P2: spatial action clustering increases: like-neighbour fraction rises from near 0.5 to
  above 0.80.
- P3: global consensus is not required: at least two macroscopic action domains persist in
  a substantial fraction of seeds while agents inside those domains are individually
  near-certain.

**Risks:** domain persistence depends on lattice size and update horizon. If P3 is noisy,
report MISS honestly rather than extending the run until it passes.

## Model 5 - `social_impact_theory`

**Framing:** genuine fixed spatial agents; model-driven opinion updates.

**Mechanism:** Agents occupy a 2D lattice or continuous positions and hold binary opinions.
Each agent has strength/persuasiveness/supportiveness parameters. At each update, net impact
from opposing and supporting sources is distance-weighted, with dynamic social impact's
number effect represented by a sublinear aggregation such as sqrt(count) or summed
strengths with distance decay. Agents flip when opposing impact exceeds supportive impact
plus a small inertia threshold.

**Why distinct:** Schelling clusters by movement; voter/Sznajd cluster or consensus by
copy/persuasion. Dynamic social impact should produce clustering and continuing minority
diversity without agent relocation.

**Locked run shape:**

- Fixed 2D torus, N around 900-1600 agents.
- Random binary initial opinions with minority fraction 0.3.
- Heterogeneous strengths but fixed positions.
- Run asynchronous updates until frozen or capped.

**Lockable predictions:**

- P1: continuing diversity: starting from 30% minority, final minority fraction remains
  above 0.10 in at least 70% of seeds, rather than complete consensus.
- P2: clustering increases: like-neighbour fraction rises from random baseline to above
  0.75 at late time.
- P3: dynamics freeze: late-window flip rate falls below 2% per sweep, indicating a stable
  clustered configuration rather than persistent churn.

**Risks:** many social-impact implementations differ in exact impact formula. The locked
docs must state the formula before running. The result is a faithful implementation of that
dynamic social-impact family, not proof of a single unique equation.

## Test Plan

For each model:

- Unit tests for parameter validation.
- Determinism: same seed returns identical summary / trajectory sample.
- Faithful-rule tests for one elementary update.
- Edge cases: absorbing states, all-same states, invalid q/a/status/epsilon/log-odds values.
- Reproduction runner smoke test for small settings where possible.
- Bundle integrity gate after artifact generation.

Batch-level checks:

- `python -m pytest tests/classics/test_<new>.py -q` for each new model.
- `python -m pytest tests/classics -q`.
- `python engine_oracle.py --science`.
- `python engine_oracle.py --check`.
- `python -m pytest tests/ -q --ignore=tests/gis`.
- Forbidden base-engine diff check over `abm_auto/runtime`, `abm_auto/codegen`,
  `abm_auto/calibration`, `abm_auto/agents`, `abm_auto/pipeline`.

## Scope Exclusions

- No real social-media, language, or survey data.
- No calibration to empirical opinion traces.
- No claim that these models validate real polarization or language death.
- No AutoData-generated challenge harness in this batch; Claude is handling that stream.
- No changes to base-engine forbidden paths.

## Implementation Order

1. Wave A locked docs for `q_voter`, `noisy_voter_kirman`, `abrams_strogatz_language`.
2. Wave A code/tests/runners/artifacts/review.
3. Wave B locked docs for `coda_continuous_opinions`, `social_impact_theory`.
4. Wave B code/tests/runners/artifacts/review.
5. Batch 7 summary note, if the implementation waves land separately.
