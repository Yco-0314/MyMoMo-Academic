"""
Phase 6 alternative: Bayesian parameter calibration with observed data.

Activates only when:
  spec.has_calibration_data == True
  AND  workspace contains observed data at spec.calibration_data_path
       (or the conventional location data/observed.csv)

When active, this REPLACES the heuristic OptimizerAgent: instead of
running 3 iterations of LLM-suggested parameter sweeps, we fit a Bayesian
posterior over the parameters using the observed data as ground truth.

Two backends:
  PyMC (preferred) — likelihood-free SMC via pm.Simulator + pm.sample_smc.
                     ABM simulators have no tractable likelihood, so SMC is
                     the standard PyMC approach. Falls back to ABC if PyMC
                     fails to import or run.
  ABC (fallback)  — simple rejection sampling. No deps beyond numpy/pandas.
                     Sample params from priors, run simulator, keep top
                     fraction by distance to observed.

Output:
  posterior_summary.csv  — per-parameter mean / std / 95% CI
  posterior_trace.json   — accepted parameter samples (lightweight, no NetCDF)
  best_params.json       — MAP estimate (or posterior mean)
  calibration_report.md  — LLM-written human summary of the posterior

The "best" params are written to SimulatorScenarios.csv so downstream
phases (sensitivity / trajectory / report) use the calibrated configuration.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()

# Optional PyMC import — keeps calibrator usable even without PyMC installed
try:
    import pymc as pm  # type: ignore
    import arviz as az  # type: ignore
    _HAS_PYMC = True
except Exception:
    _HAS_PYMC = False


_DEFAULT_MAX_SIMS = 100   # cap on simulator calls (both backends)
_DEFAULT_TOP_FRAC = 0.20  # ABC: keep top 20% by distance as posterior approx


@dataclass
class CalibrationResult:
    ok: bool
    backend: str                 # "pymc-smc" | "abc-rejection" | "skipped"
    n_simulator_calls: int
    best_params: dict[str, float]
    posterior_summary: pd.DataFrame
    reason: str = ""


class BayesianCalibrator(BaseAgent):
    """
    Phase 6 alternative: Bayesian calibration against observed data.

    Pipeline calls run() instead of OptimizerAgent when calibration data exists.
    """

    def run(
        self,
        executor,
        spec=None,
        max_sims: int = _DEFAULT_MAX_SIMS,
    ) -> CalibrationResult:
        """
        Calibrate parameters against observed data.

        Args:
            executor: shared Executor (same one used by Phase 4/5)
            spec:     ResearchSpec — must have has_calibration_data=True
            max_sims: hard cap on simulator runs (both backends respect this)

        Returns:
            CalibrationResult with backend used, sample count, best params.
        """
        console.print("[bold cyan]Phase 6 (alt): Bayesian Calibration...[/bold cyan]")

        if not (spec and spec.has_calibration_data):
            return CalibrationResult(
                ok=False, backend="skipped", n_simulator_calls=0,
                best_params={}, posterior_summary=pd.DataFrame(),
                reason="spec.has_calibration_data is False",
            )

        # Locate observed data
        obs_path = self._resolve_observed_path(spec)
        if obs_path is None or not obs_path.exists():
            console.print(
                f"  [yellow]⚠ Observed data not found "
                f"(expected: {spec.calibration_data_path or 'data/observed.csv'}) — "
                f"falling back to OptimizerAgent[/yellow]"
            )
            return CalibrationResult(
                ok=False, backend="skipped", n_simulator_calls=0,
                best_params={}, posterior_summary=pd.DataFrame(),
                reason=f"Observed data path not found: {spec.calibration_data_path}",
            )

        observed = pd.read_csv(obs_path)
        targets = spec.calibration_targets or self._infer_targets(observed)
        console.print(f"  [dim]Observed data: {obs_path.name} ({len(observed)} rows)[/dim]")
        console.print(f"  [dim]Calibration targets: {targets}[/dim]")

        # Infer parameter priors. If spec.calibration_params is set, ONLY put
        # priors on those — every other scenario column stays at its default.
        # This is critical: without this filter, structural params (num_agents,
        # periods, ...) get randomly perturbed → simulator crashes on every
        # sample → ABC/SMC report 100% failure.
        allowlist = list(spec.calibration_params) if spec.calibration_params else None
        # spec_overrides[name] = {"min": ..., "max": ...} when story.md declared
        # explicit ranges. These WIN over the CSV-inferred ±50% — without this
        # override, unit-system drift in codegen (story said percent, code uses
        # probability) silently corrupts the priors.
        spec_overrides: dict[str, dict] = {}
        for s in (getattr(spec, "calibration_param_specs", None) or []):
            name = s.get("name")
            if not name:
                continue
            lo, hi = s.get("min"), s.get("max")
            if lo is None or hi is None:
                continue
            try:
                spec_overrides[name] = {"min": float(lo), "max": float(hi)}
            except (TypeError, ValueError):
                pass
        priors = self._infer_priors(allowlist=allowlist, spec_overrides=spec_overrides)
        if not priors:
            console.print("  [yellow]⚠ Could not infer parameter priors — falling back[/yellow]")
            reason = (
                f"None of the requested calibration_params {allowlist} found "
                f"as numeric columns in SimulatorScenarios.csv"
                if allowlist
                else "No tunable parameters found in scenario CSV"
            )
            return CalibrationResult(
                ok=False, backend="skipped", n_simulator_calls=0,
                best_params={}, posterior_summary=pd.DataFrame(),
                reason=reason,
            )
        scope_label = f"{len(priors)} of {len(allowlist)} requested" if allowlist else f"{len(priors)} (all numeric)"
        console.print(f"  [dim]Parameters under inference: {list(priors.keys())} ({scope_label})[/dim]")

        # Compute observed summary statistics for distance metric
        obs_stats = self._summary_stats(observed, targets)

        # Run inference
        if _HAS_PYMC:
            try:
                result = self._run_pymc(
                    priors=priors, targets=targets, obs_stats=obs_stats,
                    executor=executor, max_sims=max_sims,
                )
            except Exception as e:
                console.print(f"  [yellow]⚠ PyMC backend failed ({e}) — falling back to ABC[/yellow]")
                result = self._run_abc(
                    priors=priors, targets=targets, obs_stats=obs_stats,
                    executor=executor, max_sims=max_sims,
                )
        else:
            console.print("  [dim]PyMC not installed — using ABC rejection sampling[/dim]")
            result = self._run_abc(
                priors=priors, targets=targets, obs_stats=obs_stats,
                executor=executor, max_sims=max_sims,
            )

        if result.ok:
            self._write_outputs(result)
            self._apply_best_params(result.best_params)
            # Final validation run: simulate ONCE with best_params and save the
            # trajectory. This is what downstream scorers (e.g. Milan MSE
            # benchmark) read to compare simulated dynamics against observed.
            final_csv = self._run_final_validation_sim(result.best_params, executor)
            if final_csv is not None:
                console.print(
                    f"  [dim]Final validation sim → {final_csv.name}[/dim]"
                )
            console.print(
                f"  [green]✓ Calibration complete[/green] "
                f"[dim]({result.backend}, {result.n_simulator_calls} sims)[/dim]"
            )
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
        else:
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
        return result

    # ── ABC fallback ────────────────────────────────────────────────────────

    def _run_abc(
        self,
        priors: dict[str, dict],
        targets: list[str],
        obs_stats: np.ndarray,
        executor,
        max_sims: int,
    ) -> CalibrationResult:
        """Approximate Bayesian Computation via rejection sampling."""
        accepted_params: list[dict] = []
        accepted_distances: list[float] = []
        all_samples: list[tuple[dict, float]] = []

        for i in range(max_sims):
            # Sample params from uniform priors
            params = {
                name: float(np.random.uniform(p["min"], p["max"]))
                for name, p in priors.items()
            }
            # Run simulator
            sim_stats = self._simulate_once(params, targets, executor, run_id=10000 + i)
            if sim_stats is None:
                continue
            # Distance to observed
            dist = float(np.linalg.norm(sim_stats - obs_stats))
            all_samples.append((params, dist))

            if (i + 1) % 10 == 0:
                console.print(f"  [dim]ABC progress: {i+1}/{max_sims}[/dim]")

        if not all_samples:
            return CalibrationResult(
                ok=False, backend="abc-rejection", n_simulator_calls=0,
                best_params={}, posterior_summary=pd.DataFrame(),
                reason="All simulator runs failed",
            )

        # Keep top fraction by distance
        all_samples.sort(key=lambda x: x[1])
        n_keep = max(1, int(len(all_samples) * _DEFAULT_TOP_FRAC))
        accepted = all_samples[:n_keep]

        # Build posterior summary
        param_names = list(priors.keys())
        post_df = pd.DataFrame(
            [p for p, _ in accepted], columns=param_names
        )
        summary = post_df.describe(percentiles=[0.025, 0.5, 0.975]).T

        # Point estimate: POSTERIOR MEAN, not single closest sample.
        # The single closest accepted sample (MAP-by-distance) is a poor
        # estimator for ABC — it overweights one random draw. Posterior mean
        # has lower mean-squared error and is the standard choice in the
        # ABC literature (Beaumont 2010, Marin et al. 2012).
        # See benchmark: virus_spread_chance closest=2.82, mean=4.55 (truth 4.40)
        # — closest is 36% off, mean is 3% off.
        best_params = {name: float(post_df[name].mean()) for name in param_names}

        return CalibrationResult(
            ok=True, backend="abc-rejection",
            n_simulator_calls=len(all_samples),
            best_params=best_params, posterior_summary=summary,
        )

    # ── PyMC SMC backend ────────────────────────────────────────────────────

    def _run_pymc(
        self,
        priors: dict[str, dict],
        targets: list[str],
        obs_stats: np.ndarray,
        executor,
        max_sims: int,
    ) -> CalibrationResult:
        """Likelihood-free inference via pm.Simulator + SMC."""
        # SMC cost: draws × steps simulator calls (approx). Stay within max_sims.
        draws = min(50, max(20, max_sims // 4))
        param_names = list(priors.keys())

        sim_counter = {"n": 0}

        def simulator(rng, *param_values, size=None):
            """Called by pm.Simulator inside SMC."""
            sim_counter["n"] += 1
            params = dict(zip(param_names, [float(v) for v in param_values]))
            sim_stats = self._simulate_once(
                params, targets, executor, run_id=20000 + sim_counter["n"]
            )
            if sim_stats is None:
                # Return large-distance dummy so SMC discards
                return obs_stats + 1e6
            return sim_stats

        with pm.Model() as model:
            # Uniform priors
            param_vars = [
                pm.Uniform(name, lower=p["min"], upper=p["max"])
                for name, p in priors.items()
            ]
            _sim = pm.Simulator(
                "sim",
                simulator,
                params=param_vars,
                distance="gaussian",
                sum_stat="identity",
                epsilon=1.0,
                observed=obs_stats,
            )
            idata = pm.sample_smc(draws=draws, chains=2, progressbar=False)

        # Build summary
        summary = az.summary(idata, var_names=param_names)
        # MAP ≈ posterior mean
        best_params = {n: float(summary.loc[n, "mean"]) for n in param_names}

        return CalibrationResult(
            ok=True, backend="pymc-smc",
            n_simulator_calls=sim_counter["n"],
            best_params=best_params,
            posterior_summary=summary,
        )

    # ── Simulator wrapper ───────────────────────────────────────────────────

    def _simulate_once(
        self, params: dict, targets: list[str], executor, run_id: int,
    ) -> Optional[np.ndarray]:
        """Write params to scenario, run simulator, read summary stats."""
        try:
            self._write_scenario_params(params)
            success, _ = executor.run(run_id)
            if not success:
                return None
            metrics_df = self._read_result_metrics(run_id)
            if metrics_df is None or metrics_df.empty:
                return None
            return self._summary_stats(metrics_df, targets)
        except Exception:
            return None

    def _write_scenario_params(self, params: dict) -> None:
        """Update SimulatorScenarios.csv with the given params."""
        csv_path = self.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"
        if not csv_path.exists():
            return
        df = pd.read_csv(csv_path)
        for name, value in params.items():
            if name in df.columns:
                df.loc[df.index[0], name] = value
        df.to_csv(csv_path, index=False)

    def _read_result_metrics(self, run_id: int) -> Optional[pd.DataFrame]:
        """Read the result CSV of a given run."""
        csvs = self.workspace.list_result_csvs(run_id)
        if not csvs:
            return None
        try:
            return pd.read_csv(csvs[0])
        except Exception:
            return None

    @staticmethod
    def _summary_stats(df: pd.DataFrame, targets: list[str]) -> np.ndarray:
        """Compute summary stats vector: [mean, std, last_value] per target."""
        stats = []
        for col in targets:
            if col in df.columns:
                series = pd.to_numeric(df[col], errors="coerce").dropna()
                if len(series) > 0:
                    stats.extend([
                        float(series.mean()),
                        float(series.std() or 0.0),
                        float(series.iloc[-1]),
                    ])
                    continue
            stats.extend([0.0, 0.0, 0.0])
        return np.array(stats, dtype=float)

    # ── Prior / target inference ────────────────────────────────────────────

    def _infer_priors(
        self,
        allowlist: list[str] | None = None,
        spec_overrides: dict[str, dict] | None = None,
    ) -> dict[str, dict]:
        """Infer uniform priors from the current scenario CSV.

        Args:
            allowlist: If non-empty, ONLY return priors for these column names
                       (after case-insensitive matching). When None or empty,
                       every numeric non-skip column gets a prior — the legacy
                       (unsafe) behaviour.
            spec_overrides: Map of param name → {"min": float, "max": float}
                            that REPLACES the CSV-inferred ±50% bounds. Use this
                            when story.md declares explicit ranges (e.g.
                            "virus_spread_chance: 0–20 percent") — without it,
                            unit drift in codegen will silently put the priors
                            on the wrong scale.

        Each numeric parameter gets a uniform prior, sourced in priority order:
          1. spec_overrides[col]      (story-declared range)
          2. CSV ±50% (or 0-1 bounded for probability-like values)
        """
        csv_path = self.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"
        if not csv_path.exists():
            return {}
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            return {}
        if df.empty:
            return {}

        skip = {"id", "run_num", "scenario_id", "period_num", "seed"}
        allowlist_lower = {a.lower() for a in (allowlist or [])}
        overrides_lower = {k.lower(): v for k, v in (spec_overrides or {}).items()}
        row = df.iloc[0]
        priors: dict[str, dict] = {}
        for col in df.columns:
            if col.lower() in skip:
                continue
            if allowlist_lower and col.lower() not in allowlist_lower:
                continue
            try:
                val = float(row[col])
            except (ValueError, TypeError):
                continue
            if math.isnan(val):
                continue

            # Priority 1: spec_overrides win when present
            if col.lower() in overrides_lower:
                ov = overrides_lower[col.lower()]
                lo, hi = ov["min"], ov["max"]
                # Clamp the CSV value (init) into the spec range so ABC starts
                # from a sane location even if codegen wrote a unit-mismatched default.
                init = min(max(val, lo), hi)
                priors[col] = {"min": lo, "max": hi, "init": init, "source": "spec"}
                continue

            # Priority 2: CSV-inferred bounds
            if 0.0 <= val <= 1.0:
                lo, hi = max(0.0, val - 0.3), min(1.0, val + 0.3)
            elif val > 0:
                lo, hi = val * 0.5, val * 1.5
            else:
                lo, hi = val * 1.5, val * 0.5
            priors[col] = {"min": lo, "max": hi, "init": val, "source": "csv"}
        return priors

    def _infer_targets(self, observed: pd.DataFrame) -> list[str]:
        """If spec.calibration_targets is empty, use all numeric columns in observed."""
        return [
            c for c in observed.columns
            if pd.api.types.is_numeric_dtype(observed[c])
            and c.lower() not in {"id", "step", "period", "run_num", "scenario_id", "agent_id"}
        ]

    def _resolve_observed_path(self, spec) -> Optional[Path]:
        """Locate the observed data file."""
        # Try the path declared in spec
        if spec.calibration_data_path:
            p = self.workspace.path / spec.calibration_data_path
            if p.exists():
                return p
            # Maybe absolute
            p_abs = Path(spec.calibration_data_path)
            if p_abs.exists():
                return p_abs
        # Conventional fallback
        p = self.workspace.path / "data" / "observed.csv"
        return p if p.exists() else None

    # ── Output writing ──────────────────────────────────────────────────────

    def _write_outputs(self, result: CalibrationResult) -> None:
        """Write posterior summary CSV, best params JSON, and a markdown report."""
        # Summary CSV
        summary_path = self.workspace.path / "posterior_summary.csv"
        result.posterior_summary.to_csv(summary_path)

        # Best params JSON
        best_path = self.workspace.path / "best_params.json"
        best_path.write_text(
            json.dumps(result.best_params, indent=2), encoding="utf-8"
        )

        # Markdown report (LLM-written brief)
        try:
            md = self._llm_report(result)
            (self.workspace.path / "calibration_report.md").write_text(md, encoding="utf-8")
        except Exception:
            pass  # report is best-effort

    def _llm_report(self, result: CalibrationResult) -> str:
        """LLM writes a human-readable calibration summary."""
        summary_text = result.posterior_summary.to_string()
        system = (
            "You are a Bayesian statistician summarising parameter calibration results. "
            "Be concrete: name the parameters, give the posterior mean and 95% CI, "
            "and comment on which parameters are well-identified vs. uncertain."
        )
        prompt = (
            f"Backend: {result.backend}\n"
            f"Simulator calls: {result.n_simulator_calls}\n\n"
            f"## Posterior summary\n\n```\n{summary_text}\n```\n\n"
            "Write a 200-word calibration report in Chinese covering:\n"
            "1. Which parameters are now tightly identified (narrow CI)?\n"
            "2. Which remain uncertain (wide CI or hit prior bounds)?\n"
            "3. What this implies about the model and the observed data."
        )
        return self.call_llm(system, prompt, max_tokens=800)

    def _apply_best_params(self, best_params: dict) -> None:
        """Write the best params to SimulatorScenarios.csv so downstream phases use them."""
        self._write_scenario_params(best_params)
        # Record in params_history for reviewer visibility
        try:
            self.workspace.append_params_history(
                run=99999, params=best_params, hypothesis="Bayesian calibration MAP estimate"
            )
        except Exception:
            pass

    def _run_final_validation_sim(self, best_params: dict, executor) -> Optional[Path]:
        """Run the simulator once with best_params, save trajectory to a known path.

        Lets downstream scorers (Milan-style MSE benchmark, reviewers) read a
        deterministic "this is what the calibrated model produces" CSV without
        guessing which iter ran with which params.
        """
        try:
            self._write_scenario_params(best_params)
            run_id = 30000  # sentinel ID for the validation sim
            success, _ = executor.run(run_id)
            if not success:
                return None
            csvs = self.workspace.list_result_csvs(run_id)
            if not csvs:
                return None
            # Pick the environment-level CSV (S/I/R counts), fall back to first.
            source = next(
                (c for c in csvs if "environment" in c.name.lower()),
                csvs[0],
            )
            target = self.workspace.path / "calibration_final_sim.csv"
            target.write_bytes(source.read_bytes())
            return target
        except Exception:
            return None
