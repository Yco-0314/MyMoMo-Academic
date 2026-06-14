# Method-Transfer Probe Matrix — PREDICTIONS (written before running)

**Status: PREDICTIONS ONLY. Written 2026-06-01 BEFORE any probe was run.
Not validated. The point is to compare these predictions against real
outcomes — wrong predictions are the most valuable signal (they expose
gaps in our understanding of the architecture).**

This file is committed/timestamped before the probe runs precisely so it
cannot be edited post-hoc to match results — the anti-fabrication "unforgeable
trace, artifact before conclusion" principle applied to this experiment
itself.

## Method of probing

Each probe = (external method × ABM domain). For each, predict:
- **Can it run?** Can the current architecture supply the input the
  method consumes?
- **If it runs, is the result meaningful?** Or does the method compute
  something on a domain where it has no interpretation?
- **Which wall does it hit?**

## Wall taxonomy (from A/B demos + extended)

- **W1 data-missing** — method needs intermediate state we don't collect
  (e.g. time-varying transmission graph). [hit by Demo 2/Ricci-SIR]
- **W2 structure-mismatch** — method's assumed dynamics ≠ domain's
  dynamics (e.g. CSD's gradual fold vs Deffuant's abrupt split). [hit by
  Demo 1/CSD-Opinion]
- **W3 interpretation-void** — method runs, produces a number, but
  nothing defines whether that number *means* anything for this domain.
  Who judges? (new — to be probed)
- **W4 representation-gap** — ABM state → the mathematical object the
  method needs (point cloud, phase-space, graph) is non-obvious. (new)
- **W5 sample-size** — data dimension/length insufficient for the
  method. (new)
- **W6 experiment-design** — method needs interventional / counterfactual
  data; passive observation insufficient. (new)

## Input-type grouping (the architecture-relevant axis)

A method's runnability is hypothesised to depend mostly on **what input
type it consumes**. Our architecture supplies aggregate time series
(env-level) + static contact graph well; agent-level history,
event-level streams, and distribution snapshots poorly.

### Type A — univariate time series (we HAVE: aggregate output columns)

| # | Method | Domain | Predict run? | Predict wall |
|---|---|---|---|---|
| 1 | Critical slowing down | Opinion | ✗ no-signal | W2 [DONE: confirmed negative] |
| 2 | Critical slowing down | SIR count_i | runs | W2-partial — count_i is a peak, not an equilibrium approach; CSD may misfire |
| 3 | Hurst exponent / DFA | SIR count_i | runs | W3 — Hurst computes, but what does long-range dependence *mean* for an epidemic curve? |
| 4 | Change-point detection | Opinion variance | runs, "succeeds" | W3-trivial — Deffuant IS a step; detecting the step is circular, not insight |
| 5 | Permutation entropy | SIR count_i | runs | W3 — computes a complexity number, no domain interpretation |

### Type B — multivariate time series (we HAVE: multiple aggregate cols)

| # | Method | Domain | Predict run? | Predict wall |
|---|---|---|---|---|
| 6 | Transfer entropy | SIR (s,i,r) | runs | W3-trivial — s→i→r is a deterministic flow; TE will show strong i→r and call it "information transfer", which is mechanically obvious |
| 7 | Granger causality | Opinion (mean,var,clusters) | runs | W5 — 3 vars × short series, Granger needs more samples for stable VAR |
| 8 | Mutual-information network | SIR (s,i,r) | runs | W3 — MI between conserved-sum quantities is artifactual (s+i+r=N) |

### Type C — static graph (we HAVE: contact network)

| # | Method | Domain | Predict run? | Predict wall |
|---|---|---|---|---|
| 9 | Fiedler value / algebraic connectivity | Schelling | W4 first — Schelling is a grid, must build same-type adjacency graph before Fiedler applies | then runs |
| 10 | Modularity / community detection | Opinion network | runs | W3 — modularity of the static Watts-Strogatz contact graph is fixed at setup; says nothing about opinion dynamics |
| 11 | Degree-centrality distribution | SIR network | runs | W2 — static-graph centrality ≠ transmission importance (which needs the time-varying spread graph) |

### Type D — time-varying graph (we LACK: event stream)

| # | Method | Domain | Predict run? | Predict wall |
|---|---|---|---|---|
| 12 | Ollivier-Ricci curvature | SIR transmission graph | ✗ | W1 [confirmed by Demo-2 recon: no edge-level infection events collected] |
| 13 | Temporal centrality | SIR | ✗ | W1 — same missing transmission graph |
| 14 | Temporal modularity | Opinion (opinion-similarity graph over time) | ✗→maybe | W1 + W4 — could rebuild a similarity graph from opinions, but that's a representation choice, not collected |

### Type E — high-dim state trajectory / point cloud (we LACK: agent-level history)

| # | Method | Domain | Predict run? | Predict wall |
|---|---|---|---|---|
| 15 | Persistent homology (TDA) | Opinion | ✗ | W4 + W1 — scalar opinion per agent → point cloud is a representation choice; agent-level history needs streaming collection |
| 16 | PCA / manifold learning | SIR agent states | ✗ | W1 — per-agent state history not stored (only aggregate counts) |
| 17 | Lyapunov exponent | Opinion | ✗ | W4 + W2 — phase-space reconstruction non-trivial; Deffuant is contractive so λ<0 is trivial anyway |

### Type F — interventional data (we LACK: active experiment)

| # | Method | Domain | Predict run? | Predict wall |
|---|---|---|---|---|
| 18 | PC causal discovery | SIR (params→outcomes) | partial | W6 + W5 — needs many runs at varied params; our calibration runs *are* such data, but not structured for causal discovery |
| 19 | do-calculus effect | Opinion intervention | ✗ | W6 — needs counterfactual runs (force an opinion, observe), not collected |

### Type G — distribution sequence (we LACK: agent-level snapshots)

| # | Method | Domain | Predict run? | Predict wall |
|---|---|---|---|---|
| 20 | Optimal transport (Wasserstein over time) | Schelling | ✗ | W1 + W4 — needs agent-position distribution per tick; only aggregate segregation index stored |

## Pre-registered aggregate predictions

Before running, I predict:

- **Type A/B/C (≈11 probes) mostly RUN but hit W3 (interpretation-void)
  or W2 (structure-mismatch).** The dominant wall for *runnable* probes
  is "computes a number with no domain meaning."
- **Type D/E/G (≈8 probes) mostly FAIL at W1 (data-missing).** The
  dominant wall for *blocked* probes is "we don't collect the
  intermediate state." This is the architecture's biggest gap:
  event-level + agent-level streaming.
- **W3 (interpretation-void) will be the most common wall overall**, and
  it is the one no amount of data collection fixes — it needs a
  method-domain *compatibility* notion (which method means what on which
  domain), echoing the ε-verifier family.
- **Most surprising prediction to test**: that the "runnable" probes are
  actually *more* dangerous than the blocked ones, because a blocked
  probe fails loudly (W1) while a runnable-but-meaningless probe (W3)
  produces a publishable-looking number that is silently garbage. If
  true, this inverts the intuition that "can run = good."

## What would falsify the framework

- If many Type-D/E/G probes actually RUN (architecture supplies more than
  expected) → the "input-type determines runnability" hypothesis is wrong.
- If runnable probes cleanly self-report meaninglessness → W3 isn't a real
  wall, the guard handles it.
- If wall types don't cluster by input-type → the taxonomy is overfit to
  the 2 demos.
