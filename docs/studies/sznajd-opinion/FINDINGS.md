# Sznajd 2000 Opinion Dynamics ("united we stand") — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`): each
lattice site is an autonomous `OpinionAgent` carrying its opinion in {-1,+1}; the
`SznajdModel` owns the seeded RNG, the lattice, the local plaquette rule, and a
`DataCollector` (the per-sweep magnetization series) -- not a god-loop. The opinions live
ON the agents; the rule reads/writes the opinions of agents at local cells, and each
plaquette pick is uniformly random with NO global oracle. Code:
`abm_auto/classics/sznajd.py`; experiment: `examples/repro_sznajd_opinion/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| lattice | **40 x 40**, periodic (toroidal) boundaries |
| opinions | s in {-1, +1}; initial up-density d (independent per cell, seeded) |
| rule variant | **2D Sznajd "united we stand"** (Stauffer 2000 generalisation) |
| update step | pick a uniformly-random 2x2 plaquette; if **all four agree**, set its **8 edge-adjacent outer neighbours** (2 above, 2 below, 2 left, 2 right; the 4 diagonal frame corners are NOT persuaded) to that opinion; else no change |
| one tick (sweep) | **L*L = 1600** plaquette picks |
| stop rule | a **frozen state** (a full sweep with zero opinion changes) or a cap of **1000 sweeps** |
| d-grid | **0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8** |
| seeds per d | **20** (seeds 0-19; each seed drives both the placement and every pick) |
| locked metric | **final magnetization** m = mean opinion, and **P(all-UP)** |
| consensus tolerance | abs(m) >= **0.95** counts as near-complete consensus (P1 metric) |

Determinism: a single seeded RNG chain drives placement + every plaquette pick, so the
same seed reproduces byte-identical output (pinned in `tests/classics/test_sznajd.py`).

## Measured outcomes per density (averaged over 20 seeds)

| d | P(all-UP) | consensus frac (abs(m)>=0.95) | full-consensus frac | mean m | var m | frozen frac | n_up / n_down |
|---|---|---|---|---|---|---|---|
| 0.2 | 0.00 | 1.00 | 1.00 | -1.000 | 0.000 | 1.00 | 0 / 20 |
| 0.3 | 0.00 | 1.00 | 1.00 | -1.000 | 0.000 | 1.00 | 0 / 20 |
| 0.4 | 0.00 | 1.00 | 1.00 | -1.000 | 0.000 | 1.00 | 0 / 20 |
| **0.5** | **0.50** | 1.00 | 1.00 | **+0.000** | **1.000** | 1.00 | 10 / 10 |
| 0.6 | 1.00 | 1.00 | 1.00 | +1.000 | 0.000 | 1.00 | 20 / 0 |
| 0.7 | 1.00 | 1.00 | 1.00 | +1.000 | 0.000 | 1.00 | 20 / 0 |
| 0.8 | 1.00 | 1.00 | 1.00 | +1.000 | 0.000 | 1.00 | 20 / 0 |

**Every run (all 140) froze on a full +/-1 consensus.** No stable stripes, no blinkers, no
non-consensus frozen states for this 8-neighbour rule. Time-to-freeze across all runs:
min 2 sweeps, median 5, mean 14.9, max 247 -- well under the 1000-sweep cap (so the cap
never truncated a run). At d=0.5 the magnetization variance is exactly 1.0, the signature
of a perfectly bimodal outcome (every run lands on +1 or -1, never in between).

## Verdicts vs the locked clauses (refutation tier -- "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Complete consensus from d=0.5 (abs(m)>=0.95 in >=80% of runs) | **REPRO** | consensus fraction = **1.000** >= 0.80 (all 20 runs reached abs(m) = 1.0) |
| P2 | Phase transition at d=1/2 (P(all-UP) ~0 for d<=0.4, ~1 for d>=0.6) | **REPRO** | max P(all-UP) over {0.2,0.3,0.4} = **0.000** <= 0.05; min P(all-UP) over {0.6,0.7,0.8} = **1.000** >= 0.95 |
| P3 | Majority initial opinion wins (P(all-UP\|d=0.7)>0.8 AND P(all-UP\|d=0.3)<0.2) | **REPRO** | P(all-UP\|d=0.7) = **1.000** > 0.8; P(all-UP\|d=0.3) = **0.000** < 0.2 |

**3/3 locked clauses REPRO.** The reproduction recovers Sznajd's central result: the
"united we stand" rule drives a closed community to **complete consensus** on a single
opinion, and the consensus reached is governed by a **phase transition at d = 1/2** -- the
initial majority always wins, with a perfectly steep step exactly at d = 0.5 (a coin-flip
there, 10 up / 10 down over 20 seeds).

## Caveats and honest notes

- **Steepness of the transition.** The measured step is maximally sharp: P(all-UP)
  jumps 0 -> 0.5 -> 1 over d = 0.4 -> 0.5 -> 0.6 with nothing intermediate at d = 0.4 or
  d = 0.6. At d = 0.5 it is a clean coin-flip. On a finite 40x40 lattice the transition
  is already this crisp; a larger lattice would only sharpen it further (the variance at
  d = 0.5 is already 1.0, the bimodal limit).
- **No non-consensus frozen states.** Some 2D Sznajd *variants* (e.g. rules that persuade
  only a subset of neighbours, or anti-ferromagnetic flip rules) can freeze into stable
  stripes or oscillating blinkers and never reach full consensus. The variant used here --
  unanimous 2x2 -> persuade the 8 edge-adjacent neighbours (Stauffer 2000) on a periodic
  lattice -- reached **full** consensus in 100% of runs (P1 is not merely >=80%, it is
  100%). This is reported as the genuine finding of *this* variant; the rule was fixed
  before the run and was NOT changed to force consensus.
- **Metric discipline.** Grading is on the LOCKED metric only -- abs(final magnetization)
  and P(all-UP). No threshold, density, or seed was tuned to make consensus or the
  transition appear; L, the d-grid, the rule, the frozen-state stop, and the 20 seeds were
  fixed and committed before the run.
- **Scope.** A faithful reproduction of a published *synthetic* opinion-dynamics model;
  no real-world data. The contribution is whether the harness + discipline reproduce
  consensus and the d = 1/2 transition (they do) and would catch an artifact if they did
  not.

## Citations

- Sznajd-Weron, K. & Sznajd, J. (2000). "Opinion evolution in closed community."
  *Int. J. Mod. Phys. C* 11(6):1157-1165. doi:10.1142/S0129183100000936.
- Stauffer, D., Sousa, A.O. & Moss de Oliveira, S. (2000). "Generalization to square
  lattice of Sznajd sociophysics model." *Int. J. Mod. Phys. C* 11(6):1239-1245.
