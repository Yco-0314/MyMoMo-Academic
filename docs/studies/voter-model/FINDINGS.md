# Voter Model Fixation — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
voter is an autonomous `VoterAgent(Agent)` holding its own binary opinion; the model
drives the asynchronous random-pair copy updates — not a god-loop reading a global
oracle. Code: `abm_auto/classics/voter.py`; experiment: `examples/repro_voter_model/run.py`.

## Model (faithful, complete-graph / well-mixed asynchronous voter)

N agents, each holding an opinion in {0, 1}. The dynamics are **asynchronous**:

1. One UPDATE: pick a uniformly random agent **i**; pick a uniformly random **OTHER**
   agent **j** (j ≠ i — the complete graph / well-mixed neighbourhood is everyone else);
   set `opinion[i] = opinion[j]`.
2. The update reads **only the two agents' own local opinions**. No global tally is
   consulted to drive the copy. The running up-count is maintained incrementally purely
   as a cheap absorbing-state check and as the magnetization metric — it is never an
   input to any agent's decision.
3. One **sweep** = N such updates (one update per agent on average).
4. The states **all-0** and **all-1** are **absorbing**: once everyone agrees, every copy
   is a no-op and nothing can ever change. Run until consensus or a generous cap
   (`max_sweeps = 200·N`, far above the O(N)-sweep mean-field consensus time).

Outcome per run = which consensus (all-0 / all-1) + the number of sweeps to reach it.
The LOCKED metric is **P(fixation to all-up) = fraction of runs that end all-1**, over
the ensemble of runs at each u. Determinism: one seeded RNG chain on the model ⇒ same
seed reproduces the run exactly.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| N | **1000** |
| initial up-fraction grid u | **0.2, 0.5, 0.8** |
| runs per u | **200** (seed_base 0 → seeds 0..199) |
| metric | **P(all-up) = fraction of runs ending all-1** |
| P2 tolerance | **±0.07** of u |
| P3 tolerance | **±0.10** of 2u−1 |
| consensus cap | 200·N sweeps (never hit) |

## Measured P(all-up) vs the line P = u (200 runs per u; binomial SE)

| u | P(all-up) | binomial SE | offset \|P − u\| | consensus rate | mean magnetization | (2u − 1) | sweeps to consensus mean [min, max] |
|---|---|---|---|---|---|---|---|
| 0.2 | **0.2000** | 0.0283 | 0.0000 | 1.000 | −0.6000 | −0.60 | 499.6 [34.6, 2766.0] |
| 0.5 | **0.4600** | 0.0352 | 0.0400 | 1.000 | −0.0800 | 0.00 | 695.9 [90.9, 2983.8] |
| 0.8 | **0.7900** | 0.0288 | 0.0100 | 1.000 | +0.5800 | +0.60 | 524.6 [35.2, 2463.6] |

## Fixation probability is the initial density

Across all three densities the fixation probability to all-up sits essentially on the
diagonal **P(all-up) = u**: 0.200 at u = 0.2, 0.460 at u = 0.5, 0.790 at u = 0.8 — worst
offset 0.040, comfortably inside the locked ±0.07 band and within ~1 binomial standard
error of the line in every case (SE ≈ 0.028–0.035 at 200 runs). This is the classic
mean-field voter result (Clifford–Sudbury 1973; Holley–Liggett 1975): under the symmetric
copy rule the up-count is a bounded martingale, so the probability of absorbing into the
all-up state equals the initial up-fraction. The mean final magnetization tracks **2u − 1**
(−0.600 / −0.080 / +0.580 vs −0.60 / 0.00 / +0.60; worst offset 0.080 < 0.10), the
expectation-conservation statement of the same martingale.

## Consensus is always reached (absorbing)

Every one of the 600 runs (200 × 3) reached an absorbing consensus — consensus rate
**1.000** at every u, none truncated by the cap. There is no perpetual coexistence in a
finite well-mixed voter model: the only absorbing states are unanimity, and the finite
population reaches one of them with probability 1. Consensus time is O(N) sweeps with a
wide right tail (mean ≈ 500–700 sweeps, max ≈ 3000), exactly the heavy-tailed
mean-field consensus-time behaviour.

## Verdicts (locked metric = P(fixation to all-up))

| # | Prediction | Result | Number |
|---|---|---|---|
| P1 | every run reaches absorbing consensus (rate = 1.0 at every u) | **REPRO** | min consensus rate 1.000 = 1.0 ✓ |
| P2 | P(all-up) within ±0.07 of u for every u | **REPRO** | worst offset 0.0400 ≤ 0.07 ✓ |
| P3 | mean final magnetization within ±0.10 of 2u−1 for every u | **REPRO** | worst offset 0.0800 ≤ 0.10 ✓ |

**3 / 3 locked clauses REPRO.**

## Caveats (honest)

- **Finite-ensemble noise on P(all-up).** P(all-up) is an estimate from 200 Bernoulli
  realisations per u, so it carries a binomial standard error of ≈ 0.028–0.035. The
  largest deviation from the diagonal (u = 0.5: 0.460 vs 0.500, offset 0.040) is ~1.1 SE
  — sampling noise, not a bias; with more runs it would shrink toward the line. The ±0.07
  band was locked to be a few SE wide at this run count, and the result passes on the
  locked metric without any tuning of N, the u grid, or the run count.
- **Fixation = density is exact only in the mean-field limit.** The result P(all-up) = u
  is exact for the complete graph / well-mixed voter (here the update samples j uniformly
  from all other agents — a genuine complete graph). On low-dimensional lattices the
  fixation probability still equals the initial density (the up-count remains a
  martingale), but consensus-time scaling differs; this study deliberately uses the
  well-mixed case the locked claim is about.
- **The running up-count is a metric, not an oracle.** To make the absorbing-state check
  and the magnetization cheap, the model keeps an incremental up-count. A faithfulness
  test (`test_update_picks_distinct_pair_and_maintains_tally`) verifies it always equals
  an independent recount of agent state, and no agent's copy decision ever reads it —
  each update reads only the two selected agents' local opinions, as the voter rule
  requires.
- **Scope.** This is a faithful reproduction of a published synthetic model (mean-field /
  complete-graph voter); no real-world data. The contribution is whether the harness +
  discipline reproduce the fixation = initial-density result and would catch an artifact —
  they do (P1–P3 pass on the locked metric against the mean-field anchors P(all-up) = u
  and mean magnetization = 2u − 1).
