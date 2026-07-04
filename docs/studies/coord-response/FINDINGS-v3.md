# Coord-Response ABM — FINDINGS v3 (agent-based redesign, post-run + post-audit)

**Status:** v3 run complete against the pre-registered `PREDICTIONS-locked-v3.md`
(committed `ab4eaec` BEFORE this run, `e5ad37b`). Verdicts reported against their
LITERAL locked clauses; **a 22-agent adversarial audit then refuted the headline P3
mechanism story, and this document has been corrected accordingly (prose-only — no
re-run, no re-tuning; the locked W=2 verdicts are unchanged).** The model is genuinely
agent-based, and the lock-before-run + no-parameter-tuning discipline was independently
git-verified intact (params fixed in `10d9a9d` before the lock; lock `ab4eaec` 21:57
before run `e5ad37b` 22:04; predictions doc never edited post-lock; v2 thresholds
reused verbatim).

**Config:** N=30 networks, seeds (0,1,2,3,4), budget B=4, null-gate margin 1.0 tick,
fail penalty 30.0 (pending-aware metric), `coord_window=2` (locked default).

## TL;DR — what v3 actually shows (corrected after audit)

1. **DOC A's optimization robustly helps (P1/P2) — the defensible result.** Optimized
   beats original in 87% of networks (P1) and beats a random-edge null (P2, margin
   1.57); both robust across the `coord_window` knob. This is the study's real finding.
2. **The v3 load channel is genuine and edge-responsive** (peak_overload varies on
   17/30 networks; optimized ≥ original whenever it varies) — the structural defect the
   v2 audit found is fixed, and the model is now a real ABM.
3. **🔴 But the divergence thesis (static↑ → process↓ via load) is NOT demonstrated.**
   P3's locked clause is technically satisfied (corr 0.222, 1 counterexample), so P3 is
   reported REPRO **to honor pre-registration**, but the audit proved the lone
   counterexample is **spurious**: network 2's `peak_overload` is *invariant* 1.875
   across all treatments (it is NOT one of the 17 load-varying networks), and its −0.4
   "backfire" is **pure failure-RNG** — with failures disabled it is exactly 0.0, and
   over 500 seeds it is a statistical true-zero (mean −0.002; 485/500 ties; 8 worse / 7
   better — a coin flip). **With failures off, the load channel produces ZERO
   counterexamples ensemble-wide.** In this model the timing benefit dominates wherever
   the load channel fires; static optimization never actually backfires through load.
4. **P5 (CEI) is sound but coarse/structural:** removing a top-CEI department worsens
   makespan far more than a median one (Δ221 vs 67), driven by a reachability **pending
   stall** cascade, not a subtle process effect.

**Net:** v3 succeeds at being a genuine ABM with a live load channel and at holding the
honesty discipline; it does **not** vindicate DOC B's divergence worry — within this
synthetic model, DOC A's static-efficiency optimization is robustly beneficial and the
"counterexample" the pre-registered test caught was noise. That negative result is the
honest contribution.

## Verdict table (W=2, locked)

| Prediction | Verdict | score | threshold | honest reading |
|---|---|---|---|---|
| P1 — optimized beats original makespan in ≥60% of ensemble | **REPRO** | 0.8667 | 0.60 | ✅ robust (0.90/0.87/0.87 at W=1/2/3) |
| P2 — null-gate: optimized beats original AND random-edge null | **REPRO** | 1.57 | 1.0 | ✅ robust (pass at W=1–6) |
| P3 — 0<corr<0.9 AND ≥1 counterexample (static↑, makespan↑) | **REPRO** | 0.222 | 0.9 | 🔴 **clause met SPURIOUSLY** — the counterexample is failure-RNG, not the load channel (see §P3); divergence NOT demonstrated |
| P4 — phase ranking REPORTED (single combined DAG) | **REPORTED** | 0.0 | 0.0 | — |
| P5 — top-CEI removal degrades makespan more than median-CEI | **REPRO** | 154.167 | 0.0 | ✅ robust, but reachability/penalty-driven (see §P5) |

## The genuine v3 mechanism (what makes this an ABM, and edge-responsive)

Autonomous `DepartmentAgent`s run `receive → decide → act` each tick on the platform
scheduler (`AgentSet` + `DataCollector`); each agent acts only on its **local inbox**
and capacity. Activation timing is **edge-responsive**: the *environment* (model)
computes, each tick, the least-latency arrival of every task's activation at every node
via a Dijkstra over the current topology (edge weight `w` costs `ceil(1/w)` ticks) into
a model-owned message bus that agents read once `arrival ≤ t`. (This is a leak-free,
distributed-*equivalent* message bus — arrivals are numerically identical to faithful
per-agent relay; the propagation is centrally computed, not literally relayed agent-to-
agent. The agents themselves are genuinely autonomous.) A shared collaborator (e.g.
省交通运输厅, on 3 phase-2 tasks) bears coordination load only during a short
`coord_window` after each task's activation reaches it; whether several windows OVERLAP
at the hub — i.e. whether it overloads — depends on the topology-dependent arrival
spread. So `peak_overload` is emergent and varies by treatment.

**Mechanism functionality (verified, outcome-blind before lock + at run):**
- `peak_overload` varies across {original, optimized, random} on **17/30** networks at
  W=2; optimized > original on **15/30**. (v2: invariant constant 1.875 everywhere.)
- Direction robust across the window knob (channel present at W=1–6; optimization never
  *lowers* the peak below original) — not a single-W artifact.
- `peak_overload` is **binary at this DAG scale** — only 1.25 (2 windows collide) or
  1.875 (3 collide). The channel is real but **coarse (2-state)**.
- Original baselines complete all 9 tasks (0 non-done over 150 runs). Deterministic.

## §P3 — consistency / divergence (CORRECTED after audit)

corr(static_gain, makespan_gain) = **0.222** — a weak-positive mapping (static
efficiency helps the process on average but explains little per-network variance), the
"imperfect mapping" DOC B posits. The locked clause also requires ≥1 counterexample
(static↑ but makespan↑/worse); the ensemble produced exactly **1 → network 2**. The
audit dissected it:

- **It does NOT exercise the v3 load channel.** Net-2's `peak_overload` is invariant
  **1.875** across original/optimized/random — it is not a load-varying network. The
  per-tick utilization series are identical between treatments.
- **The −0.4 is pure failure-RNG.** With `failure_prob=0` (and `slope=0`), original and
  optimized are *identical*: 36.0 every seed (gain exactly 0.0). The −0.4 comes solely
  from the half-step retry on failure (`_model.py` act-stage) landing on a different
  critical-path task under optimized timing in 2 of the 5 locked seeds.
- **It is a statistical true-zero / seed-window artifact.** Mean makespan_gain on net 2:
  −0.40 at n=5 (the locked window) → −0.06 at n=50 → −0.01 at n=200 → **−0.002 at
  n=500 (485/500 ties, 8 worse vs 7 better)**. A *different* 5-seed window gives 0.000.
- **The W-story is quantization, not saturation.** The counterexample appears at
  W ∈ {1,2,4,5} and is absent only at W=3 and W=6 (extended sweep below), where net-2's
  mean makespan_gain lands exactly on the strict `<0` boundary (one seed's sign flip
  cancels another). `peak_overload` is identically saturated at 1.875 (orig=opt) for all
  of W=2–6, so saturation cannot distinguish them. (The earlier "W=3 saturation leaves
  no room" explanation was wrong and has been removed.)

**Honest conclusion:** P3's pre-registered clause is met, so REPRO is reported (moving
the goalpost post-hoc would itself break the discipline) — **but the result is spurious;
the divergence thesis is not demonstrated.** With failures disabled the load channel
yields zero counterexamples across the whole ensemble (n_improved still 26/30, corr
≈0.20). The genuine takeaway is the opposite of a divergence: in this model static
optimization's timing benefit robustly survives the (real, but weak) load channel.

### coord_window sweep (pre-registered W=1/2/3, extended W=4/5/6 for disclosure)

| W | P1 frac | P1 | P2 | corr | #counterexamples | P3 | P5 |
|---|---|---|---|---|---|---|---|
| 1 | 0.90 | ✅ | ✅ | 0.229 | 1 | ✅ | ✅ |
| **2 (locked)** | 0.867 | ✅ | ✅ | 0.222 | 1 | ✅ | ✅ |
| 3 | 0.867 | ✅ | ✅ | 0.251 | 0 | ❌ | ✅ |
| 4 | 0.867 | ✅ | ✅ | 0.245 | 1 | ✅ | ✅ |
| 5 | 0.90 | ✅ | ✅ | 0.258 | 1 | ✅ | ✅ |
| 6 | 0.90 | ✅ | ✅ | 0.264 | 0 | ❌ | ✅ |

P1/P2/P5 robust to W. P3's lone (spurious) counterexample blinks in/out at the
sub-tick quantization boundary (present {1,2,4,5}, absent {3,6}) — consistent with RNG
noise, not a mechanism with a coherent W-dependence.

## §P5 — CEI validation (CORRECTED after audit)

mean makespan increase on removal: top-CEI dept=**221.21**, median-CEI dept=**67.05** →
P5 REPRO (top > median), robust across W. Mechanism (corrected): isolating a central
department disconnects its collaborators, so the task it leads **fails** and every
downstream task **stalls PENDING** (its predecessor never completes). The pending-aware
penalty then fires on all non-done tasks: top-CEI removal leaves **~9 non-done (≈1
FAILED root + ≈8 PENDING dependents; 29/30 networks collapse fully, net 14 partially
completes)** vs ≈2–3 non-done on median removal. So the Δ221-vs-67 gap is
**reachability/penalty-dominated**, a coarse "remove the critical hub → coordination
stalls" effect, not a subtle process signal (peak_overload ≈0.78 on the top-CEI arm —
no overload involved). The audit separately *refuted* a sharper attack ("CEI value adds
nothing beyond binary DAG-membership"): holding structural role fixed, within-network
corr(CEI, makespan-delta) ≈ 0.71 and the higher-CEI lead has the higher delta in 80% of
pairwise comparisons — so static CEI *does* predict dynamic criticality. P5 is honest as
REPRO with the reachability caveat.

## P4 — phase ranking (reported-only)

Single combined 9-task DAG, so reported not scored. Mean completion tick by phase
(optimized): {监测预警: 13.15, 处置救援: 30.95, 事后恢复: 39.15} — monitoring earliest,
recovery latest, following the DAG. DOC A's static phase ranking (监测预警 > 处置救援 >
事后恢复) is noted, not scored.

## Honest comparison to v2 (why the redesign was still worth it)

| | v2 (god-loop) | v3 (agent-based) |
|---|---|---|
| Is it an ABM? | No — central two-pass loop, passive depts | Yes — autonomous `DepartmentAgent.step()` on platform |
| `peak_overload` | invariant constant 1.875 (channel absent) | emergent, varies on 17/30 nets |
| P3 (divergence) | MISS (no counterexample possible) | REPRO by the literal clause, but the counterexample is RNG noise → divergence still NOT demonstrated |
| P5 (CEI) | MISS (pending-blind makespan bug inverted it) | REPRO (fixed metric; reachability/pending-stall driven) |
| P1/P2 (timing) | REPRO but pass-by-construction | REPRO and now genuinely falsifiable (load *could* fight timing — it just doesn't win) |

The discipline earned its keep a third time: v1 was an artifact, v2 over-claimed
"overload bites," and v3's clean 4/4 table tempted a "divergence demonstrated"
narrative — which the audit refuted as RNG noise before it shipped. The honest result
is narrower and more interesting: a genuine ABM whose real load channel is too weak to
overturn DOC A's timing benefit.

## Sensitivity & scope

- **coord_window sweep** (table above) is the primary robustness check. P1/P2/P5 robust;
  P3's counterexample is sub-tick RNG (present at W∈{1,2,4,5}).
- **Synthetic representative ensemble, not real provinces.** No real coordination
  network data — only DOC A's reported optimal edges, top-CEI nodes, per-phase gains.
- **Uncalibrated agent parameters** (capacity / task_rate / failure slope /
  coord_window) — set for mechanism functionality, never to a cross-treatment outcome
  (git-verified: fixed before the lock).
- **Claim is method-mechanism validity on a synthetic agent-based model, not real-world
  response prediction.** No hazard physics, no casualty/loss, non-spatial.
- **Known model limitations (audit, not affecting locked results):** activation
  propagation is computed centrally (distributed-equivalent message bus, not literal
  agent relay); `Scenario.triggers` is currently inert (timing comes from
  `Task.trigger_tick` + DAG `needs`); the `_origin`/`_arrival` cache assumes a static or
  edge-adding topology (the default scenario has no edge cuts).
- Motivates real-network collection for a future exact validation.
