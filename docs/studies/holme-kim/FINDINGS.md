# Holme-Kim Growing Scale-Free with Tunable Clustering (2002) — FINDINGS

**Status: 2/3 locked clauses REPRO; P3 is an honest MISS driven by a single marginal
sub-clause (L at p=1, N=1000 = 4.15 vs the locked <=4.0 bar).** Network-generation
reproduction (disclosed) on `abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT tuned to
hit any threshold. Tier: **refutation** (never "verified").

## What was built

The genuine Holme-Kim (2002) growing network: Barabasi-Albert preferential attachment
(PA) **plus** a triad-formation step. The network is grown one node at a time; each
arriving `NodeAgent` makes `m` attachment decisions on the neutral platform:

- **Edge 1** is a pure PA draw (degree-weighted, without replacement) that fixes the
  arrival's **hub**.
- **Edges 2..m**: with probability `p`, a **triad-formation** step -- attach to a random
  not-yet-linked **neighbour of that same hub**, closing a triangle `new-hub-neighbour`;
  otherwise (prob `1-p`, or if the hub has no eligible neighbour) another PA draw.

`p = 0` recovers plain BA (vanishing clustering); raising `p` dials the clustering up.
This is the classic Holme-Kim algorithm -- the same rule networkx's
`powerlaw_cluster_graph(n, m, p)` implements. The transitivity **formula** matches
networkx exactly, and our clustering is statistically indistinguishable from networkx at
low/mid `p`; the two differ only by a disclosed modest amount at `p = 1` (see below).

Metrics (all fixed before running, none tuned):

- **Clustering (P1, graded):** the **average local clustering coefficient** `<C>` -- the
  quantity Holme & Kim actually report and plot. The hub-weighted **global transitivity**
  is carried as a documented secondary; it is systematically lower and is NOT graded.
- **Degree tail (P2):** the discrete power-law MLE of Clauset-Shalizi-Newman (2009) with
  `kmin = m + 1` fixed on theoretical grounds (first degree above the `k = m` birth spike)
  -- the identical estimator + kmin rule used in the Barabasi-Albert reproduction.
- **Path length (P3):** the mean shortest-path length `L` from exact BFS over a random
  sample of source nodes (an unbiased large-N estimator on these connected graphs).

Deterministic given a seed (single seeded `model.rng`). `N = 10000` is fast.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| m | 3 |
| N (clustering + degree-tail sweep) | 5000 |
| p grid | 0.0, 0.15, 0.45, 1.0 |
| seeds (sweep) | 0,1,2,3,4 (5 seeds) |
| path-length sizes | N = 1000 and N = 5000 |
| path-length p | 0.0, 1.0 |
| path-length seeds / BFS sources | 0,1,2 / 100 |
| degree-tail fit | discrete-MLE, kmin = m+1 = 4 |

## Results (mean over seeds; raw)

**Clustering sweep (N = 5000, 5 seeds):**

| p | average local <C> (graded) | global transitivity (secondary) |
|---|---|---|
| 0.00 | **0.0095** | 0.0053 |
| 0.15 | 0.0853 | 0.0227 |
| 0.45 | 0.2460 | 0.0580 |
| 1.00 | **0.6172** | 0.1463 |

Ratio `<C>(p=1)/<C>(p=0)` ~= **65x**; strictly monotone in p.

**Degree tail (N = 5000, 5 seeds, kmin = 4):** gamma(p=0) = **2.676**, gamma(p=1) =
**2.683**, `|d-gamma|` = **0.007**.

**Path length (BFS-sampled):**

| p | L(N=1000) | L(N=5000) | growth |
|---|---|---|---|
| 0.0 | 3.475 | 4.016 | 0.54 |
| 1.0 | **4.154** | 4.936 | 0.78 |

## Verdicts

| # | Clause (locked) | Measured | Verdict |
|---|---|---|---|
| **P1** | <C>(p=1) >= 0.40 AND ratio >= 5 AND monotone | <C>(p=1)=**0.617**, ratio~=**65x**, monotone ok | **REPRO** |
| **P2** | gamma(0),gamma(1) in [2.0,3.5] AND \|d-gamma\| <= 0.4 | 2.676 / 2.683, \|d-gamma\|=**0.007** | **REPRO** |
| **P3** | L(1000) in [3,4] & L(5000) in [3.5,5] for p in {0,1}, growth <= ~1 | p=0 all pass; **L(p=1,N=1000)=4.154 > 4.0** | **MISS** |

## Honest interpretation

- **Tunable clustering is reproduced cleanly (P1 REPRO).** The triad knob dials the
  average local clustering from **0.0095 (plain BA -- vanishing, as expected for a grown
  scale-free network) to 0.617 at p = 1** -- a ~65x swing, strictly monotone across the
  grid, and comfortably above the locked 0.40 bar. This is the central Holme-Kim claim:
  clustering becomes a free parameter that BA cannot touch. *Metric note (disclosed):* P1
  is graded on the **average local clustering**, the quantity Holme & Kim report and the
  one that reaches ~0.6 for m = 3; the hub-weighted **global transitivity** is far lower
  (0.146 at p = 1) and is carried only as a secondary. Reading P1's `C` as transitivity
  would falsify the magnitude clause -- that is a known property of the transitivity metric
  on these graphs, not of the model, and it is why the local coefficient is the faithful
  choice.

- **The scale-free tail is preserved and independent of clustering (P2 REPRO).** The MLE
  exponent is gamma ~= 2.68 at both p = 0 and p = 1, both inside [2.0, 3.5] and near the
  Holme-Kim value, with `|d-gamma| = 0.007` -- the triad step reshapes local clustering
  without perturbing the degree tail. This is the combination BA cannot produce: high,
  tunable clustering **with** an intact gamma ~= 2.6-3 tail.

- **Small-world is *mostly* preserved, but P3 is an honest MISS on one marginal
  sub-clause.** For p = 0 all four path-length bounds pass. For p = 1 the path length is
  short and grows only slowly with N (L: 4.15 -> 4.94 from N = 1000 -> 5000, growth 0.78
  <= 1), so the *qualitative* small-world property clearly holds. But the locked window
  `L(N=1000) in [3, 4]` is **breached at p = 1: L = 4.154 > 4.0**. The triad step, by
  spending edges on local triangles instead of long-range PA edges, lengthens shortest
  paths just enough to push the N = 1000 mean past 4.0. This is a real, robust effect (not
  a seed artifact: per-seed L clusters tightly around 4.0-4.3), and because the locked
  clause is a conjunction over all four (size x p) checks, one breach makes the whole
  clause a **MISS**. We report it as such rather than widen the window. Every other P3
  check -- L(p=0) at both sizes, L(p=1, N=5000), and both growth rates -- passes.

**Bottom line:** the reproduction cleanly demonstrates the two defining Holme-Kim results
-- **clustering is a tunable knob (<C>: 0.01 -> 0.62)** and **the scale-free exponent is
preserved and clustering-independent (gamma ~= 2.68, |d-gamma| = 0.007)** -- the
BA-impossible combination. It reports honestly that the strict small-world *window* is
marginally exceeded at p = 1, N = 1000 (L = 4.15 vs the locked <= 4.0), so P3 is a MISS by
0.15 on a single sub-clause even though the path length remains short and log-growing.

## Faithfulness cross-check

Our native implementation's global transitivity matches `networkx.transitivity` **exactly**
on a grown graph, and its clustering p-sweep matches `networkx.powerlaw_cluster_graph`
(same classic algorithm) at low/mid p; the two differ by a disclosed ~0.05 at p = 1
(ours ~0.16 vs nx ~0.12 transitivity at N = 2000) from a faithful-but-not-identical
PA-sampling choice (exact degree-weighting from a connected (m+1)-clique seed vs a
repeated-node set-subset from m isolated nodes). The BFS mean-path estimator matches
`networkx.average_shortest_path_length` exactly on a small connected graph. These pins live
in `tests/classics/test_holme_kim.py`.

## Source

Holme, P. & Kim, B.J. (2002). *Growing scale-free networks with tunable clustering.*
Physical Review E 65:026107. doi:10.1103/PhysRevE.65.026107.

Scope: a faithful reproduction of a published synthetic network-generation model; no
real-world data. Framing is **network-generation (disclosed)**: the network is grown one
node at a time, each arrival an agent making `m` BA+triad attachment decisions, and the
outcome is the emergent structure (clustering, degree tail, path length), not agent
trajectories. The contribution is whether the harness + locked-prediction discipline
reproduce tunable clustering with a preserved scale-free tail and small-world path length --
and would catch an artifact, including reporting an honest MISS where a locked window is
marginally exceeded.
