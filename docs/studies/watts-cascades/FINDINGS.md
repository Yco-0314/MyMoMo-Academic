# Watts 2002 Global Cascades — FINDINGS

**Run 2026-06-29, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`):
each vertex is an autonomous `CascadeAgent` applying the local threshold rule under an
`AgentSet` scheduler + `DataCollector` (not a god-loop). Code:
`abm_auto/classics/watts_cascade.py`; experiment: `examples/repro_watts_cascades/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| graph | Erdős–Rényi `gnm_random_graph` (z = 2m/n exact); fresh graph + fresh seed node per trial |
| n | **10,000** (full paper size — no compromise) |
| φ (threshold, uniform) | **0.18** |
| global-cascade cutoff | final active fraction **≥ 0.10** |
| seeds per z | **100** |
| z-grid (16 pts) | 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0 |
| vulnerable degree bound | K = ⌊1/φ⌋ = **5** |

Degree-0 convention: an isolated node's active-fraction is 0, so it never activates
unless it is itself the seed (Watts' convention — an isolated vertex cannot be
triggered by neighbours it does not have). Update is synchronous → order-independent
→ deterministic given the trial index.

## Measured global-cascade frequency per z

| z | freq | n_cascades / 100 | bimodal | size modes (low / mid / high) |
|---|---|---|---|---|
| 0.5 | 0.00 | 0 | no | 100 / 0 / 0 |
| 1.0 | 0.01 | 1 | yes | 99 / 0 / 1 |
| 1.5 | 0.51 | 51 | yes | 49 / 0 / 51 |
| 2.0 | 0.69 | 69 | yes | 31 / 0 / 69 |
| 2.5 | 0.82 | 82 | yes | 18 / 0 / 82 |
| 3.0 | 0.84 | 84 | yes | 16 / 0 / 84 |
| 3.5 | **0.91** (peak) | 91 | yes | 9 / 0 / 91 |
| 4.0 | 0.90 | 90 | yes | 10 / 0 / 90 |
| 4.5 | 0.82 | 82 | yes | 18 / 0 / 82 |
| 5.0 | 0.69 | 69 | yes | 31 / 0 / 69 |
| 5.5 | 0.36 | 36 | yes | 64 / 0 / 36 |
| 6.0 | 0.05 | 5 | yes | 95 / 0 / 5 |
| 6.5 | 0.00 | 0 | no | 100 / 0 / 0 |
| 7.0 | 0.00 | 0 | no | 100 / 0 / 0 |
| 7.5 | 0.00 | 0 | no | 100 / 0 / 0 |
| 8.0 | 0.00 | 0 | no | 100 / 0 / 0 |

**Measured cascade window (first/last z with freq>0): z ∈ [1.0, 6.0].**
Canonical (Watts, φ=0.18): ≈ [1, 5.8]. Peak frequency 0.91 at z=3.5.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Cascade frequency non-monotonic in z (≈0 low, interior peak, ≈0 high) | **REPRO** | freq(z=0.5)=0.00 ≤ 0.02; peak=0.91 @ z=3.5; freq(z=8.0)=0.00 ≤ 0.02 |
| P2 | Lower boundary near ER connectivity onset (first z with freq>0 in [0.8, 2]) | **REPRO** | measured lower = **1.0** ∈ [0.8, 2.0] |
| P3 | Upper boundary finite, last z with freq>0 in [4, 7] | **REPRO** | measured upper = **6.0** ∈ [4, 7] (canonical 5.8) |
| P4 | Cascade-size distribution bimodal (tiny-local vs system-spanning) | **REPRO** | aggregated in-window: low=440, **mid=0**, high=660 |

**4/4 testable clauses REPRO.** The reproduction recovers Watts' central result:
a finite interior "cascade window" in mean degree z, opening at the connectivity
onset and closing where vulnerable vertices (k ≤ K = 5) stop percolating.

## Honest caveats

- **Boundaries are grid-resolution-limited.** The measured window [1.0, 6.0] is read
  off a 0.5-spaced grid, so each boundary is accurate only to ±0.5. The upper boundary
  6.0 is one grid step above the canonical 5.8; at z=5.5 freq is still 0.36 and at z=6.0
  it is 0.05 (5 cascades), so the true upper edge sits between 5.5 and 6.5 — consistent
  with 5.8. Both boundaries fall inside the locked acceptance ranges; we do **not**
  refine the grid to land closer to canonical (that would be post-hoc tuning).
- **The lower boundary z=1.0 is a single-cascade boundary** (1/100). It coincides
  exactly with the ER giant-component onset, which is the right physics, but a 1-cascade
  count is near the noise floor; the window is unambiguously open by z=1.5 (51/100).
- **Bimodality is unusually clean: the middle band is literally empty** (mid=0 at every
  z, aggregate mid=0/1100). Final sizes are either O(1/n) local failures or a single
  large system-spanning mode — exactly Watts' qualitative picture, with no intermediate
  cascades at n=10,000.
- **No config compromise.** Full n=10,000 and 100 seeds/z were used (no reduction).
  Sweep runtime ≈ 92 s.
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed together with the code, so it points to the parent
  commit). Reproduction integrity is anchored on the content-addressed **sha256** of the
  docs/data artifacts (all `replay: strong`, verified MATCH), not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* model — no real-world data.
  The contribution is that the harness + lock-first discipline reproduce the
  cascade-window result and would surface an artifact (a refutation gate, not a truth
  certificate).
