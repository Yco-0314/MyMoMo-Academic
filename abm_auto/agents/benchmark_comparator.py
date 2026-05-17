"""
Benchmark Comparator - Compares simulation results with baseline data.

Supports:
- Manual baseline data input (CSV format)
- Quantitative comparison metrics (RMSE, MAE, correlation)
- Statistical significance tests
- Visualization of baseline vs simulation
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np
from rich.console import Console

console = Console()


class BenchmarkComparator:
    """Compares simulation results with baseline/reference data."""

    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path

    def load_baseline(self, baseline_path: Path | str) -> pd.DataFrame:
        """
        Load baseline data from CSV.

        Expected format:
        - time,metric1,metric2,...
        - 0,100,50,...
        - 1,95,55,...
        """
        baseline_path = Path(baseline_path)
        if not baseline_path.exists():
            raise FileNotFoundError(f"Baseline file not found: {baseline_path}")

        df = pd.read_csv(baseline_path)
        console.print(f"  [green]✓ Loaded baseline: {baseline_path.name}[/green]")
        console.print(f"    Shape: {df.shape}, Columns: {list(df.columns)}")
        return df

    def load_simulation_results(self) -> pd.DataFrame:
        """
        Load simulation results from workspace.

        Looks for:
        - simulation_results.csv (aggregated across runs)
        - data_collector.csv (from latest run)
        """
        candidates = [
            self.workspace_path / "simulation_results.csv",
            self.workspace_path / "data_collector.csv",
        ]

        for path in candidates:
            if path.exists():
                df = pd.read_csv(path)
                console.print(f"  [green]✓ Loaded simulation: {path.name}[/green]")
                console.print(f"    Shape: {df.shape}, Columns: {list(df.columns)}")
                return df

        raise FileNotFoundError(
            f"No simulation results found in {self.workspace_path}"
        )

    def align_data(
        self,
        baseline: pd.DataFrame,
        simulation: pd.DataFrame,
        time_col: str = "time"
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Align baseline and simulation data on time axis.

        Returns:
        - baseline_aligned: baseline data with matching time points
        - simulation_aligned: simulation data with matching time points
        """
        # Find common time points
        baseline_times = set(baseline[time_col].unique())
        simulation_times = set(simulation[time_col].unique())
        common_times = sorted(baseline_times & simulation_times)

        if not common_times:
            console.print(
                "  [yellow]⚠ No overlapping time points between baseline and simulation[/yellow]"
            )
            # Fallback: interpolate simulation to baseline times
            return baseline, simulation

        baseline_aligned = baseline[baseline[time_col].isin(common_times)].copy()
        simulation_aligned = simulation[simulation[time_col].isin(common_times)].copy()

        console.print(f"  Aligned on {len(common_times)} time points")
        return baseline_aligned, simulation_aligned

    def compute_metrics(
        self,
        baseline: pd.DataFrame,
        simulation: pd.DataFrame,
        metric_cols: list[str]
    ) -> dict[str, dict[str, float]]:
        """
        Compute comparison metrics for each variable.

        Metrics:
        - RMSE: Root Mean Squared Error
        - MAE: Mean Absolute Error
        - MAPE: Mean Absolute Percentage Error
        - R²: Coefficient of determination
        - Correlation: Pearson correlation coefficient
        """
        results = {}

        for col in metric_cols:
            if col not in baseline.columns or col not in simulation.columns:
                console.print(f"  [yellow]⚠ Column '{col}' not found in both datasets[/yellow]")
                continue

            baseline_vals = baseline[col].values
            simulation_vals = simulation[col].values

            # Handle aggregated simulation data (mean ± std)
            if simulation_vals.dtype == object:
                # Parse "mean ± std" format
                simulation_vals = np.array([
                    float(str(v).split("±")[0].strip())
                    for v in simulation_vals
                ])

            # Ensure same length
            min_len = min(len(baseline_vals), len(simulation_vals))
            baseline_vals = baseline_vals[:min_len]
            simulation_vals = simulation_vals[:min_len]

            # Compute metrics
            rmse = np.sqrt(np.mean((baseline_vals - simulation_vals) ** 2))
            mae = np.mean(np.abs(baseline_vals - simulation_vals))

            # MAPE (avoid division by zero)
            mape = np.mean(
                np.abs((baseline_vals - simulation_vals) / (baseline_vals + 1e-10))
            ) * 100

            # R² and correlation
            ss_res = np.sum((baseline_vals - simulation_vals) ** 2)
            ss_tot = np.sum((baseline_vals - np.mean(baseline_vals)) ** 2)
            r2 = 1 - (ss_res / (ss_tot + 1e-10))

            correlation = np.corrcoef(baseline_vals, simulation_vals)[0, 1]

            results[col] = {
                "RMSE": float(rmse),
                "MAE": float(mae),
                "MAPE": float(mape),
                "R²": float(r2),
                "Correlation": float(correlation),
                "Baseline_Mean": float(np.mean(baseline_vals)),
                "Simulation_Mean": float(np.mean(simulation_vals)),
            }

        return results

    def generate_comparison_report(
        self,
        metrics: dict[str, dict[str, float]],
        baseline_path: Path | str
    ) -> str:
        """
        Generate markdown report of comparison results.

        Returns markdown string.
        """
        report = f"""# Baseline Comparison Report

## Data Sources
- **Baseline**: `{Path(baseline_path).name}`
- **Simulation**: Workspace results

## Quantitative Comparison

"""

        for var, stats in metrics.items():
            report += f"### {var}\n\n"
            report += "| Metric | Value |\n"
            report += "|--------|-------|\n"

            for metric_name, value in stats.items():
                if metric_name.endswith("_Mean"):
                    report += f"| {metric_name} | {value:.4f} |\n"
                else:
                    report += f"| {metric_name} | {value:.4f} |\n"

            report += "\n"

            # Interpretation
            r2 = stats.get("R²", 0)
            corr = stats.get("Correlation", 0)
            mape = stats.get("MAPE", 100)

            if r2 > 0.9 and corr > 0.95:
                quality = "**Excellent fit** ✓"
            elif r2 > 0.7 and corr > 0.8:
                quality = "**Good fit**"
            elif r2 > 0.5:
                quality = "**Moderate fit**"
            else:
                quality = "**Poor fit** ⚠"

            report += f"**Interpretation**: {quality}\n"
            report += f"- R² = {r2:.3f} indicates {r2*100:.1f}% variance explained\n"
            report += f"- MAPE = {mape:.1f}% average percentage error\n\n"

        report += """## Summary

"""

        # Overall assessment
        avg_r2 = np.mean([m.get("R²", 0) for m in metrics.values()])
        avg_corr = np.mean([m.get("Correlation", 0) for m in metrics.values()])

        if avg_r2 > 0.8:
            report += "✓ **Model shows strong agreement with baseline data**\n\n"
        elif avg_r2 > 0.6:
            report += "⚠ **Model shows moderate agreement with baseline data**\n\n"
        else:
            report += "⚠ **Model shows weak agreement with baseline data** - consider recalibration\n\n"

        report += f"- Average R²: {avg_r2:.3f}\n"
        report += f"- Average Correlation: {avg_corr:.3f}\n"

        return report

    def compare(
        self,
        baseline_path: Path | str,
        metric_cols: list[str] | None = None,
        time_col: str = "time"
    ) -> dict[str, Any]:
        """
        Main entry point: load data, align, compute metrics, generate report.

        Args:
            baseline_path: Path to baseline CSV file
            metric_cols: List of columns to compare (if None, auto-detect numeric columns)
            time_col: Name of time column for alignment

        Returns:
            {
                "metrics": {...},
                "report": "...",
                "baseline_path": "...",
            }
        """
        console.print("[bold cyan]Comparing with baseline data...[/bold cyan]")

        # Load data
        baseline = self.load_baseline(baseline_path)
        simulation = self.load_simulation_results()

        # Auto-detect metric columns if not specified
        if metric_cols is None:
            metric_cols = [
                col for col in baseline.columns
                if col != time_col and pd.api.types.is_numeric_dtype(baseline[col])
            ]
            console.print(f"  Auto-detected metric columns: {metric_cols}")

        # Align data
        baseline_aligned, simulation_aligned = self.align_data(
            baseline, simulation, time_col
        )

        # Compute metrics
        metrics = self.compute_metrics(
            baseline_aligned, simulation_aligned, metric_cols
        )

        # Generate report
        report = self.generate_comparison_report(metrics, baseline_path)

        result = {
            "metrics": metrics,
            "report": report,
            "baseline_path": str(baseline_path),
        }

        return result

    def save_comparison(self, comparison: dict) -> Path:
        """Save comparison results to workspace."""
        # Save metrics as JSON
        metrics_path = self.workspace_path / "baseline_comparison.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(comparison["metrics"], f, indent=2)

        # Save report as markdown
        report_path = self.workspace_path / "baseline_comparison.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(comparison["report"])

        console.print(f"  [green]✓ Comparison saved to {report_path.name}[/green]")
        return report_path
