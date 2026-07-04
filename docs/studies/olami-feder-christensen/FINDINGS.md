# Olami-Feder-Christensen Earthquakes / Self-Organized Criticality (1992) — FINDINGS

**Status: 3/3 locked clauses REPRO.** Faithful reproduction of self-organized
criticality (SOC) on `abm_auto._platform`. Predictions were locked BEFORE running
(`PREDICTIONS-locked.md`); the config below was fixed before the run and was NOT tuned to
make any clause pass.

## Framing disclosure (read first)

This is a **DRIVEN-THRESHOLD CELLULAR AUTOMATON** (a model of self-organized
criticality), **NOT autonomous-agent-stepping**. There is no agent that perceives
neighbours and chooses an action each tick. Instead a uniform external ("tectonic")
drive loads a continuous force field until the most-loaded site reaches threshold, and
the resulting topple/redistribution cascade is a deterministic relaxation rule. It is
still built on the neutral platform — each lattice cell is a roster `SiteAgent` (a
force-carrying site), held in the model's `AgentSet` — but the dynamics live at the model
level (drive + avalanche) and the per-cell `step` is a no-op, exactly as in the other CA
reproductions of this suite. We disclose this so the work is not over-claimed as
"agent-based" in the multi-agent-decision sense.

## What was built

A 50×50 lattice of continuous forces `F_i`, initialised `~ U[0, 1)`, with an **open**
boundary. One event is one drive+avalanche:

- **DRIVE** (slow-driving / zero-velocity limit): add a single uniform increment to
  EVERY site so the maximum site reaches the threshold `F_th = 1.0`
  (`delta = 1 − max(F)`; `F_i += delta` everywhere). After this, `max(F) == 1` exactly —
  the just-critical site is the avalanche seed.
- **RELAX** (avalanche): any site with `F ≥ 1` topples — it resets to 0 and adds
  `α·F_old` to each of its 4 von-Neumann neighbours. **Open boundary**: force sent toward
  an off-lattice neighbour (across an edge / out of a corner) is **lost**. A topple can
  push a neighbour over threshold, so the avalanche cascades until no site is `≥ 1`.
- **EVENT SIZE** `s` = number of topplings triggered by one drive (a site may topple more
  than once in an avalanche; each toppling counts). Every event has `s ≥ 1`.

`α` is the redistribution/conservation parameter (`α ≤ 0.25`): an interior topple gives
away `4α` of the released force and dissipates `1 − 4α`. `α = 0.25` is conservative;
`α = 0.2` (main) and `α = 0.1` are dissipative. The avalanche uses an explicit relaxation
**queue** (cost `O(#topplings)`, not a full-lattice rescan per micro-step); the drive is
`O(L²)`. A 5000-drive **transient** is discarded so the system self-organizes to its
stationary critical state before the next `10⁴` events are collected. The run is
deterministic given a seed (the only randomness is the seeded initial force draw).

Faithfulness is pinned by 21 tests (`tests/classics/test_olami_feder_christensen.py`):
exact single-topple bookkeeping (`4α·F` moved, site → 0, interior conserves `4α`,
`α=0.25` conserves all, corner loses the off-lattice share), drive correctness
(`max == F_th` after a drive, same increment everywhere), open-boundary neighbour counts
(4/3/2 interior/edge/corner), a cascade and a multi-topple avalanche on hand-built tiny
lattices, event-size accounting, and determinism.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| lattice L | 50 (open boundary) |
| α grid | 0.2 (main) and 0.1 |
| threshold F_th | 1.0 |
| initial forces | U[0, 1) |
| transient (discarded) | 5000 drives |
| events collected / arm | 10000 |
| seeds | main = 0, alt = 123 (alt for P3 init-independence) |
| P1 bars | ≥ 2 decades AND max ≥ 100× median nonzero |
| P3 metric | log-histogram TV distance < 0.10 (two halves AND two seeds) |

## Results (real numbers from this run)

| Arm | mean event size | max | median nonzero | decades spanned | max / median |
|---|---|---|---|---|---|
| **α = 0.2 (main, seed 0)** | **1.726** | **125** | 1.0 | **2.097** | **125.0** |
| **α = 0.1 (seed 0)** | **1.079** | 12 | 1.0 | 1.079 | 12.0 |
| α = 0.2 (alt seed 123) | 2.121 | 168 | 1.0 | 2.225 | 168.0 |

Bulk vs tail (α = 0.2): 87.4% of events are single topples (`s = 1`), 1.83% are `s ≥ 10`,
0.21% are `s ≥ 50` — a sharp peak at 1 with a long heavy tail out to 125. At α = 0.1 the
distribution is far more compressed: 95.5% are single topples, only 0.04% reach `s ≥ 10`,
and none reach 50 (the most dissipative arm loses force faster, so avalanches die sooner).

P3 distribution-stationarity TV distances: **two halves of the post-transient stream =
0.0092**; **two different seeds/inits (seed 0 vs seed 123) = 0.0274** — both far below the
0.10 bar.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Power-law (heavy-tailed) event sizes (α = 0.2) | ≥ 2 decades AND max ≥ 100× median nonzero | 2.097 decades, max/median = 125 | **REPRO** |
| **P2** | More conservative α → heavier tail | mean(α=0.2) > mean(α=0.1) | 1.726 > 1.079 | **REPRO** |
| **P3** | Self-organizes to a stationary critical state | distribution stationary AND init-independent (TV < 0.10) | TV 0.0092 (halves), 0.0274 (seeds) | **REPRO** |

## Honest interpretation

- **P1 — self-organized criticality is real and unambiguous.** Starting from a uniform
  random force field and with no tuning, the slow drive plus dissipative topple rule
  drives the system to a state whose avalanche-size distribution is sharply peaked at
  `s = 1` but heavy-tailed out to `s = 125` — a range spanning **2.10 decades**, with the
  largest event **125×** the median nonzero event. This is the Gutenberg-Richter /
  scale-free signature the OFC model is famous for: no characteristic event size, a tiny
  fraction of large cascades carrying disproportionate "moment." (System-spanning events
  are bounded by the modest L = 50 lattice and the open-boundary dissipation, so the tail
  is finite-size-cut, not a perfect power law — but the heavy-tailed, multi-decade
  signature is squarely present and passes both locked bars.)

- **P2 — conservation controls the tail, in the right direction.** Moving from α = 0.1 to
  α = 0.2 (more force redistributed per topple, less dissipated) lifts the mean event size
  from **1.079 to 1.726** and the maximum from **12 to 125** — a >10× heavier tail. More
  conservative dynamics keep avalanches alive longer, so they grow larger. This is the
  qualitative α-dependence OFC reported, and the locked inequality holds decisively.

- **P3 — the critical state is genuinely self-organized (stationary + init-independent).**
  The post-transient event-size distribution does not drift: its first and second halves
  are essentially identical (TV = 0.0092), and a run from a completely different random
  initial field (seed 123) lands on the same distribution shape (TV = 0.0274). The system
  forgets its initial condition and settles onto one attractor distribution — the
  defining property of self-organized criticality, not a fine-tuned critical point.

**Bottom line:** all three locked clauses reproduce. The harness + locked-prediction
discipline recover the OFC result — a heavy-tailed, conservation-dependent, stationary and
initial-condition-independent avalanche-size distribution — from first principles, with no
parameter tuned to make a clause pass.

## Source

Olami, Z., Feder, H. J. S. & Christensen, K. (1992). *Self-organized criticality in a
continuous, nonconservative cellular automaton modeling earthquakes.* Physical Review
Letters 68(8):1244–1247. doi:10.1103/PhysRevLett.68.1244.

Scope: a faithful reproduction of a published synthetic SOC model; no real-world data.
The contribution is whether the harness + discipline reproduce self-organized criticality
(a heavy-tailed, α-dependent, stationary + init-independent avalanche-size distribution)
and would catch an artifact.
