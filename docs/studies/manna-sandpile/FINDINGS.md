# Manna Stochastic Sandpile (Manna 1991) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Self-organized-criticality (SOC) reproduction.
**Framing: CA (disclosed)** — this is a stochastic *cellular automaton*, not an
agent-stepping ABM. There are no agents that perceive, decide, and act; no scheduler over
an agent roster; no per-agent step. It is a stochastic toppling rule applied to a grid of
integer heights until the grid is stable, disclosed exactly as the `btw_sandpile` and
`oslo_ricepile` reproductions disclose the same. The lock-first + honest-verdict + L3-bundle
discipline still fully applies.

Predictions were locked BEFORE running (`PREDICTIONS-locked.md`, committed 2026-07-02). The
config below was fixed before the run; **nothing was tuned to make a clause pass.** The fit
cutoff `s_min = 1` was declared before grading and the whole `s_min` sweep is reported as a
diagnostic (below) so a reviewer can see the exponent is not cherry-picked.

## What was built

An `L x L` grid of integer heights (grains per cell), `L = 64`, with an **open boundary**
(grains that leave the lattice are lost — the dissipation that lets the driven pile reach a
steady state). The dynamics:

- **Drive:** add one grain at a uniformly random cell, then relax.
- **Topple (relaxation):** a cell is **critical** when its height `>= 2`. A critical cell
  loses exactly 2 grains, and each of those **2 grains is sent to an INDEPENDENTLY,
  uniformly randomly chosen nearest neighbour** (von-Neumann 4-neighbourhood: up / down /
  left / right). The two grains are drawn separately, so they may land on the same neighbour
  or on two different ones; a grain aimed off the lattice edge is lost. Relaxation repeats
  (synchronous sweeps: all currently-critical cells topple together) until no cell is
  critical.
- **Avalanche size `s`** = the total number of individual topplings triggered by that one
  added grain (`s = 0` if it caused no toppling).

**The distinctive rule** — and the whole point of the Manna model — is the *stochastic*
two-grain redistribution. The deterministic BTW sandpile topples at threshold 4 by sending
one grain to each of its 4 fixed neighbours; the Manna model topples at threshold 2 and
scatters its 2 grains to two *randomly chosen* neighbours. That randomness puts it in the
separate **Manna (conserved directed-percolation) universality class**, distinct from
deterministic BTW and from the non-conservative Olami-Feder-Christensen earthquake model.

**Determinism.** The whole run is reproducible from a single integer seed: one
`numpy.random.default_rng(seed)` draws every drop location *and* every grain-scatter
direction. NumPy vectorises the toppling sweep for speed; the result is the canonical
stochastic-CA outcome for that seed. (Faithfulness + determinism tests in
`tests/classics/test_manna_sandpile.py`, 18 tests, all passing.)

## Run configuration (fixed before the run)

| quantity | value |
|---|---|
| lattice | `L = 64`, open boundary |
| threshold | height `>= 2` (Manna two-state) |
| redistribution | stochastic: 2 grains, each to an independently-random von-Neumann neighbour |
| transient discarded | `L*L*25 = 102,400` grains (lock requires `>= L*L*20`) |
| avalanches recorded | `40,000` at stationarity (lock requires `>= 10^4`) |
| seed | `0` |
| tau fit | exact discrete power-law MLE (Hurwitz-zeta likelihood; Clauset, Shalizi & Newman 2009), Brent root-find on the score, lower cutoff `s_min = 1` |

## Results (actual run numbers)

- **Fitted exponent:** `tau = 1.2620 +/- 0.0016` at `s_min = 1` (`n_tail = 28,136` nonzero
  avalanches). Manna's 2D value is `~1.27` — this lands essentially on it.
- **`s_min` sweep (diagnostic, not graded):**

  | `s_min` | `tau` | stderr | `n_tail` |
  |---:|---:|---:|---:|
  | 1  | 1.2620 | 0.0016 | 28,136 |
  | 2  | 1.3192 | 0.0020 | 25,922 |
  | 4  | 1.3589 | 0.0024 | 22,064 |
  | 8  | 1.3965 | 0.0029 | 18,313 |
  | 16 | 1.4353 | 0.0036 | 14,883 |

  The exponent drifts up slowly with `s_min` (a known finite-size / cutoff effect on a
  bounded `L = 64` lattice — the upper cutoff of the scaling window pulls the local slope up
  as `s_min` rises). `s_min = 1`, using the whole nonzero scaling region, sits closest to the
  literature `1.27`; `s_min = 1, 2, 4` all fall inside the locked `[1.20, 1.40]` band, and
  the grading value was fixed to `s_min = 1` before the run.
- **Heavy tail:** nonzero avalanches span **4.57 decades** (`1 .. 36,961`); median nonzero
  size `= 19`; **max / median = 1,945x**.
- **Occupancy:** stationary mean occupancy `= 0.6994` grains/cell (final `0.7102`) — a
  finite, stable active density, neither frozen (`~2`) nor drained (`~0`).
- **Zero avalanches:** `11,864 / 40,000` drops (29.7%) caused no toppling; `28,136` nonzero.
- The log-binned size histogram is a clean straight power-law over ~4 decades with the
  expected upper cutoff at the lattice scale (see `results.json`,
  `size_histogram_log_binned`).

## Per-clause verdicts (honest)

| clause | prediction | pass clause | measured | verdict |
|---|---|---|---|---|
| **P1** | Manna-class avalanche exponent | discrete-MLE `tau` in `[1.20, 1.40]` (Manna 2D `~1.27`) | `tau = 1.2620` (`s_min = 1`, `n_tail = 28,136`) | **REPRO** |
| **P2** | heavy-tailed, not exponential | nonzero sizes span `>= 2` decades AND max `>= 100x` median nonzero | `4.57` decades; max/median `= 1,945x` | **REPRO** |
| **P3** | finite stationary active density | stationary mean occupancy in `[0.6, 0.95]` | `0.6994` grains/cell | **REPRO** |

**P1 — REPRO.** The discrete-MLE tail exponent is `1.262`, inside `[1.20, 1.40]` and within
`~0.7%` of Manna's `1.27`. This is the load-bearing SOC + universality-class signature: the
stochastic sandpile produces a power-law avalanche distribution with the Manna exponent, not
the deterministic-BTW exponent.

**P2 — REPRO, comfortably.** The distribution is emphatically heavy-tailed: `4.57` decades
of nonzero sizes and a max avalanche `1,945x` the median — orders of magnitude past the
locked `2`-decade / `100x` bars. Not remotely exponential.

**P3 — REPRO.** The lock flagged occupancy as the honest MISS-risk clause; the measured
stationary occupancy `0.6994` sits comfortably inside `[0.6, 0.95]`. The driven pile
self-organises to a genuine critical steady state with a finite active density — open-boundary
dissipation balances the drive, so the lattice is neither frozen at saturation nor drained
empty.

## Honest caveats

- **`tau` depends on the fit window.** The `s_min` sweep shows the local slope rising from
  `1.26` (`s_min = 1`) to `1.44` (`s_min = 16`). This is expected on a finite `L = 64`
  lattice — the finite upper cutoff biases the fitted slope upward as the lower cutoff
  climbs. We fixed `s_min = 1` *before* grading (the full scaling region, closest to the
  literature value); a reviewer can read the whole sweep from `results.json` and see the
  band-pass is not an artefact of a hand-picked cutoff. A much larger `L` would flatten this
  drift but cost far more runtime.
- **Single seed, single `L`.** One seed (`0`) at `L = 64` with 40k avalanches. The verdict is
  about whether the harness reproduces the Manna SOC power-law and would catch an artefact
  (a non-power-law, the wrong exponent, or a frozen/drained lattice), not a finite-size
  scaling study of `tau(L)`.
- **CA, not ABM (disclosed).** As stated up top and in the module docstring and bundle
  `extra.framing = "CA (disclosed)"`: no agents, no scheduler, no per-agent decisions — a
  stochastic toppling rule on a grid of heights.

## Reproduce

```
.venv/bin/python -m pytest tests/classics/test_manna_sandpile.py -q
PYTHONPATH=. .venv/bin/python examples/repro_manna_sandpile/run.py
```

The runner regenerates `results.json` and `verdict-bundle.json`; the L3 bundle
content-addresses this `FINDINGS.md`, the locked predictions, and the design spec, so a
reviewer can diff the regenerated bundle against the committed one.
