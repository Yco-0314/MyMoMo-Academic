# CODA (Continuous Opinions, Discrete Actions) — review

**tier: minimal** (all-REPRO 3/3, every margin huge; no load-bearing dead-mechanism risk).
Built to the committed rigorous lock (ν = ln(α/(1−α)) = 0.8473, 2×10⁶→4×10⁶ doubling check).

## Mandatory cheap checks (all pass)
- numeric-provenance: **pass** — graded numbers match the bundle (P1 879≥100, P2 0.945>0.003, P3 8≤250).
- fair-control: **n/a** — single-arm extremization study; P3 compares the random-start cluster count (~330) to the frozen count (7–8) as a documented baseline.
- no-post-lock-drift: **pass** — all three clauses graded verbatim against the committed lock; L3 bundle integrity gate (sha256 of PREDICTIONS + FINDINGS) passes.
- mechanism-aliveness: **pass** — the extremization mechanism is vividly alive (max|l|/ν ≈ 879→still doubling at 4M, median ≈ 1530); P1's doubling-growth check (1.94 ≥ 1.3) actively rules out a plateau artifact, which is the failure mode a too-short run would hide.
- framing-disclosure: **pass** — hidden continuous belief + discrete action + asynchronous single-observation update disclosed in docstring, agent docstring, run.py, FINDINGS.

## Verdict: SOUND. 3/3 REPRO with large margins.
Faithful Bayesian discrete-action update; distinctness signature confirmed (beliefs DIVERGE to
certainty, inverting Deffuant/HK averaging). The builder caught + fixed a real RNG-stream bug
(chunked vs straight batches drew different streams, which would have invalidated the doubling
check) and verified snapshot-invariance — a genuine correctness improvement, not a verdict tune.
23/23 faithfulness tests pass. No tuning, no fabrication.

REVIEW COMPLETE
