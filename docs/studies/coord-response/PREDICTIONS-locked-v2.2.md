# Coord-Response ABM — LOCKED Predictions v2.2 (pre-registration)

**Status:** LOCKED before the v2.2 cross-treatment experiment run.
**Date locked:** 2026-06-28
**Branch:** `feat/coord-response-abm`
**Supersedes:** `PREDICTIONS-locked-v2.1.md`.

## Why v2.2 (transparent)

The v2.1 run was still degenerate (mean_orig == mean_opt == 37.60, corr = NaN):
even after info-delay gated from eligibility, every task coordinated over a
DIRECT required edge of weight ≥ 1, so its delay sat at the 1-tick floor
(ceil = 1) and no edge addition could lower it. The model could respond to delay
in principle but had no ROOM for the optimizer to act.

**Fix (commit `965d9e4`, mechanism, verified OUTCOME-BLIND):** required
(lead,collaborator) edges are now added at WEAK weight (~0.34–0.84 → delay
1.2–2.9 ticks, above the floor) with a STRONG hub backbone, so baseline
coordination is slow and an added shortcut CAN reduce a task's delay. Verified by
single-treatment diagnostics ONLY: (a) baseline still completes all 9 tasks;
(b) peak_overload > 1.0 (1.875); (c) 6/9 tasks have baseline ceil-delay > 1;
(c2) a best-possible strong overlay drops makespan 43→39 (room = 4 ticks). The
actual optimized-vs-original-vs-null comparison was **NOT** consulted; whether
DOC A's GLOBAL-efficiency greedy captures that room is the open research question.

> **Lock-first + outcome-blind.** I do not know the v2.2 outcomes. Any of P1–P5
> may be FALSIFIED → MISS. No thresholds/params tuned to pass.

## Experiment configuration

N = 30 networks (`representative_network(seed=ni)`, ni = 0..29); seeds
(0,1,2,3,4); budget B = 4; treatments original / optimized (CEI-protected on
省应急管理厅) / null (B random edges); primary outcome makespan (lower better,
penalty 30, timing scale ≈ 40 ticks); null-gate margin 1.0 tick.

## Predictions (same spirit + thresholds throughout v2)

- **P1 — Process effectiveness.** `optimized` beats `original` mean makespan in
  **≥ 60%** of the 30 networks. REPRO ≥60%; PARTIAL 50–60%; MISS <50%.
- **P2 — Null-gate.** Mean `optimized` beats mean `null` AND mean `original` by
  **≥ 1.0 tick** (gate passes → "not refuted"). REPRO if pass; MISS otherwise.
- **P3 — Consistency.** `corr(static_gain, makespan_gain)` is **> 0 and < 0.9**
  AND **≥ 1 counterexample** (static_gain > 0 but makespan_gain < 0). REPRO if
  both; PARTIAL if one; MISS if neither. If DOC A's global-efficiency edges
  systematically miss the response critical path, makespan_gain may be ~0
  ensemble-wide (corr near 0/NaN) → P3 MISS — a valid honest divergence finding.
- **P4 — Phase ranking.** Reported-only; compared to DOC A's 监测预警 > 处置救援 >
  事后恢复 ranking. REPORTED.
- **P5 — CEI validation.** Isolating the top-CEI department raises mean makespan
  **more** than isolating a median-CEI department. REPRO if so; MISS otherwise.

## Sensitivity analysis (mandatory)

±50% capacity & failure_prob (scaled from v2 hub/non-hub defaults); record whether
P1 and P2 hold. Robustness, not tuning.

## Honest scope

Synthetic representative ensemble, not real provinces; parameters set for
mechanism-functionality only (baseline completes; overload occurs; optimizer has
room); method-mechanism validity, not real-world prediction; motivates
real-network collection. No real network data.
