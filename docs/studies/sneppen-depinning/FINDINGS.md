# Sneppen Interface Depinning (1992, model "A") — FINDINGS

**Status: 2/3 locked clauses REPRO, 1 honest MISS (P3).** Extremal-dynamics / SOC
reproduction — **framing CA (disclosed)**: there are no stepping agents; one "advance"
selects the GLOBAL minimum-pinning column and raises it, then enforces a bounded-slope
constraint on its neighbours (a centralized, model-orchestrated operation, exactly like the
BTW-sandpile and Bak-Sneppen reproductions). Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and **nothing was tuned
to make a clause pass**. The falsified clause (P3) is reported as a MISS.

## What was built

A 1D **self-affine interface** in a **quenched random medium** (Sneppen model A). The state
is an integer height profile `h[x]` over `L` **periodic** columns, plus a current random
pinning value `eta[x] ~ U[0, 1)` on each column — the random pinning force at that column's
interface front.

One **extremal advance** is:

1. find the column `x*` with the **global minimum** pinning `eta` (the weakest-pinned front
   point);
2. **advance** it: `h[x*] += 1` and **redraw** `eta[x*] ~ U[0,1)` (a fresh quenched value at
   the new front position);
3. **enforce the bounded-slope constraint** `|h[x] - h[x±1]| <= 1`: if the advance leaves a
   periodic neighbour lagging by 2, pull that neighbour up too (`h += 1`, redraw its `eta`)
   and **propagate** until every bond satisfies the constraint. The forced pull-ups are part
   of the same advance — they are the local relaxation the extremal move triggers.

From a flat start the width `W = std(h)` roughens and then **saturates** at a size-dependent
`W_sat(L)`; the acted-on pinning value self-organizes to a critical ceiling. The model is
deterministic given a seed (one `numpy.random.default_rng(seed)` draws every pinning value).

## Locked config (FIXED before the run; nothing tuned)

| Param | Value |
|---|---|
| L sweep | {32, 64, 128, 256} (periodic) |
| advances per (L, seed) | `600 * L` (grows each size well past saturation) |
| seeds | 4 (seed_base 0) |
| transient discarded | first 50% of advances (roughening transient) |
| stationary width samples | 400 per (L, seed) |
| stationary slope snapshots | 200 per (L, seed) |
| pinning distribution | `U[0, 1)`, redrawn on advance |
| avalanche + slope L | 256 (largest size) |

## Metrics (locked)

- **P1 chi**: fit `W_sat(L) ~ L^chi` as the OLS slope of `log W_sat` vs `log L`; require
  `chi ∈ [0.5, 0.75]` AND `W_sat` monotone increasing in L.
- **P2 avalanches**: the Sneppen "signal" is the acted-on minimum pinning `eta_min` at each
  advance. The running "global-minimum threshold" is the **running maximum (record)** of that
  signal; an **avalanche = the number of advances between successive record increases** (a
  maximal run during which no new record is set), measured over the full run and pooled over
  the 4 seeds at L=256. Require the nonzero sizes to span **≥ 2 decades** AND **max ≥ 100×
  median nonzero**.
- **P3 correlation**: the nearest-neighbour spatial correlation of the interface height
  **differences** `dh[x] = h[x+1] - h[x]` (adjacent slopes), i.e. `corr(dh[x], dh[x+1])`,
  averaged over stationary snapshots. Require **< 0** (anticorrelated). A matched
  **random-deposition** baseline (drop one unit on a uniformly random column, no extremal
  rule, no slope constraint) is reported for contrast.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Self-affine roughness | `chi ∈ [0.5, 0.75]` **AND** W_sat monotone in L | **chi = 0.654** (r²=0.9997), W_sat = 2.11 → 3.40 → 5.30 → 8.25, monotone **True** | **REPRO** |
| **P2** | Scale-free avalanches | span ≥ 2 decades **AND** max ≥ 100× median nonzero | **4.97 decades**, max/median = **30968×** (max=92903, median=3, n=698) | **REPRO** |
| **P3** | Anticorrelated growth | adjacent-slope correlation **< 0** | **+0.260** (per-seed +0.261/+0.266/+0.262/+0.252) | **MISS** |

## Honest interpretation

- **P1 — the interface is self-affine with a roughness exponent in the depinning class
  (REPRO).** Across the L sweep the saturated width scales as a clean power law:
  `W_sat = 32 → 2.11`, `64 → 3.40`, `128 → 5.30`, `256 → 8.25`, monotone increasing, with a
  log-log slope **chi = 0.654** and an essentially perfect fit (r² = 0.9997). That sits
  squarely inside the locked `[0.5, 0.75]` band and right on the Sneppen depinning-class value
  (≈ 0.63). The lock flagged chi as the honest MISS-risk clause (it needs a clean sweep to
  saturation); here the sweep *did* saturate and chi landed on target — a genuine pass, not a
  near-miss.

- **P2 — extremal activity is scale-free (REPRO).** The record-run avalanche sizes span
  **~5 decades** (from 1 to 92903 advances between successive record pinning values) with a
  max **~31000×** the median nonzero size — far past the locked `≥ 2 decades` / `≥ 100×` bars,
  and consistent across seeds (per-seed decades 4.71–4.97, max/median 17140–46452). The
  self-organized extremal dynamics produce the broad, scale-free burst-size distribution the
  Sneppen "signal" is known for.

- **P3 — the anticorrelation clause is FALSIFIED; this is an honest MISS.** The locked clause
  predicted that adjacent interface-height differences are **anticorrelated** (`< 0`), with
  uncorrelated random deposition giving `≈ 0`. The measurement is the opposite: the Sneppen
  interface's adjacent slopes are **positively correlated, +0.260** (tightly, across all four
  seeds). The physics is unambiguous once measured — a self-affine interface with a `|dh| ≤ 1`
  slope constraint is **smooth**: a rising region tends to keep rising, so neighbouring slopes
  share sign and correlate **positively**. It is *faceted/anticorrelated* growth (alternating
  up/down slopes) that would give a negative correlation, and the Sneppen depinning interface
  is not that. Moreover the locked baseline claim is also wrong in this metric: **random
  deposition gives -0.471**, not `≈ 0` — because `dh[x]` and `dh[x+1]` share the term `h[x+1]`
  with opposite sign, random deposition is *mechanically* anticorrelated (≈ -1/2). So on this
  specific metric the lock had the sign backwards for both the model (predicted `<0`, measured
  `+0.26`) and the baseline (predicted `≈0`, measured `-0.47`). We report **MISS** rather than
  redefining the metric to pass.

  What the data *does* show (reported as a cross-check, not scored) is a real, strong spatial
  correlation signature that distinguishes Sneppen from random deposition — just with the
  opposite sign to the locked clause: the extremal interface's adjacent slopes are strongly
  **positively** correlated (+0.26) while random deposition is **negatively** correlated
  (-0.47). The distinction between self-organized depinning and uncorrelated deposition is
  genuine and large; the locked clause simply predicted the wrong sign for it.

**Bottom line.** The reproduction cleanly recovers the two robust Sneppen signatures — a
self-affine roughness exponent chi ≈ 0.65 in the depinning class (P1) and a ~5-decade
scale-free extremal-avalanche distribution (P2) — while the geometry clause (P3) is an
**honest MISS**: the locked "anticorrelated adjacent slopes" prediction is falsified because a
smooth self-affine depinning interface has **positively** correlated adjacent slopes. 2/3
locked clauses REPRO; the miss is a mis-calibrated locked bar, reported as a miss, not tuned
away.

## Source

Sneppen, K. (1992). *Self-organized pinning and interface growth in a random medium.*
Physical Review Letters 69(24):3539-3542. doi:10.1103/PhysRevLett.69.3539.

Scope: a faithful reproduction of a published synthetic model; no real-world data. Framing:
**CA (disclosed)** — an extremal-dynamics / self-organized-criticality model integrated by a
centralized minimum-pinning rule with a bounded-slope constraint, not an agent-stepping ABM
(no scheduler over an agent roster, no per-agent perceive/decide/act) — disclosed exactly as
the BTW-sandpile / Bak-Sneppen reproductions disclose the same. The contribution is whether
the harness + lock-first discipline reproduce the Sneppen self-affine roughening, scale-free
extremal activity, and interface geometry, and would honestly report a falsified geometry
clause.
