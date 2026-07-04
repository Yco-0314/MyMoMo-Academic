# Price (1976) Cumulative-Advantage Citation Model — FINDINGS

**Status: 2/3 locked clauses REPRO; P1 is an honest MISS on ONE of its three
conjuncts** — the locked `k_max ∈ [40, 400]` band, which was calibrated for a small
network but is applied here at the locked `N ≥ 50,000`, where the hub is far larger
(`k_max ≈ 2,700`). The two *mechanistic* signatures inside P1 — constant out-degree and a
huge in/out variance ratio — pass decisively, as do P2 and P3. Genuine (mildly)
agent-based, **network-generation** reproduction on `abm_auto._platform`. Predictions were
locked BEFORE running (`PREDICTIONS-locked.md`); the config below was fixed before the run
and was NOT tuned.

## What was built

A growing **directed** citation graph. Papers arrive one at a time; each new
`PaperAgent` emits **exactly `m = 3` out-edges** (citations) to EXISTING (older) papers
only, choosing each target `j` with probability ∝ (`in-degree k_j + a`), with the Price
additive constant `a = 1`. Only **in-degree** (citation count) grows by cumulative
advantage; every non-seed paper's out-degree is fixed at `m` forever, and edges point only
backward in time, so the graph is a **DAG**. This is the FIRST scale-free / preferential-
attachment model (de Solla Price 1965/1976), predating Barabási–Albert by three decades.

Cumulative-advantage sampling is Newman's O(1) trick: a running **target list** in which
node `j` appears once per received citation plus `a` times for the additive constant, so a
uniform pick is exactly a draw ∝ (`k_j + a`). Growing to `N = 100,000` takes ~1 s. The
model is deterministic given a seed (single seeded `model.rng`).

The **contrast run** (`m = 1, a = 1`) has analytic exponent `γ = 2 + a/m = 3` — degenerate
with BA — and is used ONLY to demonstrate the `a/m` tunability of the tail (it is *not* the
main claim; `m ≥ 2` is required for the discriminating `γ < 3` regime).

### Distinctness from Barabási–Albert (why this is a separate reproduction)

| Property | Price (this model) | Barabási–Albert |
|---|---|---|
| Edges | **directed** (citation DAG) | undirected |
| Out-degree | **exactly `m`** (never grows) | min degree `m`, degree = in+out |
| Additive constant `a` | **yes** — tunes `γ = 2 + a/m` | none |
| Never-cited mass `p₀` | **`(m+a)/(2m+a) = 4/7 ≈ 0.571`** | **0** |
| Tail exponent `γ` | **tunable `< 3`** (2.33 at m=3,a=1) | fixed `≈ 3` |

A BA rerun fails P1 (undirected), P2 (`p₀ = 0`), and the `γ < 3` half of P3.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| out-edges per paper `m` | 3 |
| additive constant `a` | 1 |
| uncited seed papers | 20 |
| `N` (P1/P2 structural) | 50,000 |
| `N` (P3 tail) | 100,000 |
| RNG seeds (averaged) | 0, 1, 2 |
| contrast run | `m = 1, a = 1` (analytic γ = 3) |
| tail fit | CSN discrete-MLE, **KS-selected** `k_min` |

## Results (over seeds 0,1,2)

| Signature | Measured | Analytic / band |
|---|---|---|
| non-seed out-degree all `== m`, var ≈ 0 | **True, var = 0** | constant out-degree |
| in-degree max `k_max` (N=50k) | **≈ 1,979 – 3,381** (mean ≈ 2,734) | locked band **[40, 400]** |
| `Var(in)/Var(out)` | **≈ 2.3×10⁵ – 2.7×10⁵** | need `> 50` |
| zero-in-degree fraction `p₀` | **0.570 – 0.572** | band [0.52, 0.62]; analytic **0.571** |
| `γ̂` at m=3 (N=100k, KS `k_min`) | **≈ 2.20 – 2.22** (mean ≈ 2.21) | band [2.1, 2.9]; analytic **2.33** |
| `γ̂` at m=1 contrast | **≈ 2.63 – 2.89** (mean ≈ 2.74) | analytic **3.0**; must exceed m=3 γ̂ |

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Directed DAG + constant out-degree | out-deg `==m` var≈0 **AND** `k_max∈[40,400]` **AND** `Var(in)/Var(out)>50` | out-deg exact, var-ratio ≈ 2.6×10⁵, but **`k_max ≈ 2,734`** | **MISS** (k_max band) |
| **P2** | Large never-cited mass | `p₀ ∈ [0.52, 0.62]` | **0.571** | **REPRO** |
| **P3** | Tunable heavy tail `γ < 3` | m=3 `γ̂∈[2.1,2.9]` **AND** `<3` **AND** m=1 contrast higher | **2.21**, contrast **2.74** (gap 0.53) | **REPRO** |

## Honest interpretation

- **The cumulative-advantage mechanism reproduces cleanly and is unambiguously distinct
  from BA.** The two structural claims that separate Price from every undirected
  preferential-attachment model both hold at full strength: out-degree is a hard constant
  `m` (variance exactly 0 among non-seed papers — a paper's reference list never changes),
  while in-degree is heavy-tailed with an in/out variance ratio of order 10⁵. That
  directed asymmetry is the essence of a citation DAG and BA cannot produce it.

- **P2 lands on the analytic value almost exactly.** The never-cited fraction is
  `p₀ = 0.571`, matching the closed-form `(m+a)/(2m+a) = 4/7` to three decimals across all
  seeds. A majority of papers are cited zero times — a signature BA structurally cannot
  reproduce (`p₀ = 0` there). This is the strongest single confirmation of the mechanism.

- **P3 confirms the tunable sub-cubic tail.** The KS-selected discrete-MLE exponent is
  `γ̂ ≈ 2.21` at `m = 3` — comfortably inside the locked `[2.1, 2.9]` band and decisively
  below 3 — and the `m = 1` contrast rises to `γ̂ ≈ 2.74`, a gap of ~0.5 that directly
  exhibits the `γ = 2 + a/m` tunability (the whole point that distinguishes Price from the
  fixed-`γ = 3` BA model). The measured `γ̂` sits ~0.12 below the analytic 2.33; this is the
  expected finite-size **downward** pull of the KS estimator on a truncated tail (the band
  was locked wide precisely to absorb finite-size bias in either direction), not a defect.

- **P1 is an honest MISS on its `k_max` sub-band, and it is a MISS in the estimator, not
  the mechanism.** Two of P1's three conjuncts pass overwhelmingly (constant out-degree;
  variance ratio ~5,000× the `>50` bar). The failing conjunct is the locked band
  `k_max ∈ [40, 400]`. At the locked network sizes (`N ≥ 50,000`), the largest hub reaches
  `k_max ≈ 2,700` — roughly 7× above the band's ceiling. This is a *tension inside the
  lock itself*: the `[40, 400]` band corresponds to `N ≈ 1,000–2,000` (measured `k_max` is
  ~150 at N=1k, ~250 at N=2k, and grows like `N^{1/(γ−1)}`), whereas the lock's body and the
  P1 clause both mandate `N ≥ 50,000`. Held to `N ≥ 50k` as written, the band is falsified —
  and the discipline forbids shrinking `N` to 1,000 to slip under 400, since the P1 clause
  pins `N ≥ 50k`. So we report MISS. Note the direction: `k_max` overshoots the band, i.e.
  the hub is *larger* and the tail *heavier* than the band anticipated — the failure is the
  band being too tight for the mandated `N`, not the model under-producing hubs. The `>20·m`
  lower rationale (60) is satisfied ~45× over.

**Bottom line:** the reproduction demonstrates the mechanistic core of the first
cumulative-advantage model — a directed citation DAG with constant out-degree, a majority
never-cited mass at the analytic `4/7`, and a tunable sub-cubic tail (`γ̂ ≈ 2.2`, rising
toward 3 as `a/m` rises) — cleanly distinct from Barabási–Albert. It reports the one locked
sub-band it exceeds (`k_max`) honestly as a MISS: the hub grows *past* the band's ceiling
at the mandated network size, a lock-internal calibration mismatch rather than a failure of
the mechanism.

## Source

Price, D. J. de Solla (1976). *A general theory of bibliometric and other cumulative
advantage processes.* Journal of the American Society for Information Science
27(5):292–306. doi:10.1002/asi.4630270505. (Mechanism from de Solla Price 1965, *Networks
of scientific papers*, Science 149:510–515; master-equation derivation of `γ = 2 + a/m` in
Newman 2010, *Networks: An Introduction*, ch. 14. Tail fit: Clauset, Shalizi & Newman 2009,
*Power-law distributions in empirical data*, SIAM Review 51:661–703.)

Scope: a faithful **network-generation** reproduction of a published synthetic model; no
real-world data. The contribution is whether the harness + locked-prediction discipline
reproduce the first cumulative-advantage network (directed DAG, large never-cited mass,
tunable `γ < 3`), keep it distinct from BA, and would catch an artifact.
