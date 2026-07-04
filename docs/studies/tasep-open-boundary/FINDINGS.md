# TASEP with Open Boundaries (Derrida, Evans, Hakim & Pasquier 1993) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Cellular-automaton / interacting-particle
reproduction — framing **CA (disclosed)**: this is a stochastic hopping-exclusion rule on
a 1D lattice under random-sequential update, NOT an agent-stepping ABM (there are no
perceive/decide/act agents and no scheduler over an agent roster). Predictions were locked
BEFORE running (`PREDICTIONS-locked.md`); the config below was fixed before the run and
nothing was tuned to make a clause pass.

## What was built

The **totally asymmetric simple exclusion process (TASEP)** on a 1D **open** chain of
`L = 200` sites. Each site holds a binary occupation `occ[i]` in {0, 1} (hard-core
exclusion: at most one particle per site). Particles move only to the **right** (totally
asymmetric), so the maximum hop distance is 1 site.

**Random-sequential update.** One *sweep* = `L` elementary attempts. There are exactly
`L + 1` candidate moves — one **left inject**, the `L - 1` **bulk bonds** `i -> i+1`, and
one **right extract** — and each attempt draws ONE candidate uniformly and applies it with
its rate:

- **left inject** (site 0): if `occ[0] == 0`, set `occ[0] = 1` with probability `alpha`;
- **bulk bond `i -> i+1`**: if `occ[i] == 1 and occ[i+1] == 0`, hop with probability 1
  (bulk hop rate 1);
- **right extract** (site `L-1`): if `occ[L-1] == 1`, set `occ[L-1] = 0` with probability
  `beta`.

The update is strictly sequential within a sweep (each attempt sees the occupations the
previous attempt left), which is the canonical random-sequential TASEP dynamics.

**Observables (locked before the run).** Warm up `WARMUP = 2000` sweeps from the empty
chain (discarded), then measure over `MEASURE = 8000` sweeps:

- **Current** `J` = successful hops across the **fixed central bond** `c = L//2`, counted
  per sweep and time-averaged. Because a specific bond is selected with probability
  `1/(L+1)` per attempt and a sweep is `L` attempts, this equals the per-bond hopping rate
  per unit time in the random-sequential clock, directly comparable to the mean-field
  currents `alpha(1-alpha)`, `beta(1-beta)`, and `1/4`.
- **Bulk density** `rho` = mean occupancy of the **central third** of the chain
  (`L//3 .. 2L//3`), time-averaged. The central third avoids the boundary layers so the
  reported `rho` is the bulk plateau (the lock's `gate_design_check`).
- **Density profile** = per-site time-averaged occupancy (used for the P3 shock check).

The model is deterministic given an integer seed (one `numpy.random.default_rng(seed)`
draws every move choice and every rate acceptance). Reported numbers are means over
`N_SEEDS = 4` seeds (base 0).

## Locked config (FIXED before the run; nothing tuned)

| Param | Value |
|---|---|
| chain length L | 200 |
| update | random-sequential; L+1 candidate moves/attempt; L attempts/sweep |
| warm-up sweeps | 2000 |
| measurement sweeps | 8000 |
| seeds | 0,1,2,3 (4 seeds) |
| P1 plateau points (alpha,beta) | (0.6,0.6), (0.7,0.9), (0.9,0.7), (0.99,0.99), (0.55,0.75) |
| P1 tolerance | \|J - 0.25\| <= 0.02 at every point |
| P2 low-density point | alpha=0.3, beta=0.8; tol +/-0.03 on J and rho |
| P3 coexistence line / crossing | (0.3,0.3) and (0.3,0.15); R^2 >= 0.85, jump >= 0.20 |

## Results (mean over 4 seeds; from the actual run)

### P1 — maximal-current plateau `J = 1/4`

| (alpha, beta) | J (+/- std) | \|J - 0.25\| | bulk rho |
|---|---|---|---|
| (0.60, 0.60) | 0.2507 (0.0006) | 0.0007 | 0.502 |
| (0.70, 0.90) | 0.2510 (0.0007) | 0.0010 | 0.498 |
| (0.90, 0.70) | 0.2510 (0.0008) | 0.0010 | 0.503 |
| (0.99, 0.99) | 0.2511 (0.0008) | 0.0011 | 0.501 |
| (0.55, 0.75) | 0.2504 (0.0003) | 0.0004 | 0.492 |

Worst `|J - 0.25| = 0.0011`, plateau spread across the five points `= 0.0007`. The current
sits on the exactly-known maximal value `1/4` and is **independent of both alpha and beta**
throughout the region `alpha, beta > 0.5`. The bulk density is `~ 0.5` everywhere on the
plateau (the maximal-current-phase value), as expected. **REPRO** (score 0.0011, threshold
0.02).

### P2 — low-density phase (alpha = 0.3 < beta = 0.8)

| quantity | measured | target | \|dev\| |
|---|---|---|---|
| current J | 0.2097 | alpha(1-alpha) = 0.2100 | 0.0003 |
| bulk rho | 0.3009 | alpha = 0.3 | 0.0009 |

The current tracks `alpha(1-alpha)` and the bulk density tracks `alpha` — the phase is
**alpha-controlled** (beta = 0.8 is irrelevant to the plateau). Both within +/-0.03.
**REPRO** (score max(dev) = 0.0009, threshold 0.03).

### P3 — coexistence line ⇒ density jump

On the coexistence line `alpha = beta = 0.3` (< 0.5) the time-averaged density profile is
roughly **linear** — the signature of a freely diffusing shock (domain wall) whose
position wanders uniformly, so the time-average rises across the chain: linear-fit
**R^2 = 0.9364**, slope `+0.00198`/site, rising from `~0.43` (left interior) toward `~0.56`
(right interior). The central-third mean on the line is `rho = 0.496` — near the shock
midpoint `~ 1/2`, exactly what a wall sitting on average mid-chain gives (it is NOT a sharp
alpha=0.3 plateau, because the line has no single bulk density — that is the whole point of
the coexistence line).

**Crossing** the line by lowering `beta` to `0.15` (< alpha = 0.3) drives the system into
the **high-density phase**: the bulk density jumps to `rho = 0.851 ~ 1 - beta = 0.85`. The
density jump is `0.851 - 0.496 = 0.3551 >= 0.20`. (Read against the low-density-branch value
`alpha = 0.3` the jump is even larger, `~0.55`; either reference clears the locked bar.)
**REPRO** (score jump = 0.3551, threshold 0.20).

## Numerical / faithfulness health

- The dynamics is exactly binary (occupations stay in {0, 1}); mass is not conserved by
  design (open boundaries inject/extract), so there is no conservation diagnostic to
  report — the correctness surface is the phase diagram itself.
- Faithfulness tests (`tests/classics/test_tasep_open_boundary.py`, 18 tests) pin the
  totally-asymmetric right-only hop, hard-core exclusion, the rate-gated boundary
  injection/extraction, the `L+1` candidate-move set, central-bond current counting,
  central-third bulk density, the analytic mean-field targets, and determinism. Two
  edge-case tests confirm the physics degrades correctly: `alpha = 0` keeps the chain
  empty forever, and `beta = 0` saturates the chain full with vanishing current (a jammed
  state with no throughput) — the model does not silently "pass" in degenerate limits.

## Honest caveats

- **Framing.** CA (disclosed). This is an interacting-particle / cellular-automaton
  stochastic rule, not an agent-stepping ABM. It is included for the same reason the BTW
  sandpile and the network-generation reproductions are: an exactly-solved, analytically
  sharp target (`J = 1/4`) that stress-tests the lock-first + honest-verdict + L3-bundle
  harness.
- **The coexistence-line profile is "roughly" linear, not perfectly.** R^2 = 0.9364 (not
  1.0): the seed-and-time-averaged profile has mild S-curvature near the boundary layers
  that a strict straight line misses. This is physically correct — the exact averaged
  coexistence profile is not a perfect ramp at finite `L` — and the locked bar
  (R^2 >= 0.85) was set with that in mind. It is reported as-is, not tuned.
- **Distinctness (kept).** A minimal hopping-exclusion process (max velocity 1) with OPEN
  boundaries whose hallmark is a boundary-induced three-phase diagram with an exactly known
  maximal current `J = 1/4` — a distinct analytic target that the closed-ring, `vmax=5`
  Nagel-Schreckenberg model never reaches.

## Verdict

| Clause | Result | Salient number | Threshold |
|---|---|---|---|
| P1 maximal-current plateau J = 1/4, independent of alpha,beta | **REPRO** | worst \|J-0.25\| = 0.0011 | <= 0.02 |
| P2 low-density J ~= alpha(1-alpha) & rho ~= alpha | **REPRO** | max dev = 0.0009 | <= 0.03 |
| P3 coexistence linear profile + density jump | **REPRO** | jump = 0.3551 (R^2 = 0.9364) | >= 0.20 (R^2 >= 0.85) |

All three locked clauses of the open-boundary TASEP phase diagram are reproduced with wide
margins. The boundary-induced three-phase structure — the exactly-known maximal current
`J = 1/4`, the alpha-controlled low-density current and density, and the coexistence-line
shock with its density jump on crossing — emerges from the microscopic random-sequential
hopping-exclusion rule with no fitting.
