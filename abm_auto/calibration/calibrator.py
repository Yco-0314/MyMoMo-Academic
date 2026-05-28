"""BayesianCalibrator orchestrator.

Glues priors / simulator / backend / posterior into the pipeline-facing
agent. After the 2026-05-25 decomposition this is ~80 lines of pure
orchestration; all algorithm-specific code lives in the sibling modules.

Activation contract (set by Pipeline._should_calibrate()):
  - spec.has_calibration_data is True
  - workspace/data/observed.csv (or spec.calibration_data_path) exists
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.calibration import backends, posterior, priors as priors_mod, refiners
from abm_auto.calibration.simulator import SimulatorWrapper, infer_targets
from abm_auto.calibration.summary_stats import full_trajectory
from abm_auto.calibration.types import CalibrationResult

console = Console()


_DEFAULT_MAX_SIMS = 100
# Extra evaluations for the local-refinement stage. Runs in addition to
# screening's budget — refinement serves a different purpose (downhill
# from screening's best) and shouldn't compete with screening's coverage.
_REFINE_EVALS = 50


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

        simulator = SimulatorWrapper(self.workspace, executor)
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

        # Use full_trajectory as the summary (preserves per-tick info, gives
        # ABC/NM a sharp loss surface). Pass the same fn into the simulator
        # so sim_stats and obs_stats live in the same vector space.
        summary_fn = full_trajectory
        simulator.summary_fn = summary_fn
        obs_stats = summary_fn(observed, targets)

        # ── Stage 1: Screening (broad prior coverage) ──
        # Preference order: RF > PyMC > ABC.
        # RF (Carrella 2021): consistently best in cross-validated benchmarks
        #   for ABM calibration; uses ALL successful sims (not top 20% like ABC).
        # PyMC SMC: theoretically principled but expensive (particle filter).
        # ABC rejection: simple fallback, always available (numpy only).
        screen_result = None
        if backends.HAS_SKLEARN:
            try:
                console.print("  [dim]Stage 1 (screen): Random Forest regression[/dim]")
                screen_result = backends.run_rf(prior_dict, targets, obs_stats, simulator, max_sims)
            except Exception as e:
                console.print(f"  [yellow]⚠ RF backend failed ({e}) — trying next[/yellow]")
        if screen_result is None and backends.HAS_PYMC:
            try:
                console.print("  [dim]Stage 1 (screen): PyMC SMC[/dim]")
                screen_result = backends.run_pymc(prior_dict, targets, obs_stats, simulator, max_sims)
            except Exception as e:
                console.print(f"  [yellow]⚠ PyMC backend failed ({e}) — trying next[/yellow]")
        if screen_result is None:
            console.print("  [dim]Stage 1 (screen): ABC rejection[/dim]")
            screen_result = backends.run_abc(prior_dict, targets, obs_stats, simulator, max_sims)

        # ── Stage 2: Refinement (local descent from screening's best point) ──
        # NM walks downhill on ||sim - obs|| from screening's best_params,
        # closing the ~10-20 distance gap between best-of-N-uniform-draws and
        # the true basin. The screening posterior_summary is carried forward.
        result = screen_result
        if screen_result.ok:
            try:
                console.print(f"  [dim]Stage 2 (refine): Nelder-Mead from {screen_result.backend}'s best[/dim]")
                refine_result = refiners.nelder_mead_refine(
                    start_params=screen_result.best_params,
                    priors=prior_dict,
                    targets=targets,
                    obs_stats=obs_stats,
                    simulator=simulator,
                    max_evals=_REFINE_EVALS,
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

        # ── Post-processing ──
        if result.ok:
            posterior.write_posterior_summary(self.workspace, result)
            posterior.write_best_params(self.workspace, result)
            posterior.write_calibration_report(self.workspace, result, call_llm=self.call_llm)
            posterior.apply_best_params(self.workspace, simulator, result.best_params)

            final_csv = posterior.run_final_validation_sim(simulator, result.best_params, self.workspace)
            if final_csv is not None:
                console.print(f"  [dim]Final validation sim → {final_csv.name}[/dim]")

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
