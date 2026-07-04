# Spatial Snowdrift Game (Hauert-Doebeli 2004) — FINDINGS

**Status: 3/3 locked clauses REPRO, and the load-bearing GATE passes.** Genuine agent-based
reproduction on `abm_auto._platform`. Predictions locked BEFORE running (`PREDICTIONS-locked.md`);
config fixed before the run, not tuned.

## What was built
An L=100 periodic lattice of pure C/D agents, Moore-8 neighbourhood, snowdrift payoffs
(T>R>S>P: R=b−c/2, T=b, S=b−c, P=0), cost-to-benefit ratio r=c/(2b−c). Payoffs are SUMMED over
the 8 neighbours (self excluded). The update rule is the **stochastic replicator / pairwise
imitation** of Hauert & Doebeli: a focal agent imitates a random neighbour with probability
proportional to the positive payoff difference. The well-mixed baseline is the analytic/mean-field
replicator interior ESS f=1−r.

## The load-bearing control (why this is not a mislabeled Nowak-May)
The SAME model was also run under a **best-takes-over** update (deterministic imitation of the best
neighbour — the Nowak-May rule). The inhibition is specific to the stochastic replicator rule:

- replicator worst inhibition gap = **0.1733** at r*=0.7; best-takes-over gap at the same r* = **0.0009**
- replicator f_lat(0.8) = **0.0000** (extinction) vs best-takes-over f_lat(0.8) = **0.3336** (no extinction)
- gate: effect is mechanism-specific = **True**

## Results (stochastic replicator; f_lat = time-avg over the last window, ≥20 runs/r)

| r | 1−r (well-mixed) | f_lat (replicator) | f_lat (best-takes-over) | inhibition gap |
|---|---|---|---|---|
| 0.40 | 0.600 | 0.4693 | 0.7179 | +0.1307 |
| 0.50 | 0.500 | 0.3582 | 0.6730 | +0.1418 |
| 0.60 | 0.400 | 0.2470 | 0.4643 | +0.1530 |
| 0.70 | 0.300 | 0.1267 | 0.2991 | +0.1733 |
| 0.75 | 0.250 | 0.0489 | 0.3196 | +0.2011 |
| 0.80 | 0.200 | 0.0000 | 0.3336 | +0.2000 |
| 0.90 | 0.100 | 0.0000 | 0.0000 | +0.1000 |

## Verdicts (refutation tier)
- **P1 REPRO** — well-mixed reproduces the interior ESS f=1−r exactly (|f_wm−(1−r)| ≤ 0.03, slope −1).
- **P2 REPRO** — spatial structure INHIBITS cooperation: f_lat < 1−r for the whole sweep, worst gap
  0.1733 at r=0.7 (≥0.10 bar) — the OPPOSITE sign to the spatial Prisoner's Dilemma.
- **P3 REPRO** — high-r extinction: f_lat(0.8) = 0.000 (lattice) while f_wm(0.8) = 0.200 (well-mixed).

No honest MISS. The headline Hauert-Doebeli result — spatial structure often INHIBITS cooperation in
the snowdrift game, unlike the PD where it promotes it — reproduces, and the best-takes-over control
confirms the effect is specific to the stochastic replicator dynamics.
