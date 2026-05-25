"""
SALib-based sensitivity analysis for ABM parameter exploration.

Replaces qualitative LLM guessing with statistically principled methods:
- Morris (screening): fast, identifies which parameters matter
- Sobol (variance decomposition): quantifies first-order + interaction effects

Workflow: define problem → generate samples → run simulations → compute indices → LLM interprets
"""
from __future__ import annotations
import json
import sys
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

# SALib is optional. The pipeline keeps working when it's missing — only
# the --sensitivity flag becomes a no-op (the agent raises a clear error).
try:
    from SALib.sample import morris as morris_sample, sobol as sobol_sample
    from SALib.analyze import morris as morris_analyze, sobol as sobol_analyze
    _HAS_SALIB = True
except Exception:
    morris_sample = sobol_sample = None
    morris_analyze = sobol_analyze = None
    _HAS_SALIB = False

from abm_auto.agents.base import BaseAgent
from abm_auto.runner.workspace import Workspace
from abm_auto.runner.executor import Executor

console = Console()


def _require_salib():
    if not _HAS_SALIB:
        raise ImportError(
            "SALib is not installed. Sensitivity analysis is unavailable. "
            "Install with: pip install SALib"
        )


class SensitivityAnalyzer(BaseAgent):
    """Runs SALib sensitivity analysis on ABM parameters."""

    def run(
        self,
        executor: Executor,
        method: str = "morris",
        n_trajectories: int = 10,
        metric_column: str | None = None,
        metric_file: str | None = None,
    ) -> dict:
        """
        Full sensitivity analysis pipeline.

        Args:
            executor: Simulation executor.
            method: "morris" (screening) or "sobol" (variance decomposition).
            n_trajectories: Number of Morris trajectories or Sobol N (base samples).
            metric_column: Column name in output CSV to use as response variable.
                          If None, LLM will pick the best candidate.
            metric_file: Which output CSV file to read metric from.
                        If None, uses the first CSV found.

        Returns:
            Dict with sensitivity indices and LLM interpretation.
        """
        _require_salib()
        console.print(f"[bold cyan]Sensitivity Analysis ({method.upper()})...[/bold cyan]")

        # 1. Define the problem from SimulatorScenarios.csv
        self._int_params = set()  # Track which params are integers
        problem, param_defaults = self._define_problem()
        if not problem["names"]:
            console.print("[yellow]No tunable parameters found in SimulatorScenarios.csv[/yellow]")
            return {}

        D = len(problem["names"])
        console.print(f"  [dim]Parameters ({D}): {problem['names']}[/dim]")
        console.print(f"  [dim]Bounds: {problem['bounds']}[/dim]")

        # 2. Generate samples — auto-scale N if not overridden
        # Morris: minimum N=4 per dimension for reliable screening (SALib default rule)
        # Sobol:  produces N×(2D+2) evaluations; need enough evaluations → N = max(req, 8)
        if method == "morris":
            # For Morris, the caller's n_trajectories is used as-is (≥4 recommended)
            N = max(n_trajectories, 4)
            samples = morris_sample.sample(problem, N=N)
        else:  # sobol
            # Auto-scale: ensure ≥ 50 total evaluations even for small D
            # Sobol total = N×(2D+2).  We want N×(2D+2) ≥ max(50, 8×D).
            min_evals = max(50, 8 * D)
            evals_per_N = 2 * D + 2
            N_min = max(1, (min_evals + evals_per_N - 1) // evals_per_N)  # ceiling div
            N = max(n_trajectories, N_min)
            if N != n_trajectories:
                console.print(
                    f"  [dim]Sobol N auto-scaled {n_trajectories} → {N} "
                    f"(D={D}, total evals={N*(2*D+2)})[/dim]"
                )
            samples = sobol_sample.sample(problem, N=N, calc_second_order=True)

        n_runs = len(samples)
        console.print(f"  [dim]Generated {n_runs} parameter combinations[/dim]")

        # 3. Run simulations for each sample
        Y = self._run_samples(
            executor, problem, samples, param_defaults,
            metric_column=metric_column, metric_file=metric_file,
        )

        if Y is None:
            console.print("[red]Could not extract metric from simulation outputs[/red]")
            return {}

        # 4. Compute sensitivity indices
        if method == "morris":
            Si = morris_analyze.analyze(problem, samples, Y)
            indices = self._format_morris(problem, Si)
        else:
            Si = sobol_analyze.analyze(problem, Y, calc_second_order=True)
            indices = self._format_sobol(problem, Si)

        # 5. Display results
        self._print_table(indices, method)

        # 6. Save raw results
        self._save_results(indices, method)

        # 7. LLM interpretation
        interpretation = self._interpret(indices, method)

        try:
            top_params = sorted(
                indices.items(),
                key=lambda kv: kv[1].get("mu_star", kv[1].get("ST", 0)) or 0,
                reverse=True,
            )[:3]
            self.workspace.audit.info(
                phase="Phase 6b",
                text=(
                    f"Sensitivity analysis ({method}) complete; "
                    f"top influential: {', '.join(p for p, _ in top_params)}"
                ),
                actor="SensitivityAnalyzer",
                structured={
                    "method": method,
                    "n_params": len(indices),
                    "top_params": [p for p, _ in top_params],
                },
            )
        except Exception:
            pass

        return {"indices": indices, "interpretation": interpretation, "method": method}

    def _define_problem(self) -> tuple[dict, dict]:
        """
        Read SimulatorScenarios.csv and build SALib problem definition.

        Returns (problem_dict, default_params).
        Heuristic for bounds: ±50% of current value (or [0, 1] for zero values).
        """
        csv_path = self.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"
        if not csv_path.exists():
            return {"num_vars": 0, "names": [], "bounds": []}, {}

        df = pd.read_csv(csv_path)
        if df.empty:
            return {"num_vars": 0, "names": [], "bounds": []}, {}

        row = df.iloc[0].to_dict()

        # Filter out metadata columns
        skip = {"id", "run_num", "scenario_id", "name", "description"}
        params = {k: v for k, v in row.items() if k not in skip and isinstance(v, (int, float, np.integer, np.floating))}

        # Track which params are integers (for type-safe CSV writing)
        for k, v in params.items():
            if isinstance(v, (int, np.integer)):
                self._int_params.add(k)

        names = list(params.keys())
        defaults = {k: float(v) for k, v in params.items()}

        bounds = []
        for name in names:
            val = defaults[name]
            if val == 0:
                bounds.append([0.0, 1.0])
            elif val > 0:
                bounds.append([val * 0.5, val * 1.5])
            else:
                bounds.append([val * 1.5, val * 0.5])  # negative values

        problem = {
            "num_vars": len(names),
            "names": names,
            "bounds": bounds,
        }
        return problem, defaults

    def _run_samples(
        self,
        executor: Executor,
        problem: dict,
        samples: np.ndarray,
        defaults: dict,
        metric_column: str | None,
        metric_file: str | None,
    ) -> np.ndarray | None:
        """Run simulation for each sample, extract scalar metric."""
        n_runs = len(samples)
        Y = np.zeros(n_runs)

        # Determine metric on first successful run
        resolved_metric_col = metric_column
        resolved_metric_file = metric_file

        for i, sample in enumerate(samples):
            console.print(f"  [dim]Sample {i + 1}/{n_runs}...[/dim]", end="\r")

            # Write params to CSV
            param_dict = {name: float(val) for name, val in zip(problem["names"], sample)}
            self._write_params(param_dict, defaults)

            # Run simulation — use negative run numbers to avoid colliding with main pipeline
            run_id = -(i + 1)
            sa_run_id = 9000 + i  # use high run numbers for SA
            success, output = executor.run(sa_run_id)

            if not success:
                console.print(f"  [yellow]Sample {i + 1} failed: {output[:100]}[/yellow]")
                Y[i] = np.nan
                continue

            # Extract metric
            val = self._extract_metric(
                executor, sa_run_id,
                resolved_metric_col, resolved_metric_file,
            )
            if val is None and resolved_metric_col is None:
                # First run: auto-detect metric
                val, resolved_metric_col, resolved_metric_file = self._auto_detect_metric(
                    executor, sa_run_id
                )

            Y[i] = val if val is not None else np.nan

        # Restore defaults
        self._write_params({}, defaults)

        console.print(f"  [green]Completed {n_runs} runs[/green]")

        # Handle NaNs
        valid = ~np.isnan(Y)
        if valid.sum() < len(problem["names"]) + 2:
            console.print("[red]Too many failed runs for reliable analysis[/red]")
            return None

        if np.isnan(Y).any():
            # Replace NaNs with mean for SALib (it needs complete arrays)
            Y[np.isnan(Y)] = np.nanmean(Y)
            console.print(f"  [yellow]Replaced {(~valid).sum()} NaN values with mean[/yellow]")

        return Y

    def _write_params(self, overrides: dict, defaults: dict) -> None:
        """Write parameter values to SimulatorScenarios.csv, preserving int types."""
        csv_path = self.workspace.model_dir / "data" / "input" / "SimulatorScenarios.csv"
        df = pd.read_csv(csv_path)
        merged = {**defaults, **overrides}
        for col, val in merged.items():
            if col in df.columns:
                # Preserve integer types: if original CSV value is int, cast back
                orig = df[col].iloc[0] if len(df) > 0 else val
                if isinstance(orig, (int, np.integer)) or (isinstance(val, float) and val == int(val) and col in self._int_params):
                    df[col] = int(round(val))
                else:
                    df[col] = val
        df.to_csv(csv_path, index=False)

    def _extract_metric(
        self, executor: Executor, run_number: int,
        metric_col: str | None, metric_file: str | None,
    ) -> float | None:
        """Extract a scalar metric from simulation output."""
        if metric_col is None:
            return None

        csvs = self.workspace.list_result_csvs(run_number)
        if not csvs:
            return None

        target = None
        if metric_file:
            target = next((c for c in csvs if c.name == metric_file), None)
        if target is None:
            target = csvs[0]

        try:
            df = pd.read_csv(target)
            if metric_col in df.columns:
                # Use the final-step mean as the scalar
                return float(df[metric_col].iloc[-1]) if len(df) > 0 else None
        except Exception:
            return None
        return None

    def _auto_detect_metric(
        self, executor: Executor, run_number: int,
    ) -> tuple[float | None, str | None, str | None]:
        """Auto-detect a suitable metric column from the first successful run."""
        csvs = self.workspace.list_result_csvs(run_number)
        if not csvs:
            return None, None, None

        # Sort: prefer Environment/aggregate CSVs over Agent CSVs
        csvs = sorted(csvs, key=lambda p: (0 if "environment" in p.name.lower() else 1, p.name))

        for csv_path in csvs:
            try:
                df = pd.read_csv(csv_path)
                # Pick first numeric column that isn't an ID/step/coordinate
                skip = {"id", "step", "period", "run_num", "scenario_id", "agent_id",
                        "id_scenario", "id_run", "id_agent", "x", "y"}
                # Prefer Environment CSV (aggregate) over Agent CSV (per-agent)
                for col in df.columns:
                    if col.lower() in skip:
                        continue
                    if pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique() > 1:
                        val = float(df[col].iloc[-1]) if len(df) > 0 else None
                        console.print(f"  [dim]Auto-detected metric: {csv_path.name}:{col}[/dim]")
                        return val, col, csv_path.name
            except Exception:
                continue

        return None, None, None

    def _format_morris(self, problem: dict, Si: dict) -> list[dict]:
        """Format Morris results into a list of dicts."""
        results = []
        for i, name in enumerate(problem["names"]):
            results.append({
                "parameter": name,
                "mu_star": float(Si["mu_star"][i]),
                "sigma": float(Si["sigma"][i]),
                "mu_star_conf": float(Si["mu_star_conf"][i]),
            })
        # Sort by mu_star descending (most influential first)
        results.sort(key=lambda x: x["mu_star"], reverse=True)
        return results

    def _format_sobol(self, problem: dict, Si: dict) -> list[dict]:
        """Format Sobol results into a list of dicts."""
        results = []
        for i, name in enumerate(problem["names"]):
            results.append({
                "parameter": name,
                "S1": float(Si["S1"][i]),
                "S1_conf": float(Si["S1_conf"][i]),
                "ST": float(Si["ST"][i]),
                "ST_conf": float(Si["ST_conf"][i]),
            })
        results.sort(key=lambda x: x["ST"], reverse=True)
        return results

    def _print_table(self, indices: list[dict], method: str) -> None:
        """Pretty-print sensitivity indices."""
        table = Table(title=f"Sensitivity Analysis ({method.upper()})")
        table.add_column("Parameter", style="cyan")

        if method == "morris":
            table.add_column("μ*", justify="right")
            table.add_column("σ", justify="right")
            table.add_column("μ* conf", justify="right")
            for row in indices:
                table.add_row(
                    row["parameter"],
                    f"{row['mu_star']:.4f}",
                    f"{row['sigma']:.4f}",
                    f"{row['mu_star_conf']:.4f}",
                )
        else:
            table.add_column("S1", justify="right")
            table.add_column("ST", justify="right")
            table.add_column("S1 conf", justify="right")
            table.add_column("ST conf", justify="right")
            for row in indices:
                table.add_row(
                    row["parameter"],
                    f"{row['S1']:.4f}",
                    f"{row['ST']:.4f}",
                    f"{row['S1_conf']:.4f}",
                    f"{row['ST_conf']:.4f}",
                )

        console.print(table)

    def _save_results(self, indices: list[dict], method: str) -> None:
        """Save sensitivity results to workspace."""
        out_path = self.workspace.path / f"sensitivity_{method}.json"
        out_path.write_text(json.dumps(indices, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"  [dim]Saved: {out_path}[/dim]")

    def _interpret(self, indices: list[dict], method: str) -> str:
        """Use LLM to interpret sensitivity analysis results."""
        console.print("[bold cyan]Interpreting sensitivity results...[/bold cyan]")

        story = self.workspace.read_story()
        design = self.workspace.read_design()

        prompt_template = self.load_prompt("sensitivity")
        prompt = (
            prompt_template
            .replace("{{ method }}", method.upper())
            .replace("{{ indices }}", json.dumps(indices, indent=2, ensure_ascii=False))
            .replace("{{ story_summary }}", story[:800])
            .replace("{{ design_summary }}", design[:800])
        )

        system = (
            "You are a computational social scientist specializing in ABM sensitivity analysis. "
            "Write in Chinese. Be rigorous and cite the statistical evidence."
        )
        interpretation = self.call_llm(system, prompt, max_tokens=2048)

        # Save interpretation
        interp_path = self.workspace.path / f"sensitivity_{method}_interpretation.md"
        interp_path.write_text(interpretation, encoding="utf-8")
        console.print(f"  [dim]Saved: {interp_path}[/dim]")

        return interpretation
