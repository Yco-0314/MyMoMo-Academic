# Independent Cascade + influence maximization — review

**tier: minimal** (all-REPRO 3/3, comfortable margins; no MISS). Reviewed vs the verified claim + lock.

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — headline (crossing λ=1.12, submod 1.0, greedy 0.9964) matches bundle/results.
- fair-control: **pass** — P1 sweeps λ=p·z on one graph family; P3 compares greedy vs OPT/random on one instance.
- no-post-lock-drift: **pass** — graded verbatim vs committed lock; integrity gate ok.
- mechanism-aliveness: **pass** — the percolation transition is real (reached 0.000→0.577 across λ=0.5→2.0, crossing 1.12) and submodularity holds in 100% of tested nested pairs.
- framing-disclosure: **pass** — hybrid (agent activation + edge-probability cascade + combinatorial-opt gate), disclosed.

## Verdict: SOUND. 3/3 REPRO. Percolation transition + submodularity + (1−1/e) greedy all confirmed.
Distinctness confirmed: edge-probability single-shot activation + submodularity + the greedy guarantee are IC
properties the built node-threshold models (Watts/Granovetter/complex-contagion) do not have. No tuning. 19 tests.

REVIEW COMPLETE
