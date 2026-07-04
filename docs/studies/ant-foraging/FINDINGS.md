# Ant Double-Bridge Foraging — FINDINGS

**Model:** Goss, Aron, Deneubourg & Pasteels (1989), "Self-organized shortcuts in the
Argentine ant", Naturwissenschaften 76:579-581 (the double-bridge experiment + Deneubourg's
branch-choice model). A genuine agent-based reproduction (foraging `AntAgent`s on
`abm_auto._platform`), graded on the LOCKED metric: the short-path traffic fraction.
Predictions P1-P3 were locked BEFORE the run (`PREDICTIONS-locked.md`); nothing below was
tuned.

## What was run

A nest and a food source are joined by two branches, a SHORT one (length Ls=1) and a LONG
one (length Ll). Each tick at most `inject_per_tick`=2 idle ants leave the nest as a stream;
each departing ant chooses a branch with Deneubourg's rule

  P(short) = (phi_short + k)^alpha / [ (phi_short + k)^alpha + (phi_long + k)^alpha ],   k=20, alpha=2,

commits to it, traverses it in time proportional to its length (`travel_time = round(speed *
length)`, speed=10 -> short=10 ticks, long(asym)=20 ticks), turns around at the food, and
returns. A fixed amount q=1 of pheromone is deposited on the chosen branch on BOTH arrivals
(outbound at the food and inbound at the nest). Each tick both reservoirs evaporate by a
factor (1-rho), rho=0.02. 64 ants; 2000 ticks; 5 seeds per arm.

**Grading metric (locked):** the short-path *traffic* fraction — of the branch *commitments*
made in a trailing window of the last 200 departures, the fraction that chose the short
branch. Steady state = mean of that fraction over the last 200 ticks, per seed.

Two arms: **ASYMMETRIC** (Ll = 2*Ls = 2) and **SYMMETRIC** (Ll = Ls = 1).

**The mechanism (why the short branch wins, with no ant measuring length).** Travel time is
proportional to length, so short-branch ants complete the round trip sooner and lay the
*first* returning pheromone while the long-branch ants are still in transit. That early lead
biases the next ants' choice via the (.)^alpha non-linearity, which biases deposition further
— the autocatalytic loop Deneubourg described. Metering the ants onto the bridge a couple at
a time (rather than releasing all 64 at once) is what lets the *earlier return*, not the
first random 50/50 cohort, set the trail; releasing the whole colony simultaneously instead
makes the outcome a coin flip (see caveats). Evaporation keeps the trail bounded and lets a
wrong early lead be overcome.

## Results

### ASYMMETRIC arm (Ll = 2*Ls) — steady short-path traffic fraction per seed

| seed | steady short-frac | final short-frac | winner |
|------|-------------------|------------------|--------|
| 0    | 0.9925            | 0.995            | short  |
| 1    | 0.9866            | 0.990            | short  |
| 2    | 0.9849            | 0.995            | short  |
| 3    | 0.9940            | 0.970            | short  |
| 4    | 0.9768            | 0.985            | short  |

Mean steady = **0.9869** (std 0.0061, min 0.9768, max 0.9940). **5/5** seeds put > 0.8 of
the traffic on the short branch. (Example seed-0 final reservoirs: phi_short ~ 194.6 vs
phi_long ~ 0.65 — the long trail has all but evaporated.)

### SYMMETRIC arm (Ll = Ls) — which branch won, per seed

| seed | final short-frac | winner |
|------|------------------|--------|
| 0    | 0.015            | long   |
| 1    | 0.990            | short  |
| 2    | 0.015            | long   |
| 3    | 0.025            | long   |
| 4    | 0.985            | short  |

**5/5** seeds broke symmetry onto a SINGLE branch (every final is > 0.8 or < 0.2 — never a
stable 50/50). The winner is seed-dependent: **2 seeds short / 3 seeds long**. With identical
branches neither is "right"; the colony still commits to one, chosen by which branch happened
to accumulate the early lead.

### P3 self-reinforcement — cross-seed mean short fraction over time (asymmetric)

| tick | mean short-frac (over 5 seeds) |
|------|--------------------------------|
| 0    | 0.5000 (neutral baseline)      |
| 100  | 0.7070                         |
| 250  | 0.9280                         |
| 500  | 0.9900                         |
| 1000 | 0.9880                         |
| 2000 | 0.9870                         |

The fraction climbs monotonically from the neutral 0.5 to ~0.99 and then holds; the largest
between-checkpoint *decrease* is 0.002 (sampling jitter once already saturated), well inside
the locked tolerance of 0.05.

## Verdicts on the LOCKED metric (short-path traffic fraction)

| # | Prediction | Pass clause | Measured | Verdict |
|---|------------|-------------|----------|---------|
| P1 | Colony selects the shorter path | asymmetric: short-frac > 0.8 at steady state in >=80% of seeds | 5/5 seeds (mean 0.987) | **REPRO** |
| P2 | Symmetric -> symmetry breaking | symmetric: one path wins (final >0.8 or <0.2) in >=80% of seeds, winner seed-dependent | 5/5 broke symmetry, 2 short / 3 long | **REPRO** |
| P3 | Self-reinforcement over time | short-frac rises monotonically over the run (and ends high) | 0.50 -> 0.99, worst drop 0.002, final 0.987 | **REPRO** |

All three locked clauses **REPRO** (3/3).

- **P1** clears with margin: every seed sits at 0.977-0.994 steady short fraction, far above
  the 0.8 bar; the worst seed (0.9768) still passes individually.
- **P2** is genuine symmetry breaking, not a degenerate tie: each symmetric run polarises
  onto one branch (finals are 0.985-0.990 or 0.015-0.025, never near 0.5), and which branch
  wins differs across seeds (2 short, 3 long) — exactly Deneubourg's "the colony picks one,
  but not always the same one" result.
- **P3** the rise is monotone within tolerance (the only non-increases are post-saturation
  jitter of <=0.002) and ends high — the short fraction does not merely fluctuate, it
  *climbs* and locks in.

## Honest caveats

- **Metered injection is load-bearing, and is disclosed.** If all 64 ants are released
  simultaneously (`inject_per_tick = 64`), P1 FAILS: the first synchronous cohort splits
  ~50/50 by chance and the alpha=2 autocatalysis then locks in whichever branch got the
  noisy early lead, so only ~2/5 seeds pick the short path (the rest lock onto the long one).
  With a metered stream (2/tick here; the result is equally strong at 3, 4, or 6/tick) the
  short branch's *earlier return* — the actual Goss mechanism — sets the trail, and 5/5
  seeds select short. This is a modelling choice about how ants enter the bridge, FIXED
  before the graded run, not a tuning of alpha/k/rho to rescue the result. It is faithful: in
  the experiment ants traverse the bridge as a stream, not as one instantaneous mob.
- **Deposit convention.** Ants lay on BOTH legs (outbound arrival + inbound arrival); the
  module also supports `deposit_on="return"` (Goss's returning-ant emphasis) and
  `"outbound"`. The convention is documented and fixed per run. The short-path advantage
  comes from differential *return timing*, not from the leg on which pheromone is laid.
- **Trail saturation is real but bounded.** With q=1 and rho=0.02 the winning reservoir
  settles high and the losing one evaporates toward 0; the choice probability is then
  effectively deterministic. This is the intended end state (a committed trail), not a
  numerical artifact — evaporation keeps phi finite.
- **Finite-size / single-regime claim.** This is one colony size (64), one length ratio
  (2:1), one (k, alpha, rho, q, speed) point, measured over the last 200 of 2000 ticks. The
  REPRO is of the *qualitative* phenomena Deneubourg/Goss reported (shorter-path selection +
  symmetry breaking + monotone self-reinforcement) on the locked metric, NOT of any
  quantitative trail-equation constant or a phase boundary in (alpha, rho). The model is
  known to be alpha/rho-sensitive — too strong an autocatalysis or too weak an evaporation
  can lock onto the long branch — and we would have reported MISS had the locked point fallen
  in that regime; it does not.
- **Determinism.** Every run is reproducible from its seed (pinned by a test): same seed ->
  identical short-fraction and pheromone series.

## Scope

Faithful reproduction of a published synthetic/biological model; no real-world data. The
contribution is whether the harness + locking discipline reproduce the self-organized
shorter-path selection and the symmetry-breaking on symmetric bridges, and would have caught
an artifact (e.g. a broken choice function, equal travel times, or a missing return-timing
asymmetry would break P1/P3). Falsified clauses would have been reported MISS; here all three
hold.
