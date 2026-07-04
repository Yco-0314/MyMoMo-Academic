# Hegselmann–Krause 2002 Bounded Confidence — FINDINGS

**Run 2026-06-30, AFTER predictions were locked** (see `PREDICTIONS-locked.md`).
Faithful agent-based reproduction on the neutral platform (`abm_auto._platform`):
each opinion is held by an autonomous `OpinionAgent`; one tick is a SYNCHRONOUS sweep
in which every agent simultaneously replaces its opinion with the mean of all opinions
within its confidence bound ε (inclusive, including itself), all computed from one
shared snapshot and committed together. Code:
`abm_auto/classics/hegselmann_krause.py`; experiment:
`examples/repro_hegselmann_krause/run.py`.

## Config (FIXED before the run; no tuning)

| param | value |
|---|---|
| N (agents) | **1000** |
| initial opinions | Uniform[0, 1] (fresh draw per seed) |
| update | **synchronous**: x_i ← mean{ x_j : \|x_i − x_j\| ≤ ε } (incl. self) |
| ε-grid | 0.05, 0.1, 0.15, 0.2, 0.3 |
| seeds per ε | **20** (seeds 0..19) |
| cluster tol | 0.01 (sort opinions, split runs at gaps > tol) |
| stationary tol | max single opinion change in a whole sweep < **1e-6** |

Determinism: the update reads only the start-of-tick snapshot, so it is
order-independent and reproducible given the seed. All runs converged (`all_converged
= true` at every ε).

## Measured #clusters and consensus fraction per ε

| ε | mean #clusters | var | range (min–max) | consensus fraction | mean sweeps |
|---|---|---|---|---|---|
| 0.05 | **8.25** | 1.09 | 7–10 | 0.00 (0/20) | 16.3 |
| 0.10 | **4.20** | 0.46 | 3–5 | 0.00 (0/20) | 9.7 |
| 0.15 | **2.60** | 0.34 | 2–4 | 0.00 (0/20) | 40.0 |
| 0.20 | **1.80** | 0.16 | 1–2 | 0.20 (4/20) | 30.1 |
| 0.30 | **1.00** | 0.00 | 1–1 | **1.00 (20/20)** | 5.3 |

Mean #clusters falls strictly and monotonically as ε rises (8.25 → 4.20 → 2.60 →
1.80 → 1.00). Consensus (a single cluster) is essentially absent below ε=0.2, partial
at ε=0.2 (20% of runs), and universal at ε=0.3. The consensus threshold therefore sits
between ε=0.2 and ε=0.3 — consistent with HK's reported ε_c ≈ 0.2.

## Verdicts vs the locked clauses (refutation tier — "not refuted", never "verified")

| # | Locked clause | Result | Salient numbers |
|---|---|---|---|
| P1 | Consensus above the confidence threshold (ε≥0.25 → 1 cluster in ≥90% of runs) | **REPRO** | consensus fraction at ε=0.3 = **1.00** ≥ 0.90 |
| P2 | mean #clusters non-increasing as ε rises | **REPRO** | max upward step = **−0.80** ≤ 0 (strictly decreasing across the grid) |
| P3 | Fragmentation at low ε (ε≤0.1 → mean #clusters ≥ 2) | **REPRO** | min mean over ε≤0.1 = **4.20** ≥ 2.0 |

**3/3 locked clauses REPRO.** The reproduction recovers HK's central result: a single
confidence-threshold transition from a fragmented opinion landscape at low ε to
consensus at high ε, with the cluster count decreasing monotonically through the
transition.

## Honest caveats

- **P1's "ε ≥ 0.25" is graded on the single grid point ε = 0.3** (0.25 is not on the
  locked grid). At ε=0.3 consensus is unanimous (20/20), well clear of the 90% bar, but
  the clause is verified at one ε, not across a ≥0.25 sub-range. The neighbouring ε=0.2
  point gives consensus in only 20% of runs, so the true 90%-consensus onset lies
  between 0.2 and 0.3 — the threshold is bracketed, not pinned, by this grid.
- **The consensus threshold is grid-resolution-limited.** With a 0.05-spaced grid the
  fragment→consensus transition is located only to within [0.2, 0.3]. We do **not**
  refine the grid to land closer to the canonical ε_c ≈ 0.2 (that would be post-hoc
  tuning); the locked grid is reported as-is.
- **Low-ε cluster counts exceed the naive Deffuant ⌊1/(2ε)⌋ band-count.** HK's
  synchronous all-neighbours-average leaves a few extra minor clusters at small ε
  (e.g. mean 8.25 at ε=0.05 vs the ⌊1/(2·0.05)⌋ = 10 band ceiling, and 4.20 at ε=0.1
  vs the 5 ceiling); the locked clauses grade the TOTAL #clusters, which is what is
  reported. No major/minor split is applied.
- **DISTINCT from Deffuant.** This is genuinely the HK model, not Deffuant: the update
  is a SYNCHRONOUS sweep averaging over the WHOLE ε-neighbourhood at once (including
  self), not a sequence of pairwise random encounters with a partial step μ. The two
  modules share only the cluster-counting helper shape; the dynamics differ.
- **All runs reached a stationary state** (max single move < 1e-6) within the step cap
  at every ε; no run was truncated. Sweep runtime ≈ 108 s (5 ε × 20 seeds).
- **Bundle `code_commit` provenance.** `verdict-bundle.json`'s `code_commit` is HEAD at
  run-time (the bundle is committed together with the code, so it points to the parent
  commit). Reproduction integrity is anchored on the content-addressed **sha256** of the
  docs/data artifacts (all `replay: strong`), not the commit pointer.
- **Scope.** Faithful reproduction of a published *synthetic* model — no real-world data.
  The contribution is that the harness + lock-first discipline reproduce the
  consensus/fragmentation result and would surface an artifact (a refutation gate, not a
  truth certificate).
