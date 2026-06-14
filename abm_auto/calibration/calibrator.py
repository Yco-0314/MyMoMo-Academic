"""BayesianCalibrator orchestrator + standalone calibration entry points.

Three layers, increasingly bundled with pipeline concerns:

  - `fit(simulator, priors, observed, targets, ...)` — pure two-stage
    calibration (screen → refine). No I/O, no workspace, no LLM. Direct
    consumer of `backends.*` and `refiners.*`.

  - `fit_from_files(model_dir, observed_csv, params_specs, targets, ...)`
    — standalone wrapper. Builds a transient Workspace + Executor +
    SimulatorWrapper from paths, calls `fit`, returns the
    CalibrationResult. Benchmark scripts use this to skip the LLM
    pipeline entirely.

  - `BayesianCalibrator.run(executor, spec)` — pipeline-facing agent.
    Calls `fit` then writes artifacts to workspace + generates LLM
    calibration report. Pipeline._should_calibrate() activates it via
    `spec.has_calibration_data is True`.

Splitting `fit` out of the class lets benchmark_calibration_handcrafted
and benchmark_external_model bypass the LLM phases (~5 min → ~30 s per
run), and makes the calibration algorithm itself unit-testable without
LLM API keys.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pandas as pd
from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.calibration import backends, posterior, priors as priors_mod, refiners
from abm_auto.calibration.simulator import SimulatorWrapper, infer_targets
from abm_auto.calibration.summary_stats import SummaryStats, full_trajectory
from abm_auto.calibration.types import CalibrationResult, Fidelity

console = Console()


_DEFAULT_MAX_SIMS = 100
# Extra evaluations for the local-refinement stage. Runs in addition to
# screening's budget — refinement serves a different purpose (downhill
# from screening's best) and shouldn't compete with screening's coverage.
_REFINE_EVALS = 50
# Default MF budget split when `use_multi_fidelity=True`.
# Coarse stage explores broadly at 0.4× ticks; medium stage refines on
# narrowed priors at 0.7× ticks. Refinement (NM) always runs at full.
_MF_COARSE_FRAC = 0.5
# Prior-narrowing factor: each side of the box shrinks to this fraction
# of the original width, centered on the previous stage's best_params.
# 0.5 (not 0.25) hedges against bad coarse calls — initial cross-domain
# run with 0.25 missed SIR's true optimum after coarse landed in a
# different basin. See ADR-008 for the tuning rationale.
_MF_NARROW_FACTOR = 0.5


def _narrow_priors(
    priors: dict[str, dict],
    around: dict[str, float],
    factor: float = _MF_NARROW_FACTOR,
) -> dict[str, dict]:
    """Shrink prior boxes around a center point for the next MF stage.

    For each param, the new range is `center ± width * factor / 2`, clipped
    to the original [min, max]. Params missing from `around` retain their
    original prior — this keeps the schedule robust when a backend silently
    drops a param.

    Choosing factor=0.25 narrows the box to 25% of the original width,
    which is the empirically robust trade-off between trusting the coarse
    stage (small factor) and hedging against bad coarse calls (factor → 1).
    """
    out: dict[str, dict] = {}
    for name, prior in priors.items():
        lo = float(prior["min"])
        hi = float(prior["max"])
        width = hi - lo
        if name not in around or width <= 0:
            out[name] = {"min": lo, "max": hi}
            continue
        center = float(around[name])
        half = width * factor / 2
        new_lo = max(lo, center - half)
        new_hi = min(hi, center + half)
        if new_hi - new_lo < width * 0.01:  # degenerate, fall back
            out[name] = {"min": lo, "max": hi}
        else:
            out[name] = {"min": new_lo, "max": new_hi}
    return out


def _run_screen_with_fallback(
    priors: dict[str, dict],
    targets: list[str],
    obs_stats,
    simulator: SimulatorWrapper,
    budget: int,
) -> CalibrationResult:
    """RF → PyMC → ABC fallback chain. Returns the first backend that succeeds.

    Factored from the original `fit()` so MF can call it per-stage without
    duplicating the cascade.
    """
    screen_result = None
    if backends.HAS_SKLEARN:
        try:
            screen_result = backends.run_rf(priors, targets, obs_stats, simulator, budget)
        except Exception as e:
            console.print(f"  [yellow]⚠ RF backend failed ({e}) — trying next[/yellow]")
    if screen_result is None and backends.HAS_PYMC:
        try:
            screen_result = backends.run_pymc(priors, targets, obs_stats, simulator, budget)
        except Exception as e:
            console.print(f"  [yellow]⚠ PyMC backend failed ({e}) — trying next[/yellow]")
    if screen_result is None:
        screen_result = backends.run_abc(priors, targets, obs_stats, simulator, budget)
    return screen_result


def fit(
    simulator: SimulatorWrapper,
    priors: dict[str, dict],
    observed: pd.DataFrame,
    targets: list[str],
    max_sims: int = _DEFAULT_MAX_SIMS,
    refine_evals: int = _REFINE_EVALS,
    summary_fn: SummaryStats = full_trajectory,
    use_multi_fidelity: bool = False,
) -> CalibrationResult:
    """Two- or three-stage Bayesian calibration.

    Pure function — no workspace, no I/O, no LLM. The simulator argument
    encapsulates how to run the model; the rest is screening + refinement.

    When `use_multi_fidelity=True`, the screening budget splits 50/50
    into coarse (Fidelity.coarse() = 0.4× periods) and medium (Fidelity.medium()
    = 0.7× periods) stages, with priors narrowed ±50% around coarse's best
    for the medium stage. Final Nelder-Mead refinement always runs at full
    fidelity.

    **MF is off by default** because empirical wall savings on lean
    handcrafted_model sims are negligible (subprocess startup + engine
    import dominate ~3-4s/sim; 0.4× periods saves ~0.25s). MF earns its
    keep on full-Pipeline runs where each sim is expensive (multi-seed
    observed, larger agent populations) — opt in explicitly there. See
    ADR-008.

    When `use_multi_fidelity=False` (default), runs like the pre-MF
    single-stage screening at full fidelity. This is the regression-safe
    path and the one cross-domain CI exercises.

    Args:
        simulator: SimulatorWrapper-like callable target.
        priors: {param_name: {"min": float, "max": float}} from spec.
        observed: DataFrame of empirical observations (must contain `targets`).
        targets: List of column names common to obs and sim outputs.
        max_sims: Total screening budget across all MF stages (default 100).
        refine_evals: Budget for Nelder-Mead refinement (default 50, on top).
        summary_fn: Reducer from DataFrame → fixed-length stats vector.
        use_multi_fidelity: Default False. Set True to enable two-stage
            MF screening — see ADR-008 for the trade-offs.
    """
    simulator.summary_fn = summary_fn
    # Pin sim output shape to observed shape — RF backend's
    # np.array(X) refuses non-uniform feature lengths across samples
    # (off-by-one tick recording can cause some sims to write 251 rows
    # vs 250). Truncating mid-flight is the simplest defense. Padding
    # short coarse-fidelity sims with the last-row value is also handled
    # here (see _align_rows in simulator.py).
    simulator.expected_rows = len(observed)
    obs_stats = summary_fn(observed, targets)

    # ── Screening (single- or multi-fidelity) ──
    if use_multi_fidelity:
        screen_result = _run_mf_screen(priors, targets, obs_stats, simulator, max_sims)
    else:
        simulator.fidelity = None
        console.print("  [dim]Stage 1 (screen, single-fidelity): RF / PyMC / ABC cascade[/dim]")
        screen_result = _run_screen_with_fallback(priors, targets, obs_stats, simulator, max_sims)

    # ── Refinement always at full fidelity, regardless of MF setting ──
    simulator.fidelity = Fidelity.full() if use_multi_fidelity else None
    result = screen_result
    if screen_result.ok:
        try:
            console.print(f"  [dim]Stage 2 (refine): Nelder-Mead from {screen_result.backend}'s best[/dim]")
            refine_result = refiners.nelder_mead_refine(
                start_params=screen_result.best_params,
                priors=priors,
                targets=targets,
                obs_stats=obs_stats,
                simulator=simulator,
                max_evals=refine_evals,
            )
            if refine_result.ok:
                result = CalibrationResult(
                    ok=True,
                    backend=f"{screen_result.backend}+nelder-mead",
                    n_simulator_calls=(
                        screen_result.n_simulator_calls + refine_result.n_simulator_calls
                    ),
                    best_params=refine_result.best_params,
                    posterior_summary=screen_result.posterior_summary,
                )
        except Exception as e:
            console.print(f"  [yellow]⚠ NM refinement failed ({e}) — using screening result[/yellow]")

    # Restore scenario CSV's `periods` to base so downstream phases
    # (posterior.apply_best_params, run_final_validation_sim) see the
    # canonical sim length, not whichever stage's scaled value got left
    # behind. No-op when MF didn't run or no `periods` column exists.
    if hasattr(simulator, "restore_periods_to_base"):
        simulator.restore_periods_to_base()

    return result


def _run_mf_screen(
    priors: dict[str, dict],
    targets: list[str],
    obs_stats,
    simulator: SimulatorWrapper,
    max_sims: int,
) -> CalibrationResult:
    """Multi-fidelity screening: coarse RF → narrowed medium RF.

    Returns the medium-stage result when both stages succeed; falls back
    to the coarse result on medium failure, and to a non-ok result if
    both fail. The simulator's `.fidelity` is left as `Fidelity.full()`
    on return so callers (e.g., NM refinement) don't inherit a stale
    coarse setting.

    Budget allocation:
      - Coarse: ⌈max_sims × 0.6⌉, but at least 10 sims (RF needs a few
        samples to build any signal at all).
      - Medium: max_sims − coarse_budget, also clamped to ≥ 10.
    """
    coarse_budget = max(10, int(max_sims * _MF_COARSE_FRAC))
    medium_budget = max(10, max_sims - coarse_budget)

    # Stage A: coarse RF on full priors.
    simulator.fidelity = Fidelity.coarse()
    console.print(
        f"  [dim]MF Stage A (coarse, periods×{Fidelity.coarse().periods_scale:.1f}, "
        f"{coarse_budget} sims): RF / PyMC / ABC cascade[/dim]"
    )
    coarse_result = _run_screen_with_fallback(priors, targets, obs_stats, simulator, coarse_budget)

    if not coarse_result.ok:
        console.print("  [yellow]⚠ Coarse stage failed; skipping medium stage[/yellow]")
        simulator.fidelity = Fidelity.full()
        return coarse_result

    # Stage B: medium RF on priors narrowed around coarse's best.
    narrowed = _narrow_priors(priors, coarse_result.best_params, factor=_MF_NARROW_FACTOR)
    simulator.fidelity = Fidelity.medium()
    console.print(
        f"  [dim]MF Stage B (medium, periods×{Fidelity.medium().periods_scale:.1f}, "
        f"{medium_budget} sims, priors narrowed ×{_MF_NARROW_FACTOR}): RF / PyMC / ABC[/dim]"
    )
    medium_result = _run_screen_with_fallback(narrowed, targets, obs_stats, simulator, medium_budget)

    simulator.fidelity = Fidelity.full()
    if not medium_result.ok:
        console.print("  [yellow]⚠ Medium stage failed; falling back to coarse result[/yellow]")
        return coarse_result
    # Combine for accurate total sim count
    return CalibrationResult(
        ok=True,
        backend=f"mf({coarse_result.backend}→{medium_result.backend})",
        n_simulator_calls=coarse_result.n_simulator_calls + medium_result.n_simulator_calls,
        best_params=medium_result.best_params,
        posterior_summary=medium_result.posterior_summary,
    )


def fit_from_files(
    model_dir: Path | str,
    observed_csv: Path | str,
    params_specs: list[dict],
    targets: list[str],
    max_sims: int = _DEFAULT_MAX_SIMS,
    refine_evals: int = _REFINE_EVALS,
    summary_fn: SummaryStats = full_trajectory,
    workspace_name: Optional[str] = None,
    timeout: int = 120,
    use_multi_fidelity: bool = False,
):
    """Standalone calibration — no LLM, no Pipeline phases.

    Builds a transient Workspace + Executor + SimulatorWrapper from paths,
    then calls `fit`. Returns `(CalibrationResult, Workspace)` so the caller
    can run a final validation sim, score MSE, or write further artifacts.

    Use this for benchmarks, regression tests, and any direct calibration
    that doesn't need the LLM-mediated Pipeline phases.

    Args:
        model_dir: Path to the model directory (contains main.py and
                   data/input/SimulatorScenarios.csv).
        observed_csv: Path to observed.csv with `tick` + target columns.
        params_specs: List of {"name": str, "min": float, "max": float} —
                      one per calibration parameter.
        targets: List of target column names (e.g. ["susceptible", "infected"]).
        max_sims, refine_evals, summary_fn: Same semantics as `fit`.
        workspace_name: Optional name for the transient workspace (defaults
                        to a timestamped slug).
        timeout: Per-sim subprocess timeout in seconds.

    Returns:
        Tuple of (CalibrationResult, Workspace). Ignore the workspace if
        you only need best_params: `result, _ = fit_from_files(...)`.
    """
    import shutil

    from abm_auto.runner.executor import Executor
    from abm_auto.runner.workspace import Workspace

    model_dir = Path(model_dir)
    observed_csv = Path(observed_csv)

    name = workspace_name or f"calibration_standalone_{int(time.time())}"
    ws = Workspace.create(name=name)

    shutil.copytree(model_dir, ws.model_dir, dirs_exist_ok=True)

    # Wipe any stale output from a previous direct run of the example
    stale_output = ws.model_dir / "data" / "output"
    if stale_output.exists():
        shutil.rmtree(stale_output)

    priors = {
        s["name"]: {"min": float(s["min"]), "max": float(s["max"])}
        for s in params_specs
        if "name" in s and s.get("min") is not None and s.get("max") is not None
    }
    observed = pd.read_csv(observed_csv)

    executor = Executor(ws, timeout=timeout)
    simulator = SimulatorWrapper(
        ws, executor,
        summary_fn=summary_fn,
        expected_rows=len(observed),
    )

    result = fit(
        simulator, priors, observed, targets,
        max_sims, refine_evals, summary_fn,
        use_multi_fidelity=use_multi_fidelity,
    )
    return result, ws


class BayesianCalibrator(BaseAgent):
    """Phase 6 alternative: Bayesian calibration against observed data.

    Replaces the heuristic OptimizerAgent when spec.has_calibration_data is True.

    Backwards-compat: public signature `run(executor, spec, max_sims)` returning
    CalibrationResult is unchanged from the pre-decomposition god class.
    """

    def run(self, executor, spec=None, max_sims: int = _DEFAULT_MAX_SIMS) -> CalibrationResult:
        console.print("[bold cyan]Phase 6 (alt): Bayesian Calibration...[/bold cyan]")

        # ── Activation gates ──
        if not (spec and spec.has_calibration_data):
            return _skip("spec.has_calibration_data is False")

        obs_path = self._resolve_observed_path(spec)
        if obs_path is None or not obs_path.exists():
            console.print(
                f"  [yellow]⚠ Observed data not found "
                f"(expected: {spec.calibration_data_path or 'data/observed.csv'}) — "
                f"falling back to OptimizerAgent[/yellow]"
            )
            return _skip(f"Observed data path not found: {spec.calibration_data_path}")

        observed = pd.read_csv(obs_path)
        targets = spec.calibration_targets or infer_targets(observed)
        console.print(f"  [dim]Observed data: {obs_path.name} ({len(observed)} rows)[/dim]")
        console.print(f"  [dim]Calibration targets: {targets}[/dim]")

        # ── Build priors (allowlist + spec range overrides) ──
        allowlist = list(spec.calibration_params) if spec.calibration_params else None
        spec_overrides: dict[str, dict] = {}
        for s in (getattr(spec, "calibration_param_specs", None) or []):
            name = s.get("name")
            lo, hi = s.get("min"), s.get("max")
            if name and lo is not None and hi is not None:
                try:
                    spec_overrides[name] = {"min": float(lo), "max": float(hi)}
                except (TypeError, ValueError):
                    pass

        simulator = SimulatorWrapper(
            self.workspace, executor,
            expected_rows=len(observed),
        )
        prior_dict = priors_mod.build_priors(
            simulator.scenario_csv_path,
            allowlist=allowlist,
            spec_overrides=spec_overrides,
        )

        if not prior_dict:
            console.print("  [yellow]⚠ Could not infer parameter priors — falling back[/yellow]")
            reason = (
                f"None of the requested calibration_params {allowlist} found "
                f"as numeric columns in SimulatorScenarios.csv"
                if allowlist
                else "No tunable parameters found in scenario CSV"
            )
            return _skip(reason)

        scope = f"{len(prior_dict)} of {len(allowlist)} requested" if allowlist else f"{len(prior_dict)} (all numeric)"
        console.print(f"  [dim]Parameters under inference: {list(prior_dict.keys())} ({scope})[/dim]")

        # Delegate the actual calibration to the standalone `fit` function.
        # The orchestrator's job from here on is only side effects: artifact
        # writes, validation sim, LLM report.
        result = fit(simulator, prior_dict, observed, targets, max_sims)

        # ── Post-processing ──
        if result.ok:
            posterior.write_posterior_summary(self.workspace, result)
            posterior.write_best_params(self.workspace, result)
            posterior.apply_best_params(self.workspace, simulator, result.best_params)

            final_csv = posterior.run_final_validation_sim(simulator, result.best_params, self.workspace)
            if final_csv is not None:
                console.print(f"  [dim]Final validation sim → {final_csv.name}[/dim]")

            # Diagnostics (α/β/ε) — observability, never blocks pipeline.
            # ~15s overhead at end of calibration on a 3-param problem.
            # `obs_stats` is local to `fit()`; recompute it here using
            # whatever summary_fn the simulator carries (set by fit() before
            # screening). Default: full_trajectory.
            console.print("  [dim]Running diagnostics (profile / Fisher / execution fidelity)...[/dim]")
            try:
                story_text = self.workspace.read_story()
            except Exception:
                story_text = ""
            diag_summary_fn = getattr(simulator, "summary_fn", full_trajectory)
            obs_stats_for_diag = diag_summary_fn(observed, targets)
            diagnostics_md = posterior.run_diagnostics(
                self.workspace,
                simulator,
                prior_dict,
                result.best_params,
                targets,
                obs_stats_for_diag,
                summary_fn=diag_summary_fn,
                story_text=story_text,
                final_sim_csv=final_csv,
                call_llm=self.call_llm,
            )

            posterior.write_calibration_report(
                self.workspace, result,
                call_llm=self.call_llm,
                diagnostics_md=diagnostics_md,
            )

            console.print(
                f"  [green]✓ Calibration complete[/green] "
                f"[dim]({result.backend}, {result.n_simulator_calls} sims)[/dim]"
            )
            self._audit_success(result)
        else:
            self._audit_failure(result)

        return result

    # ── helpers (small enough to stay on the class) ──

    def _resolve_observed_path(self, spec) -> Optional[Path]:
        if spec.calibration_data_path:
            p = self.workspace.path / spec.calibration_data_path
            if p.exists():
                return p
            p_abs = Path(spec.calibration_data_path)
            if p_abs.exists():
                return p_abs
        p = self.workspace.path / "data" / "observed.csv"
        return p if p.exists() else None

    def _audit_success(self, result: CalibrationResult) -> None:
        try:
            self.workspace.audit.info(
                phase="Phase 6 (calibration)",
                text=(
                    f"Bayesian calibration complete via {result.backend}; "
                    f"{result.n_simulator_calls} simulator calls, "
                    f"{len(result.best_params)} params fit"
                ),
                actor="BayesianCalibrator",
                structured={
                    "backend": result.backend,
                    "n_simulator_calls": result.n_simulator_calls,
                    "best_params": result.best_params,
                },
            )
        except Exception:
            pass

    def _audit_failure(self, result: CalibrationResult) -> None:
        try:
            self.workspace.audit.raise_issue(
                phase="Phase 6 (calibration)",
                severity="MEDIUM",
                text=(
                    f"Bayesian calibration skipped/failed via {result.backend}: "
                    f"{result.reason}. Falling back to heuristic optimizer."
                ),
                actor="BayesianCalibrator",
                structured={"backend": result.backend, "reason": result.reason},
            )
        except Exception:
            pass


def _skip(reason: str) -> CalibrationResult:
    """Construct a non-ok CalibrationResult for the skip paths."""
    return CalibrationResult(
        ok=False,
        backend="skipped",
        n_simulator_calls=0,
        best_params={},
        posterior_summary=pd.DataFrame(),
        reason=reason,
    )
