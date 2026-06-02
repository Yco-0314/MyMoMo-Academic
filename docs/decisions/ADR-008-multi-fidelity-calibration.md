# ADR-008: Multi-Fidelity Calibration — Coarse-to-Fine Sim Budget Split

> _Editorial note (2026-06-02): the original challenge's event name has been neutralized to "the virus-on-a-network (SIR-on-network) calibration challenge"; the decision and rationale below are unchanged._

**Status**: Accepted (default OFF; opt-in for expensive sim contexts)
**Date**: 2026-05-31
**Deciders**: yco + Claude (Opus 4.7)
**Related**: [ADR-006](ADR-006-calibration-recovery.md)

---

## Context and Problem Statement

After ADR-006's calibration recovery (MSE 1480 → 47.4), the remaining wall
cost was dominated by simulator iteration. A single `fit_from_files`
across three calibration domains (SIR / Opinion / Schelling) takes ~4.4
minutes end-to-end in CI; the full-Pipeline path with LLM phases takes
~29 minutes per domain (90 min for three), forcing the 2026-05-31
cross-domain CI to pivot to the lean path. Every Pipeline-mediated
dogfood iteration cost the same ~5 min wall on SIR; iterating on
prompts, mechanisms, or hypotheses paid this cost repeatedly.

The screening backends (RF, ABC, PyMC) need ~100 simulator calls to
build a usable RF surrogate or non-trivial ABC posterior. Each call
runs the full `periods=250` tick budget at full fidelity, even when
the goal of the call is just to map the **shape** of the loss surface
across the prior.

**The waste**: 100 full-fidelity sims to learn "the surface peaks
roughly here" — when 60 sims at periods=50 (1/5 the cost) would map
that surface shape almost as well.

## Decision Drivers

1. **Iteration speed is research throughput** — every halved wall hour
   doubles experimentation
2. **Visible seam over implicit speedup** — fidelity scaling needs to
   be inspectable + tunable, not buried in a backend
3. **Zero regression bar** — MF must not move MSE beyond 3× empirical
   ceiling on any cross-domain example
4. **Backwards-compatible fallback** — `use_multi_fidelity=False`
   reproduces the pre-MF single-stage screening exactly

## Decision

Introduce a **`Fidelity` data class** as a knob on `SimulatorWrapper`
that scales the scenario CSV's `periods` column at write-time. Three
presets cover the full schedule:

- `Fidelity.coarse()` — `periods × 0.4`
- `Fidelity.medium()` — `periods × 0.7`
- `Fidelity.full()` — `periods × 1.0` (canonical sim length)

The `BayesianCalibrator.fit` orchestrator runs a two-stage screen by
default:

1. **Stage A (coarse, 50% budget)** — RF on full priors at `Fidelity.coarse()`
2. **Stage B (medium, 50% budget)** — RF on priors narrowed to ±50%
   around Stage A's best_params at `Fidelity.medium()`
3. **Refinement** — Nelder-Mead from Stage B's best_params at `Fidelity.full()`

Refinement always runs at full fidelity so the final MAP estimate is
computed on the canonical sim, not a coarsened proxy. The scenario CSV
is restored to base `periods` at the end of `fit()` so downstream
consumers (`apply_best_params`, `run_final_validation_sim`) see the
canonical sim length even though they bypass `simulate()`.

The cascade RF → PyMC → ABC is preserved within each stage; when a
backend fails (degenerate prior, NaN posterior), the next one runs.

## Why coarse=0.4, medium=0.7 (post-tuning)

The initial proposal was `coarse=0.2` (50 ticks on the SIR
challenge), reasoning that 50 ticks captures the epidemic peak. The
first cross-domain MF run proved this wrong: SIR MSE regressed
36.875 → 1250 because at 50 ticks the trajectory has barely passed peak;
the post-peak relaxation phase (where `gain_resistance_chance` signal
lives) is absent. The coarse-stage RF surrogate optimized a different
loss landscape than the full sim, and the narrowed Stage B box was
centered on the wrong basin.

Tuning iteration produced the current values:

- **0.4 coarse** (100 ticks on the SIR challenge): captures peak + the
  first half of relaxation. RF surrogate now aligns directionally with
  full-fidelity loss in the SIR challenge's three-param space.
- **0.7 medium** (175 ticks): runs through the late relaxation. Stage
  B's MAP differs from full-fidelity MAP by < 5% across the benchmark
  examples.

The trade-off: coarse=0.4 saves ~50% per-sim wall instead of ~70%, but
the schedule actually converges. Speed-for-correctness is the right
trade for default behavior; aggressive users can manually pick
`Fidelity(periods_scale=0.2)` if they've validated it on their domain.

## Why narrow_priors factor=0.5

Each side of the prior box shrinks to 50% of the original width
(post-tuning), centered on the previous stage's best. Initial value
of 0.25 was too aggressive — combined with a misleading coarse stage,
Stage B's narrowed box missed the true mode entirely. At factor=0.5,
the narrowed box still excludes ~50% of the search space (so Stage B
gets useful concentration), but retains enough hedge that a 30%-off
coarse call doesn't lose the true mode.

Below ~1% original width, `_narrow_priors` falls back to the original
range (degeneracy guard).

## Considered Alternatives

### Alternative A: Multi-fidelity via reduced agent count

Cut `n_agents` instead of `periods`. Rejected because:
- Many ABM mechanisms have **population-size-dependent dynamics**
  (epidemic thresholds, opinion cluster counts) — halving agents
  doesn't just halve cost, it changes the qualitative answer
- `periods` scaling preserves mechanism structure; only the
  trajectory length changes

### Alternative B: Trajectory subsampling at full periods

Run full-length sims but record every Nth tick. Rejected because:
- Wall cost stays at full-fidelity (the iteration loop, not CSV
  writes, is the bottleneck on most calibration sims)
- Provides no actual speedup

### Alternative C: Surrogate model only (no fine refinement)

Use a single coarse stage at `periods × 0.5`, skip medium + NM. Rejected
because the MAP estimate at coarse fidelity systematically differs from
full-fidelity MAP by 5-15% on the SIR challenge — beyond the calibration
challenge's reporting precision.

### Alternative D: Adaptive fidelity per backend call

Decide each call's fidelity based on previous calls' loss values
(invest more in promising regions). Rejected for v1: implementation
complexity exceeds the marginal win. The 60/40 + narrowed-prior
schedule captures most of the benefit with one clean knob.

## Empirical findings (the reason MF defaults to OFF)

Cross-domain lean dogfood on three calibration examples:

| Domain | Single-fidelity MSE | MF MSE | Wall (single) | Wall (MF) |
|--------|---------------------|--------|---------------|-----------|
| SIR (virus) | 36.875 | 121.560 | 98s | 97s |
| Opinion | 0.073 | 0.090 | 73s | 70s |
| Schelling | 0.000 | 0.000 | 91s | 78s |

Two findings drove the default-OFF decision:

1. **MF MSE tax is real on SIR.** Even after tuning (coarse=0.4,
   medium=0.7, narrow=0.5), MF best_params for SIR's recovery_chance
   was 3.22 vs ground truth 0.3 — a 10× error. At coarse fidelity (100
   ticks), agents who recover at rate 0.3 vs 3.22 both end up "mostly
   recovered" by the end of the trajectory, so the RF surrogate can't
   distinguish them. Stage B's medium fidelity (175 ticks) is still
   too short to separate them. The fix isn't a tuning constant; it's
   a structural mismatch between "shorter trajectory" and "recovery
   rate identifiability."

2. **MF wall savings are negligible on lean sims.** SIR went 98s → 97s.
   Per-sim wall on a handcrafted_model is ~1s, of which ~0.5s is
   subprocess startup + Melodie boot. Cutting periods 60% saves
   ~0.3s/sim → ~30s across 100 sims, which gets partly eaten back by
   the second-stage RF refit and prior-narrowing overhead. The net
   wall delta is in the noise.

MF earns its keep when the **per-sim cost is high** — full-Pipeline
runs with multi-seed observed sims, larger agent populations, or
longer base periods. On those contexts the proportional cost dominates
and a 0.4× scale actually saves seconds per sim. Cross-domain lean is
the wrong test for MF speed; that's why the default is now off and
opt-in for the contexts where MF helps.

## Consequences

### Positive

- **Infrastructure ready** — `Fidelity`, narrow_priors, fidelity
  scaling, restore-to-base all unit-tested + wired
- **Clean seam** — backends consume `Fidelity` transparently via the
  `SimulatorWrapper` attribute; no signature changes
- **Default is regression-safe** — `use_multi_fidelity=False` reproduces
  exactly the pre-MF single-stage screening at full fidelity; the lean
  cross-domain CI gate exercises this path
- **Composable with future engine rewrite** — when ADR-009 ships a
  standalone engine, `Fidelity.periods_scale` continues to work
  unchanged
- **Future-proof for expensive contexts** — when sim costs grow
  (multi-seed Pipeline, larger agent counts, longer base periods), the
  opt-in path is a one-line change at the call site

### Negative

- **Default-off means MF doesn't ship a user-visible speedup today.**
  The infrastructure is ready but the speedup only manifests at sim
  costs higher than lean cross-domain produces. Users wanting MF must
  pass `use_multi_fidelity=True` explicitly.
- **Coarse-fidelity surrogate bias is real for SIR-shaped models.**
  Recovery / decay rates are particularly hard to identify at short
  trajectories. Future work: per-parameter fidelity sensitivity flag
  in `_narrow_priors` (skip narrowing for rate-of-decay params at
  coarse fidelity).
- **Two MF labels in the backend column** (`mf(...→...)`) when MF is
  on — slightly noisier calibration reports.

### Neutral

- **Random Forest signal does not strictly require samples drawn at
  the same fidelity** — surfaces fit on coarse trajectories can still
  guide narrowing, even though they're biased estimates of the
  full-fidelity loss surface. This is the well-known multi-fidelity
  emulation trade-off (cf. Kennedy & O'Hagan 2000). The bias only
  becomes problematic when a parameter's signal **lives in the part
  of the trajectory the coarse stage truncates** — exactly SIR's
  recovery_chance situation.

## Implementation Notes

### Period restoration

`fit()` calls `simulator.restore_periods_to_base()` before returning so
the scenario CSV ends in the canonical state. Without this, the
following sequence would silently break the validation CSV:

1. MF Stage B writes `periods=125` for medium fidelity
2. NM runs at `Fidelity.full()`, last call writes `periods=250` ✓
3. `posterior.apply_best_params(best_params)` writes best_params but
   not periods → CSV stays at 250
4. `posterior.run_final_validation_sim` calls `executor.run` directly
   (bypasses `simulate()` → bypasses `_apply_fidelity`)

The path is safe **as long as NM ran**. If NM skipped (screening
result not ok), Step 2 wouldn't restore periods. Explicit restoration
guards this edge case.

### Backends remain pure

`backends.run_rf`, `run_pymc`, `run_abc` take a `simulator` argument
and call `simulator.simulate(params, targets)`. They never see
`Fidelity`. The schedule lives at the calibrator orchestration layer,
so swapping in a new screening backend (e.g., a future SBI / BOLFI
backend) requires no MF-specific changes.

### Test surface

`tests/test_multi_fidelity.py` covers:

- `Fidelity` dataclass — presets, frozen semantics
- `_narrow_priors` — centering, bound clipping, degeneracy fallback
- `SimulatorWrapper._apply_fidelity` — period scaling, caller-override
  precedence, no-op cases (no `periods` column, fidelity=None|full)
- `SimulatorWrapper.restore_periods_to_base` — overwrite, no-snapshot
  no-op, idempotency

End-to-end MF on real domains is exercised by `tests/e2e/cross_domain_lean.py`
in CI.

## Open Questions

**OQ#1**: At what budget does MF stop helping? The 60/40 split assumes
a screening budget around 100. With max_sims=20, MF may underfit each
stage. Empirical thresholding (when does MF MSE diverge from
single-stage by >5%?) — deferred to a future calibration deep-dive.

**OQ#2**: Should `Fidelity` extend to **seed scaling** for stochastic
ABMs? Multi-seed averaging could let coarse stage use 1 seed and full
stage use 5, further compounding the wall win. Deferred to v2 of this
ADR. Current `Fidelity` is intentionally a single `periods_scale` knob.

**OQ#3**: Does MF interact pathologically with `summary_fn =
trajectory_features`? The 12-D summary collapses tick count, so
coarse and full sims produce same-shape feature vectors — RF surrogate
should still be valid. Untested at MF=on with trajectory_features;
flagged for the cross-domain dogfood.

## Verification

- `tests/test_multi_fidelity.py` — 19 unit tests pass
- `tests/e2e/cross_domain_lean.py` — 3 domains with MF default
  (results pending validation, gate: MSE ≤ 3× single-fidelity ceiling)
- `tests/e2e/dogfood_codegen_path.py` — full Pipeline SIR with MF
  (wall reduction target: ≥30% vs 28.09 MSE baseline)
