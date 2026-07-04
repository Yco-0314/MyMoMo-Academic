# Axtell Model of Firms (Axtell 1999/2001) — FINDINGS

**Status: 1/3 locked clauses REPRO. P1 (Zipf firm sizes) REPRO decisively; P2 (extreme
Gini) and P3 (Laplace-strength growth kurtosis) are honest MISSes — the two *qualitative*
signatures (strong right-skew; leptokurtic growth with volatility falling in size) are both
present with the correct sign, but this faithful base-case implementation does not reach the
locked quantitative bars.** Genuine agent-based reproduction on `abm_auto._platform`.
Predictions were locked BEFORE running (`PREDICTIONS-locked.md`); the config below was fixed
before the run and was NOT tuned to make any clause cross its threshold.

## What was built

A population of **A = 5000** `FirmAgent`s, each carrying a FIXED Cobb-Douglas preference
`theta_i ~ U(0,1)` over its **income** (an equal share of its firm's output) and its
**leisure** (`1 - e_i`), where effort `e_i in [0,1]`. Firms are groups of agents. A firm
whose members supply total effort `E = sum e_j` produces

    O(E) = a*E + b*E^2        (a = b = 1; the b*E^2 term is the local increasing return),

and shares output **equally**: a member of an `n`-member firm earns `O(E)/n`, so utility is
`U_i = (O(E)/n)^{theta_i} * (1 - e_i)^{1-theta_i}` (paper eq. 3).

When an agent is **activated** (random asynchronous activation, one agent at a time; a
"period" = `A` activations with replacement), it takes every OTHER agent's effort as fixed
and, for each option in

    { stay in current firm, found a new singleton firm,
      join friend-1's firm, join friend-2's firm },

computes its own **best-response effort** and the resulting utility, then moves to the argmax
and sets its effort there. The best-response effort maximises `O(Ebar+e)^{theta} (1-e)^{1-theta}`
(the `1/n` share is constant in `e`); its first-order condition is a quadratic in `e`, solved
in closed form and **verified against a numerical line search to grid resolution** in the
tests. Each agent has **nu = 2 fixed random network neighbours** (a social network assigned
once at t=0, never re-drawn); the two "friend firms" are the firms those neighbour-agents
currently belong to.

Everyone starts as a singleton. The model runs to a **stationary** firm-size distribution;
because large firms are **rare and transient** (they boom, then abruptly perish — Axtell's
Fig. 12), the size distribution and per-firm log-growth rates are sampled from **many
independent snapshots** across the post-burn-in run, not one instantaneous cross-section.

The firm registry (`firm_effort`, `firm_size`) is kept **exact and updated incrementally** on
every effort change and every move, so an activation costs O(nu), not O(#firms); the tests pin
that the cached totals always equal the recomputed truth and that total membership is
conserved.

### Faithfulness (what was deliberately NOT changed)

The mechanism is the paper's **base case**, verified line-by-line against the primary text
(Axtell 1999 CSED WP-3):

- **Lazy per-agent effort updates.** Only the activated agent re-optimises; other members
  keep their last effort until they themselves are drawn. (The section 2.2 analytical worked
  example showing simultaneous Nash re-equilibration is the *equilibrium analysis*, not the
  simulation dynamics.) An eager "all members re-optimise on composition change" variant was
  tried during characterisation and *flattened* the growth kurtosis — it is unfaithful and
  was rejected.
- **Candidate set = {stay, singleton, 2 fixed-friend firms}** — "limited information
  processing", NOT a fresh random sample of firms each step. A fresh-sample variant does
  sharpen the tail (mean size -> ~4-5, Gini -> 0.61), but it is **unfaithful** (the paper's
  friends are a fixed nu=2 social network) and it *destroys* the tent-shaped growth — so it
  was rejected. We report the faithful base case.
- **Strictly equal output sharing.** Compensation-by-contribution and agent "loyalty" are
  section 4.7 / Table-8 variations that increase concentration; the base case uses neither.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| population A | 5000 (lock: N >= 5000; larger sharpens the tail) |
| production (a, b) | 1.0, 1.0 — O(E) = E + E^2 |
| fixed neighbours nu | 2 |
| seeds | 0,1,2,3 (4 seeds) |
| periods / burn-in | 600 / 200 (each period = A activations) |
| sampling gap | 5 periods |

## Results (mean over 4 seeds)

| Quantity | Value | Per-seed |
|---|---|---|
| **P1** rank-size log-log slope | **-1.277** | -1.30, -1.25, -1.27, -1.29 |
| **P2** firm-size Gini | **0.474** | 0.47, 0.49, 0.48, 0.46 |
| **P3** log-growth excess kurtosis | **0.590** | 0.70, 0.58, 0.47, 0.61 |
| **P3** sigma-growth vs size (log-log slope) | **-0.078** | -0.05, -0.08, -0.08, -0.11 |
| mean firm size | 2.67 | — |
| max firm size | ~83 | — |
| number of firms | ~1872 | — |

The firm-size distribution is heavily right-skewed: at any snapshot most firms are singletons
or size 2-3, with a thin tail of firms in the tens (max ~83 at N=5000; transiently larger).
The activation mix over the run is ~41% stay / ~47% join / ~12% found-singleton — agents
actively migrate into productive firms.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Zipf firm sizes | rank-size slope in [-1.5, -0.7] | **-1.277** | **REPRO** |
| **P2** | Extreme size inequality | firm-size Gini >= 0.60 | **0.474** | **MISS** |
| **P3** | Tent-shaped (Laplace) growth | excess kurtosis > 1.5 AND sigma falls with size | **0.590** (& slope -0.078 < 0) | **MISS** |

## Honest interpretation

- **P1 (Zipf) is reproduced decisively and is faithful.** The rank-size log-log slope is
  **-1.28**, tight across seeds (std ~ 0.02) and identical on the pooled sample — squarely
  inside the locked [-1.5, -0.7] band and *matching the paper's own base-case exponent*
  (Axtell reports mu = 1.28 for the base case, versus the empirical mu ~ 1.23 US / 1.11 UK).
  The power-law firm-size distribution emerges endogenously from local increasing returns +
  self-interested migration + equal sharing, with **no built-in scale** — this is the
  headline Axtell/Zipf result and it holds.

- **P2 (extreme Gini) is an honest MISS at 0.47 vs the 0.60 bar — but the sign of the effect
  is unambiguously right.** The distribution is strongly right-skewed (Gini 0.47 >> 0 already
  signals a heavy right tail: a few firms of size 80+ amid ~1900 mostly-tiny firms). The
  locked 0.60 bar was pitched at the *empirical* U.S. figure (~0.89) with slack for finite-N
  tail truncation; this **faithful base case** (A=5000, nu=2 fixed friends, strictly equal
  shares) concentrates less than that. We confirmed during characterisation that the shortfall
  is a genuine, robust property of the faithful formulation, not a run-length or sampling
  artifact: it is stable across seeds, unchanged by pooling ~75 independent snapshots, and
  unchanged by running 3x longer. The Gini *does* rise to >=0.60 under non-base variations
  (fresh-sampled candidate firms, or larger b/beta, or agent loyalty lambda>0 — all of which
  Axtell's own tables show increase concentration), but reaching it that way would abandon the
  base case, which the discipline forbids. We report the faithful base case's honest number.

- **P3 (Laplace growth) is an honest MISS on the kurtosis threshold, with both qualitative
  signatures present.** Pooled log-growth is **leptokurtic** (excess kurtosis +0.59 > 0:
  heavier-than-Gaussian tails, a positive tent-ward departure from the parabola), and the
  **Stanley scaling holds directionally** — growth-rate volatility *decreases* with firm size
  (sigma-vs-size log-log slope -0.078 < 0; Axtell's empirical gamma ~ 0.17). But the peak is
  not Laplace-*strength* (~3) at the locked, well-sampled gap; the kurtosis is also highly
  sensitive to the measurement gap (it is not robustly > 1.5 at any faithful gap with adequate
  sampling), so we do not chase a gap that crosses 1.5 — that would be metric-tuning. The
  central Axtell-Stanley claim (growth is fatter-tailed than Gaussian and volatility falls
  with size) is qualitatively reproduced; the strong-Laplace quantitative bar is not met.

**Bottom line:** the reproduction cleanly delivers the central Axtell result — a **Zipf
(power-law) firm-size distribution emerging from endogenous firm formation with no built-in
scale** (P1, slope -1.28, on the paper's own number) — and exhibits the *correct sign* of the
other two stylized facts (strong right-skew; leptokurtic growth with size-declining
volatility). It falls short of the locked *quantitative* bars for extreme inequality (Gini
0.47 vs 0.60) and Laplace-strength growth kurtosis (0.59 vs 1.5), which we report honestly as
MISSes rather than reaching them via non-base-case variations that the faithfulness discipline
forbids.

## Source

Axtell, R. (1999). *The Emergence of Firms in a Population of Agents: Local Increasing Returns,
Unstable Nash Equilibria, and Power Law Size Distributions.* CSED Working Paper No. 3,
Brookings Institution / Santa Fe Institute. See also Axtell, R. (2001), *Zipf Distribution of
U.S. Firm Sizes*, Science 293:1818 (doi:10.1126/science.1062081); and Stanley, M.H.R. et al.
(1996), *Scaling behaviour in the growth of companies*, Nature 379:804 (doi:10.1038/379804a0).

Scope: a faithful reproduction of a published synthetic agent-based model; no real-world data.
The contribution is whether the harness + locked-prediction discipline reproduce the Zipf
firm-size power law, extreme size inequality, and tent-shaped growth from endogenous firm
formation — and would catch an artifact.
