# Watts–Strogatz Small-World — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).

## This is a NETWORK-GENERATION reproduction, not an agent-stepping ABM

State this plainly: the Watts–Strogatz model is a **network-generation procedure**, not
an agent-based model. There are **no agents stepping** on the neutral platform here.
We build a graph from a fixed rule (ring lattice → rewire each edge with probability p)
and measure two structural quantities of the resulting graph. The contribution is a
faithful *structural* reproduction of the small-world result, held to the same
lock-first → honest-verdict → L3-bundle discipline as the genuinely agent-based
reproductions in this suite. We do **not** claim it as agent-based.

Code: `abm_auto/classics/watts_strogatz.py`; experiment:
`examples/repro_watts_strogatz/run.py`. The canonical WS rewiring rule is provided by
networkx `watts_strogatz_graph(n, k, p, seed)` (the reference generator).

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| generator | networkx `watts_strogatz_graph(n, k, p, seed)` (ring lattice → per-edge rewire) |
| n (nodes) | **1000** |
| k (degree, k/2 per side) | **10** |
| p-grid (8 pts, log-spaced) | **0, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0** |
| seeds per p | **10** (seeds 0..9) |
| L(p) | average shortest-path length on the **largest connected component** |
| C(p) | networkx `average_clustering` (mean local clustering over nodes) |
| normalisation | L/L0 and C/C0 vs the p=0 lattice values L0, C0 |

The p=0 lattice is seed-independent (no rewiring), so L0, C0 are exact. The lattice
clustering matches the analytic `C_lattice = 3(k−2)/(4(k−1)) = 27/36 = 0.6667` exactly.
Every metric is a pure function of (n, k, p, seed); the run is deterministic and the
table below is reproducible. Sweep runtime ≈ 44 s.

## Measured L(p)/L0 and C(p)/C0 (mean over 10 seeds; ± = population stdev)

| p | L(p) | **L/L0** | C(p) | **C/C0** | L_std | C_std | giant frac |
|---|---|---|---|---|---|---|---|
| 0.0   | 50.4505 | **1.0000** | 0.6667 | **1.0000** | 0.000 | 0.000 | 1.0000 |
| 0.001 | 27.3057 | **0.5412** | 0.6648 | **0.9972** | 4.516 | 0.001 | 1.0000 |
| 0.003 | 14.9316 | **0.2960** | 0.6604 | **0.9906** | 1.580 | 0.002 | 1.0000 |
| 0.01  | 8.7157  | **0.1728** | 0.6454 | **0.9681** | 0.700 | 0.004 | 1.0000 |
| 0.03  | 6.0105  | **0.1191** | 0.6089 | **0.9134** | 0.144 | 0.004 | 1.0000 |
| 0.1   | 4.4194  | **0.0876** | 0.4872 | **0.7307** | 0.032 | 0.006 | 1.0000 |
| 0.3   | 3.6084  | **0.0715** | 0.2352 | **0.3528** | 0.011 | 0.005 | 1.0000 |
| 1.0   | 3.2679  | **0.0648** | 0.0087 | **0.0131** | 0.002 | 0.001 | 1.0000 |

L0 (lattice) = 50.4505, C0 (lattice) = 0.6667; L1 (random) = 3.2679, C1 (random) = 0.0087.
The graph stays fully connected at every p in the grid (giant fraction = 1.0000), so L is
the path length of the whole graph at all sampled p — the giant-component convention only
ever matters at smaller p / lower k.

**Small-world window (L/L0 < 0.5 AND C/C0 > 0.5, restricted to p∈[0.001,0.1]):
p ∈ {0.003, 0.01, 0.03, 0.1}.** Inside this window the path length has already
collapsed (down to 9–30% of the lattice) while clustering is still 73–99% of the
lattice — the defining small-world regime.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Endpoints: L(0)≫L(1) AND C(0)≫C(1) (each ratio ≥ 5×) | **REPRO** | L0/L1 = **15.44×**, C0/C1 = **76.46×** (both ≥ 5) |
| P2 | Small-world window: ∃ p∈[0.001,0.1] with L/L0<0.5 AND C/C0>0.5 | **REPRO** | window p ∈ **{0.003, 0.01, 0.03, 0.1}** (4 grid points) |
| P3 | L collapses faster than C (L/L0 crosses 0.5 at smaller p than C/C0) | **REPRO** | p(L/L0<0.5) = **0.003** < p(C/C0<0.5) = **0.3** |

**3/3 locked clauses REPRO.** The reproduction recovers the central Watts–Strogatz
result: a broad intermediate range of rewiring p where a handful of long-range shortcuts
have already collapsed the characteristic path length toward the random-graph value while
local clustering remains essentially at lattice levels — a small world.

## Honest caveats

- **Network-generation, not agent-based** (restated): no agents step here; this is a
  structural reproduction of a network-science result. Do not cite it as evidence the
  agent platform reproduces small-worlds — it does not exercise the platform at all.
- **networkx is the reference generator, not an independent implementation.** We use
  `watts_strogatz_graph` as the canonical WS rule and networkx's own
  `average_shortest_path_length` / `average_clustering` as the metrics. This is a
  faithful reproduction of the *published result*, not a cross-implementation check; a
  bug shared with networkx would not be caught. The faithful-construction unit tests
  (k-regularity, n·k/2 edges, the analytic lattice clustering `3(k−2)/(4(k−1))`, the
  giant-component path-length convention, determinism) anchor that the construction and
  metrics are the intended ones.
- **Boundaries are grid-resolution-limited.** P3's half-drop crossings are read off the
  8-point log grid, so each is accurate only to the next grid step. L/L0 is already
  0.5412 at p=0.001 and 0.2960 at p=0.003, so the true L half-drop sits just above
  p=0.001; C/C0 is still 0.7307 at p=0.1 and 0.3528 at p=0.3, so the true C half-drop
  sits between p=0.1 and p=0.3. The ordering (L crosses first, by ~two decades of p) is
  robust to the grid; we do **not** refine the grid to sharpen the crossings (that would
  be post-hoc tuning).
- **p=0.001 L variance is large** (L_std = 4.516, ~17% of the mean). At the smallest
  nonzero p only ~5 of the 5000 edges are rewired in expectation, so whether any
  long-range shortcut lands — and where — swings L a lot across seeds. This is expected
  WS behaviour at the very onset; the window predictions all live at p ≥ 0.003 where the
  spread is much smaller, and we average over 10 fixed seeds and report the stdev rather
  than picking a favourable seed.
- **No config compromise.** Full n=1000, k=10, 10 seeds/p (no reduction). L is tractable
  at n=1000.
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed together with the code, so it points to the parent
  commit). Reproduction integrity is anchored on the content-addressed **sha256** of the
  docs/data artifacts (all `replay: strong`), not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* network model — no
  real-world data. The contribution is that the harness + lock-first discipline reproduce
  the small-world window and would surface an artifact (a refutation gate, not a truth
  certificate).
