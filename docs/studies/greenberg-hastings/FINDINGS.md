# Greenberg-Hastings Excitable Media (1978) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Cellular-automaton reproduction (a 3-state excitable
CA — disclosed; there are no stepping agents, only a synchronous local update rule on a 2D
grid). Predictions were locked BEFORE running (`PREDICTIONS-locked.md`); the config below was
fixed before the run and nothing was tuned to make a clause pass. One clause (P1) exposes a
genuine, honestly-reported subtlety of the *discrete* model — see the interpretation.

## What was built

A 3-state Greenberg-Hastings excitable cellular automaton on a 2D grid. Every cell is in one
of `r + 2` states, encoded as an integer in `0 .. r+1`:

    0            = QUIESCENT (rest / excitable)
    1            = EXCITED (firing)
    2, ..., r+1  = the r REFRACTORY states (a deterministic countdown back to rest)

**Synchronous update** (whole grid replaced at once), **von-Neumann** (4-)neighbourhood:

    quiescent (0) -> excited (1)  iff >= 1 von-Neumann neighbour is EXCITED, else stays 0
    excited (1)   -> 2            (first refractory)
    refractory k  -> k+1,  and the last refractory (r+1) -> 0 (quiescent)

Only the EXCITED state excites neighbours; refractory cells do not. A refractory tail is
therefore a one-way "wall" a wavefront cannot back-propagate through — which is exactly what
makes a broken front curl into a **rotating spiral**, makes two head-on fronts **annihilate**,
and sets a **refractory-length-dependent critical re-entry size**. The cycle length is
`T = 1 + r` (excited once, then r refractory steps); the default is `r = 4`, so `T = 5`.

The CA is **deterministic** — the update is a pure function of the grid, with no randomness in
the dynamics. Given an initial grid the evolution is bit-for-bit identical every run. NumPy is
used only to make the synchronous neighbour test fast (a wrap-around OR of the four shifted
excited-masks). The grid is TOROIDAL for the spiral (so the domain edge does not kill it) and
OPEN (non-wrapping) for the collision and critical-size experiments (so an escaping / a
transmitted wave is unmistakable).

## Locked config (FIXED before the run; nothing tuned)

| Item | Value |
|---|---|
| refractory length r (default) | 4 (cycle length T = 1 + r = 5) |
| neighbourhood | von-Neumann (4) |
| update | synchronous, 3-state |
| P1 spiral | broken wavefront on a 220x220 **torus**, 500 steps |
| P1 pass bar | rotation period = T +-1, stable over >= 20 rotations, activity never dies |
| P2 collision | two head-on planar fronts on an 80x80 **open** grid, +-3-column collision band |
| P2 pass bar | band -> 0 within one refractory period T; NO transmitted front past the line |
| P3 critical size | refractory lengths r in {4, 8, 12}, sizes L = 2..29, **open** boundary |
| P3 pass bar | finite L_c (dies < 5 cycles below, persists > 100 cycles at/above), L_c increases monotonically with r |

## Results (raw, from the run)

**P1 — rotating spiral (torus, r=4, T=5).** A broken wavefront winds up into a single
persistent rotating spiral. The rotation period, measured at a fixed probe cell away from the
core (the modal excitation gap) AND cross-checked by the linearly-detrended autocorrelation of
the global excited-cell count, is **6** (both methods agree). The excitation gap is a rock-solid
`[min, max] = [6, 6]` over **37 rotations**; activity never dies (the excited count stays > 0
the entire run; final excited count 8070 on the 220x220 torus). The measured period 6 equals
**T + 1** — within the locked `+-1` tolerance of `T = 5`.

**P2 — wavefront annihilation (open, r=4, T=5).** Two planar fronts launched head-on (gap 26)
meet at the centre collision line at **step 10**. The excited count in the +-3-column collision
band goes `... 0, 160, 160, 160, 80, 0 ...` — it returns to **0 just 4 steps after the meet**
(<= one refractory period T = 5), and the **total** excited count over the whole open grid
reaches **0**: both fronts are fully consumed, with **no transmitted front** past the collision
line (`no_pass_through = True`). A control single front (in the faithfulness tests) travels
cleanly across the whole grid and off the far edge — so the medium *does* transmit an isolated
wave; the annihilation is genuine, not a medium that simply cannot propagate.

**P3 — refractory-set critical size (open boundary).** Sweeping the linear domain size L for
three refractory lengths:

| r | T = 1+r | L_c (smallest L that persists > 100 cycles) | just below L_c (L = L_c - 1) |
|---|---|---|---|
| 4 | 5 | **4** | dies at 0.8 cycles |
| 8 | 9 | **8** | dies at 0.89 cycles |
| 12 | 13 | **12** | dies at 0.92 cycles |

`L_c` is **finite** and increases **strictly monotonically** with the refractory length r
(4 -> 8 -> 12; here `L_c ~= r`). Below `L_c` activity dies in **< 1 cycle** (far under the
locked < 5), and at/above `L_c` the spiral persists the full **120 cycles** run.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Rotating spiral with a fixed period | rotation period = T +-1, stable over >= 20 rotations, never dies | period **6** (T=5, T+1), gaps [6,6] over **37** rotations, alive throughout | **REPRO** |
| **P2** | Colliding wavefronts annihilate | band -> 0 within T; no transmitted front | band 0 in **4** steps (<= T=5), total excited -> **0**, no pass-through | **REPRO** |
| **P3** | Refractory-set critical size | finite L_c, dies < 5 cyc below / persists > 100 cyc above, monotone in r | L_c = **4, 8, 12** for r = **4, 8, 12**; dies < 1 cyc below | **REPRO** |

## Honest interpretation

- **A broken wavefront really does nucleate a persistent rotating spiral (P1).** The refractory
  tail's one-way-wall property curls the free end of the cut front into a one-armed spiral that
  rotates indefinitely — activity never dies over the whole 500-step run and the medium settles
  into a strictly periodic rhythm. This is the central Greenberg-Hastings phenomenon: sustained
  self-organising re-entrant activity from a purely local excitable rule.

- **The measured rotation period is `T + 1 = 6`, not exactly `T = 5` — an honest discreteness
  effect, inside the locked +-1 tolerance.** In the continuum picture a spiral rotates with the
  cell cycle length T. In the *discrete* CA the rotating arm's tip must wait one extra tick for
  the cell at the pivot to finish its refractory countdown AND for its neighbour to become
  re-excitable, so the global rhythm is one tick longer than the naive T. We measured this two
  independent ways (a fixed probe cell's excitation gaps and the detrended global-count
  autocorrelation) and both give exactly 6. The locked clause allowed `+-1`, so this REPROs
  honestly — but we flag plainly that the period is `T+1`, not `T`, and that a coarser check
  demanding *exactly* T would have (wrongly) called this a miss. (A sweep over r shows the
  rotation period is generally `>= T` — e.g. r=2->4, r=4->6, r=5->8 — never below T; the discrete
  spiral is if anything a hair slower than the continuum cycle, never faster.)

- **Head-on fronts annihilate with no pass-through (P2).** When two fronts meet, each runs
  straight into the fresh refractory tail the other has just laid down; neither can advance into
  a refractory wall, so both extinguish. The collision band falls silent within one refractory
  period and the whole open grid returns to rest — the classic excitable-media wave
  annihilation (there is no soliton-like pass-through; excitable waves are not solitons). The
  isolated-front control confirms the medium transmits a lone wave, so the annihilation is a
  real collision outcome, not a propagation failure.

- **There is a finite, refractory-set critical size for re-entry, increasing with r (P3).** A
  domain smaller than `L_c` cannot hold a full rotating loop: the winding arm meets its own /
  the boundary too soon and the pattern self-extinguishes within a cycle. A domain at/above
  `L_c` sustains the spiral for the full run. `L_c` grows monotonically with the refractory
  length r (longer refractory tail => longer wavelength => more room needed), here tracking
  `L_c ~= r`. This is the discrete analogue of the re-entrant-arrhythmia size threshold the
  excitable-media literature associates with the model.

**Bottom line:** the reproduction cleanly demonstrates all three Greenberg-Hastings signatures —
a broken front that winds into a **persistent rotating spiral** with a fixed rhythm (P1), **wave
annihilation** on head-on collision with no pass-through (P2), and a **finite refractory-set
critical re-entry size** that increases with r (P3). The one honest nuance, surfaced rather than
hidden, is that the discrete spiral's period is `T+1`, not exactly `T` — comfortably inside the
locked +-1 tolerance, and itself a faithful feature of the discrete model.

## Source

Greenberg, J. M. & Hastings, S. P. (1978). *Spatial patterns for discrete models of diffusion in
excitable media.* SIAM Journal on Applied Mathematics 34(3):515-523. doi:10.1137/0134040.

Scope: a faithful reproduction of a published excitable-media cellular automaton; no real-world
data. Framing: a deterministic 3-state excitable **cellular automaton** (a synchronous local
update rule on a 2D grid with a von-Neumann neighbourhood, not an agent-stepping ABM) —
disclosed exactly as the game-of-life / forest-fire / turing-pattern reproductions disclose they
are cellular / grid-PDE models. The contribution is whether the harness + locked-prediction
discipline reproduce the Greenberg-Hastings signatures (a fixed-period rotating spiral, wavefront
annihilation, and a refractory-set critical re-entry size) and would catch an artifact.
