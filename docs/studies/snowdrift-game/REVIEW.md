# Spatial Snowdrift Game (Hauert-Doebeli 2004) — review

**tier: minimal-plus-gate** (all-REPRO 3/3; the load-bearing keep-with-gate control PASSED). Genuine
agent-based. Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (worst inhibition gap 0.1733 at r*=0.7) matches bundle/results/FINDINGS.
- fair-control: **pass** — the replicator vs best-takes-over arms differ ONLY in the update rule; the r-sweep is otherwise identical.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; FINDINGS authored + re-run so the bundle fingerprints it.
- mechanism-aliveness: **pass** — the inhibition mechanism is alive AND mechanism-SPECIFIC (see gate).
- framing-disclosure: **pass** — genuine C/D lattice agents with stochastic replicator imitation, disclosed.

## THE LOAD-BEARING GATE (keep-with-gate) — PASSED decisively.
The whole point of a distinct reproduction (vs the built nowak_may_pd) is the SIGN of the spatial effect.
The best-takes-over control confirms the inhibition is specific to the stochastic replicator rule, not a
mislabeled Nowak-May:
- replicator worst inhibition gap = 0.1733 (r*=0.7) vs best-takes-over gap = 0.0009 (≈0)
- replicator f_lat(0.8) = 0.000 (extinction) vs best-takes-over f_lat(0.8) = 0.334 (no extinction)
- mechanism-specific = True

## Verdict: SOUND. 3/3 REPRO.
P1 well-mixed f=1−r (exact); P2 spatial structure INHIBITS cooperation (f_lat < 1−r across the sweep,
worst gap 0.1733 — OPPOSITE sign to the spatial PD); P3 high-r extinction (f_lat(0.8)=0 vs f_wm 0.2).
The Hauert-Doebeli headline reproduces, and the gate proves it is the stochastic-replicator mechanism,
not the payoff relabeling, that produces it. 27 tests. No tuning. (Experiment authored + run centrally
after the builder wrote the code but did not complete the run.)

REVIEW COMPLETE
