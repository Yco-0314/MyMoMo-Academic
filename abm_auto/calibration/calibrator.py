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
from abm_auto.calibration.types import CalibrationResult

console = Console()


_DEFAULT_MAX_SIMS = 100
# Extra evaluations for the local-refinement stage. Runs in addition to
# screening's budget — refinement serves a different purpose (downhill
# from screening's best) and shouldn't compete with screening's coverage.
_REFINE_EVALS = 50


def fit(
    simulator: SimulatorWrapper,
    priors: dict[str, dict],
    observed: pd.DataFrame,
    targets: list[str],
    max_sims: int = _DEFAULT_MAX_SIMS,
    refine_evals: int = _REFINE_EVALS,
    summary_fn: SummaryStats = full_trajectory,
) -> CalibrationResult:
    """Two-stage Bayesian calibration: screen, then locally refine.

    Pure function — no workspace, no I/O, no LLM. The simulator argument
    encapsulates how to run the model; the rest is screening + refinement.

    Args:
        simulator: SimulatorWrapper-like callable target.
        priors: {param_name: {"min": float, "max": float}} from spec.
        observed: DataFrame of empirical observations (must contain `targets`).
        targets: List of column names common to obs and sim outputs.
        max_sims: Budget for screening stage (default 100).
        refine_evals: Budget for Nelder-Mead refinement (default 50, on top).
        summary_fn: Reducer from DataFrame → fixed-length stats vector.
    """
    simulator.summary_fn = summary_fn
    # Pin sim output shape to observed shape — RF backend's
    # np.array(X) refuses non-uniform feature lengths across samples
    # (off-by-one tick recording can cause some sims to write 251 rows
    # vs 250). Truncating mid-flight is the simplest defense.
    simulator.expected_rows = len(observed)
    obs_stats = summary_fn(observed, targets)

    # ── Stage 1: Screening (broad prior coverage) ──
    # Preference order: RF > PyMC > ABC.
    screen_result = None
    if backends.HAS_SKLEARN:
        try:
            console.print("  [dim]Stage 1 (screen): Random Forest regression[/dim]")
            screen_result = backends.run_rf(priors, targets, obs_stats, simulator, max_sims)
        except Exception as e:
            console.print(f"  [yellow]⚠ RF backend failed ({e}) — trying next[/yellow]")
    if screen_result is None and backends.HAS_PYMC:
        try:
            console.print("  [dim]Stage 1 (screen): PyMC SMC[/dim]")
            screen_result = backends.run_pymc(priors, targets, obs_stats, simulator, max_sims)
        except Exception as e:
            console.print(f"  [yellow]⚠ PyMC backend failed ({e}) — trying next[/yellow]")
    if screen_result is None:
        console.print("  [dim]Stage 1 (screen): ABC rejection[/dim]")
        screen_result = backends.run_abc(priors, targets, obs_stats, simulator, max_sims)

    # ── Stage 2: Refinement (local descent from screening's best point) ──
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

    return result


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

    result = fit(simulator, priors, observed, targets, max_sims, refine_evals, summary_fn)
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
