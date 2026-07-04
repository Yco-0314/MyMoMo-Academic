# Nagel-Schreckenberg Traffic (1992) — FINDINGS

**Status: 3/3 locked clauses REPRO (P1, P2, P3).** Honest report. Faithful
reproduction of a published *synthetic* model; no real-world data.
The contribution is whether the shared harness + locked-claim discipline
reproduce the fundamental diagram and its spontaneous-jam transition, and would
catch an artifact — not a new empirical result.

**Framing (adversarial review 2026-06-30):** Nagel-Schreckenberg is canonically a
**cellular automaton** (the 1992 paper is literally titled "A cellular automaton model
for freeway traffic"), and the synchronous update here is computed centrally per tick
(the `CarAgent.step` is effectively a no-op — the model applies the four rules in
parallel). So this is a **CA-style reproduction** (like the BTW sandpile), NOT a
genuine agent-stepping ABM; the cars are state-carrying agents but they do not
autonomously drive the tick. Treat the earlier "genuine agent-based" wording as
superseded by this disclosure.

## What was built

A Nagel-Schreckenberg cellular-automaton model on the neutral platform
(`abm_auto._platform`): a 1D **ring** of `L=1000` cells, each holding at most one
`CarAgent` with integer position and integer velocity in `[0, vmax]`, `vmax=5`,
slowdown probability `p=0.3`. Each tick applies the four NaSch steps **in
parallel** (synchronous update — the defining feature of NaSch):

1. **Accelerate** `v <- min(v+1, vmax)`
2. **Brake** `v <- min(v, gap)` where `gap` = empty cells ahead to the next car
3. **Randomize** with prob `p`, `v <- max(v-1, 0)`
4. **Move** `x <- (x+v) mod L`

All new velocities are computed from the *frozen current configuration* first,
then every car moves — a sequential update would be a different, less-jammy
model, so this is load-bearing. The gap is the only thing a car reads beyond its
own state (local interaction on the ring); the only global coupling is the shared
ring occupancy. One seeded RNG chain places the cars and drives every
randomization draw, so each run replays bit-for-bit from its seed.

Outcomes (the LOCKED metrics), averaged over the post-transient measurement
window: **mean velocity** `<v>`, **flow** `q = rho * <v>` (cars crossing a fixed
point per tick — the fundamental-diagram observable), and **stopped fraction**
(cars with `v == 0`, the jam metric).

## Configuration (FIXED before the run; not tuned)

| Parameter | Value |
|---|---|
| Ring length L | 1000 cells |
| vmax | 5 |
| slowdown prob p | 0.3 |
| density grid rho | 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7 |
| seeds per rho | 10 (seeds 0..9) |
| transient (discarded) | 1000 ticks |
| measurement window | 500 ticks |
| update | parallel (synchronous) |

## Fundamental diagram (mean over 10 seeds; +/- = cross-seed std)

| rho | cars | flow q | mean v | stopped frac |
|----:|----:|---:|---:|---:|
| 0.05 | 50 | 0.2341 +/- 0.0002 | 4.682 +/- 0.004 | 0.000 +/- 0.000 |
| 0.10 | 100 | **0.4614 +/- 0.0014** | 4.614 +/- 0.014 | 0.001 +/- 0.001 |
| 0.15 | 150 | 0.4587 +/- 0.0066 | 3.058 +/- 0.044 | 0.185 +/- 0.010 |
| 0.20 | 200 | 0.4365 +/- 0.0070 | 2.182 +/- 0.035 | 0.298 +/- 0.018 |
| 0.30 | 300 | 0.3932 +/- 0.0039 | 1.311 +/- 0.013 | 0.435 +/- 0.014 |
| 0.40 | 400 | 0.3477 +/- 0.0013 | 0.869 +/- 0.003 | 0.515 +/- 0.010 |
| 0.50 | 500 | 0.2969 +/- 0.0016 | 0.594 +/- 0.003 | 0.605 +/- 0.007 |
| 0.70 | 700 | 0.1884 +/- 0.0008 | 0.269 +/- 0.001 | 0.763 +/- 0.004 |

**Flow argmax: rho = 0.10** (peak flow 0.4614). The flow rises from the
low-density branch, peaks at an interior density, then falls monotonically as the
road jams — the textbook fundamental diagram. Cross-seed variance is tiny (std
<= 0.007 on flow everywhere), so the shape is not a single-seed accident.

## Verdicts (locked metrics; refutation tier)

- **P1 — interior flow maximum: REPRO.** `argmax_rho flow = 0.10`, an interior
  point of the grid `[0.05, 0.70]` (not an endpoint), matching the canonical
  critical density `rho_c ~ 0.1` for vmax=5, p=0.3. Falsifier (peak pinned at
  the lowest or highest density) did not occur.

- **P2 — free-flow at low density, congested at high: REPRO.** mean
  `v(rho=0.05) = 4.682 >= 3` AND mean `v(rho=0.5) = 0.594 <= 2`. Velocity decays
  monotonically across the grid (4.68 -> 0.27).

- **P3 — spontaneous jams emerge (p>0, no obstacle): REPRO.** stopped fraction
  `(rho=0.5) = 0.605 >= 0.1`. With no obstacle on the ring, 60% of cars are at
  rest at rho=0.5 purely from the randomization-seeded congestion that
  back-propagates — the spontaneous start-stop ("phantom") jam.

## Spontaneous jams — the mechanism

Jams appear with **no obstacle**: at intermediate-to-high density the random
slow-down (step 3) occasionally drops a car's speed; the car behind must brake to
its gap, the next behind brakes, and a stop wave propagates *backwards* against
the flow. Above the critical density the road can no longer dissipate these waves
faster than they form, so a persistent jammed region coexists with free-flow
gaps. The stopped fraction is the fingerprint: it is ~0 in the free-flow regime
(rho <= 0.1), jumps once the critical density is passed (0.185 at rho=0.15), and
climbs steadily (0.605 at rho=0.5, 0.763 at rho=0.7). Setting `p=0` removes the
stochastic trigger so the **spontaneous (phantom) jams vanish** — the deterministic
NaSch limit reaches a smooth steady state with no random start-stop waves (correction,
adversarial review 2026-06-30: at *high* density the deterministic limit still has many
stopped cars from sheer crowding — e.g. ~34% stopped at rho=0.5 — so it is the
*p-driven phantom* jams that vanish, not all stopped cars). The tests confirm the
phantom-jam removal — direct evidence that the spontaneous jams are *p-driven*, not
artifacts of placement or boundaries.

## Caveats / honesty

- This is a faithful reproduction of a **synthetic** model, not a calibration to
  real traffic data. P1-P3 are qualitative/structural anchors (interior peak,
  free-flow->jam transition, spontaneous jams), not point predictions of real
  flow values. The absolute flow numbers depend on L, vmax, p and the
  measurement protocol; only the *shape* claims are graded.
- The exact critical density and peak-flow value are protocol-dependent (vmax=5,
  p=0.3 here). The peak sits at rho=0.1 on this grid; a finer grid could place it
  slightly differently, but it remains interior — that is all P1 claims.
- The update is **parallel**, as the original requires. A sequential update is a
  different model and would shift the diagram; the test suite pins the parallel
  semantics (move uses the velocity computed from the frozen state).
- Refutation tier: passing these gates means the locked claims were **not
  refuted** by a disciplined run with fixed parameters — not that the model is
  "verified true." The value is that an artifact (e.g. an accidental sequential
  update, or a peak pinned at an endpoint) would have produced a MISS.

## Reproduce

```
PYTHONPATH=. .venv/bin/python examples/repro_nagel_schreckenberg/run.py
PYTHONPATH=. .venv/bin/python -m pytest tests/classics/test_nagel_schreckenberg.py -q
```

Cite: Nagel, K., Schreckenberg, M. (1992). *A cellular automaton model for
freeway traffic.* Journal de Physique I 2(12):2221-2229. doi:10.1051/jp1:1992277.
