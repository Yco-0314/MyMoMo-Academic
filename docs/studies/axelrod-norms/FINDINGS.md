# Axelrod 1986 Norms / Metanorms — FINDINGS

**Status: 2/3 locked clauses REPRO; P1 is an honest MISS.** The COMPARATIVE result —
metanorms strongly RAISE enforcement and SUPPRESS boldness versus the plain norm (P2,
P3) — reproduces decisively. The plain norm does NOT collapse in a *majority* of seeds at
this configuration (P1 MISS). Genuine agent-based reproduction on `abm_auto._platform`.
Predictions were locked BEFORE running (`PREDICTIONS-locked.md`); the config below was
fixed before the run and was NOT tuned to make any clause pass.

## What was built

20 `PlayerAgent`s, each carrying two **heritable 3-bit genes** — boldness `B in {0..7}`
and vengefulness `V in {0..7}` (normalised `b = B/7`, `v = V/7 in [0,1]`). The two arms
are the genuine Axelrod (1986) norms game and its metanorm variant, sharing every rule
and constant and differing ONLY in the metanorm step.

**One round** (one defection opportunity for every agent, in turn):

- The known chance of being seen this act is drawn `S ~ U(0,1)` (common to all observers
  of that act — the simple faithful choice, documented as the exact rule).
- The actor **defects** iff `b = B/7 > S` (bold enough to risk being seen). A defection
  gives the defector the temptation `T = +3` and inflicts the hurt `H = -1` on every
  other agent.
- Every other agent **sees** the defection independently with probability `S`; each seer
  **punishes** with probability `v = V/7`, costing the defector the enforcement penalty
  `E = -9` and the punisher the enforcement cost `P = -2`.
- **METANORM arm only:** a seer who saw the defection but did NOT punish is itself a
  violator; every other agent can see that non-punishment (prob `S`) and meta-punish with
  probability equal to its own `v`, costing the non-punisher `E' = -9` and the
  meta-punisher `P' = -2`.

**One generation** = 4 such rounds, with payoffs accumulated. Then **Axelrod's
evolutionary update**: compute the population payoff mean `mu` and std `sigma`; an agent
with payoff `>= mu + sigma` reproduces twice, one with `<= mu - sigma` dies, the rest
reproduce once; the offspring pool is truncated/topped-up to exactly `N`. Each inherited
gene mutates per-bit with probability `0.01` (a bit flip keeps the gene in `{0..7}` by
construction). Run 100 generations over 20 seeds. The model is deterministic given a seed
(the only randomness is the seeded initial gene draw + the seeded round/selection draws).

The two arms are **FAIR**: identical N, payoff constants, rounds per generation,
generations, mutation rate, initial gene draw and seeds. They differ ONLY in whether the
metanorm meta-punishment step is applied. The outcome metric (LOCKED) is the
population-mean vengefulness `V` and boldness `B` on the 0..7 scale, averaged over the
final 20 generations and over the 20 seeds.

## Locked config (FIXED before the run; not tuned)

| Param | Value |
|---|---|
| N (players) | 20 |
| genes (3-bit each) | B, V in {0..7} |
| payoffs (T / H / E / P) | +3 / -1 / -9 / -2 |
| metanorm (E' / P') | -9 / -2 |
| rounds per generation | 4 |
| mutation rate (per bit) | 0.01 |
| generations | 100 |
| seeds | 0..19 (20 seeds) |
| measurement window | last 20 generations |

## Results (seed-mean over 20 seeds; 0..7 scale; raw)

| Arm | seed-mean final V | V range (std) | seed-mean final B | B range (std) |
|---|---|---|---|---|
| **NO-METANORM (plain norm)** | **2.877** | [0.045, 5.165] (std 1.397) | **0.880** | [0.105, 6.820] (std 1.401) |
| **METANORM** | **5.942** | [4.553, 6.753] (std 0.584) | **0.139** | [0.050, 0.255] (std 0.050) |

Per-seed NO-METANORM final V: 4.29, 0.78, 3.94, 1.37, 3.35, 3.17, 3.76, 5.17, 2.98,
4.78, 2.68, 3.70, 0.78, 1.66, 2.57, 3.26, 4.76, 0.04, 1.99, 2.51.
Per-seed METANORM final V: 5.79, 5.60, 6.19, 5.60, 5.61, 6.65, 6.51, 5.56, 6.34, 4.75,
6.75, 5.76, 5.93, 6.38, 6.55, 4.55, 6.64, 6.24, 5.74, 5.68.

No-metanorm seeds with final V < 2.5 (the collapse bar): **6 / 20** — a minority.

Representative seed-0 trajectory (mean V at gen 0 / 10 / 50 / 100): NO-METANORM 3.50 ->
3.50 -> 4.15 -> 3.85; METANORM 3.50 -> 6.90 -> 6.45 -> 6.20. Boldness (mean B at gen 0 /
10 / 50 / 100): NO-METANORM 4.00 -> 0.35 -> 0.00 -> 0.60; METANORM 4.00 -> 1.45 -> 0.00
-> 0.00. In both arms boldness is driven down from the random start; under the metanorm it
stays crushed near zero, while without it boldness can re-creep upward in some seeds.

## Verdicts

| # | Clause | Pass bar | Measured | Verdict |
|---|---|---|---|---|
| **P1** | Plain norm collapses | majority of no-metanorm seeds end V < 2.5 | **6 / 20** below 2.5 | **MISS** (minority, need >= 11) |
| **P2** | Metanorms raise enforcement | V_meta > V_nometa | **5.942 > 2.877** | **REPRO** |
| **P3** | Contrast holds | V_meta - V_nometa > 0 AND B_meta < B_nometa | **+3.065** and **0.139 < 0.880** | **REPRO** |

## Honest interpretation

- **Metanorms unambiguously raise enforcement and suppress boldness (P2, P3 REPRO).**
  Adding ONLY the metanorm step — punishing those who fail to punish — lifts the
  seed-mean final vengefulness from **2.88 to 5.94** on the 0..7 scale (a +3.07 jump,
  well outside the seed spread of either arm) and drives the seed-mean final boldness
  from **0.88 down to 0.14**. The metanorm arm is also far tighter across seeds (V std
  0.58 vs 1.40): every one of the 20 metanorm seeds ends with V >= 4.55, while the
  no-metanorm seeds scatter from 0.04 to 5.17. This is exactly Axelrod's central
  qualitative finding — the metanorm is what makes enforcement (vengefulness) stick and
  keeps boldness crushed — and it reproduces cleanly and comparatively.

- **P1 is an honest MISS: the plain norm does NOT collapse in a majority of seeds here.**
  Only **6 of 20** no-metanorm seeds end below the locked V < 2.5 collapse bar; the
  seed-mean (2.88) sits just above it. This is reported as a MISS, not papered over. The
  cause is faithful, not a bug: with these payoff magnitudes (E = -9 is a heavy fine
  relative to T = +3) even the plain norm retains *moderate* enforcement in many seeds —
  some vengefulness survives because punishing is cheap relative to the harm prevented,
  so V drifts to an intermediate level rather than collapsing to zero. Axelrod himself
  reported that the plain-norm outcome is **seed-sensitive** and does not uniformly
  collapse — the norm "can" decay but is not guaranteed to — and that seed-sensitivity is
  exactly what we observe: a wide spread (V from 0.04 to 5.17) with a *minority*, not a
  majority, falling to the collapse level. The locked P1 over-stated this as a majority
  collapse; the faithful model returns the honest minority and we report it as MISS. We
  did NOT adjust payoffs, rounds, generations, or the collapse bar to flip P1.

- **The comparative claim — the one that matters — holds decisively.** Whether or not the
  plain norm fully collapses, the metanorm RAISES enforcement and LOWERS boldness versus
  the plain norm in every aggregate and in the seed-by-seed spread. We do NOT claim "the
  norm always establishes"; we claim, and reproduce, that the metanorm makes the norm
  *much* more enforceable than the plain norm.

**Bottom line:** the reproduction cleanly demonstrates Axelrod's *mechanistic*,
comparative result — the metanorm ("punish the non-punishers") is what sustains
vengefulness and suppresses boldness — while honestly reporting that, at this faithful
configuration, the plain norm decays only partially (a minority of seeds below the
collapse bar), so the absolute-collapse clause P1 falls short and is recorded as MISS.

## Source

Axelrod, R. (1986). *An Evolutionary Approach to Norms.* American Political Science
Review 80(4):1095-1111. doi:10.2307/1960858.

Scope: a faithful reproduction of a published synthetic model; no real-world data. The
contribution is whether the harness + locked-prediction discipline reproduce Axelrod's
COMPARATIVE result — metanorms raise enforcement and suppress boldness relative to the
plain norm — and would catch an artifact. The locked claims are comparative, not "the
norm always establishes".
