"""Lean calibration benchmark — no LLM, no Pipeline phases.

Calls `fit_from_files()` directly. Bypasses:
  - ModeDetector / Hypothesis / Designer / Viability / OddWriter / Reporter
    LLM phases (the bulk of benchmark_external_model.py's wall time)
  - BayesianCalibrator class wrapper + LLM-generated calibration_report.md
  - ResearchSpec parsing (we pass specs inline)

Result: ~100s per calibration vs ~150-200s via BayesianCalibrator,
~300s+ via full Pipeline. ~3× speedup over benchmark_external_model.

Use this as the fast feedback loop when iterating on calibrator code.
benchmark_external_model.py remains valuable as a full-pipeline integration
test; benchmark_calibration_handcrafted.py remains the detailed single-run
diagnostic.

Usage:
    python benchmark_calibration_lean.py [N=3] [max_sims=100]
"""
from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

from abm_auto.calibration.calibrator import fit_from_files
from abm_auto.calibration.posterior import (
    run_final_validation_sim,
    write_best_params,
)
from abm_auto.calibration.simulator import SimulatorWrapper
from abm_auto.runner.executor import Executor
from benchmark_calibration_challenge import GROUND_TRUTH, score_calibration_mse

console = Console()

REPO = Path(__file__).parent
MODEL_DIR = REPO / "examples" / "calibration_challenge_virus" / "handcrafted_model"
OBSERVED = REPO / "examples" / "calibration_challenge_virus" / "observed.csv"

PARAMS_SPECS = [
    {"name": "virus_spread_chance",    "min": 0,  "max": 20,  "unit": "percent"},
    {"name": "recovery_chance",        "min": 0,  "max": 5,   "unit": "percent"},
    {"name": "gain_resistance_chance", "min": 0,  "max": 100, "unit": "percent"},
]
TARGETS = ["susceptible", "infected", "resistant"]


def run_one(max_sims: int, run_idx: int) -> dict | None:
    """Calibrate once, score against ground truth, return summary."""
    name = f"calibration_lean_{int(time.time())}_{run_idx}"
    t0 = time.time()

    result, ws = fit_from_files(
        model_dir=MODEL_DIR,
        observed_csv=OBSERVED,
        params_specs=PARAMS_SPECS,
        targets=TARGETS,
        max_sims=max_sims,
        workspace_name=name,
    )

    if not result.ok:
        console.print(f"  [red]Calibration failed: {result.reason}[/red]")
        return None

    # Persist + run validation sim for MSE scoring
    write_best_params(ws, result)
    executor = Executor(ws, timeout=120)
    simulator = SimulatorWrapper(ws, executor, base_run_id=99000)
    final_csv = run_final_validation_sim(simulator, result.best_params, ws)

    wall = time.time() - t0
    mse_val = None
    if final_csv is not None:
        mse_res = score_calibration_mse(OBSERVED, final_csv)
        mse_val = mse_res.get("aggregate_mse")

    return {
        "wall": wall,
        "best_params": result.best_params,
        "mse": mse_val,
        "workspace": str(ws.path),
    }


def main() -> int:
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    max_sims = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    console.rule(f"[bold blue]Lean calibration benchmark — {n_runs} runs[/bold blue]")
    console.print(f"Model:    {MODEL_DIR.name}")
    console.print(f"Observed: {OBSERVED.name}")
    console.print(f"GT:       {GROUND_TRUTH}")
    console.print(f"Per run ≈ 100s (vs ~300s via full Pipeline)")

    results: list[dict] = []
    for i in range(1, n_runs + 1):
        console.rule(f"[cyan]Run {i}/{n_runs}[/cyan]")
        r = run_one(max_sims, i)
        if r is None:
            continue
        results.append(r)
        bp = r["best_params"]
        mse_s = f"{r['mse']:.1f}" if r["mse"] is not None else "—"
        console.print(
            f"  wall={r['wall']:.0f}s  MSE={mse_s}  "
            f"virus={bp['virus_spread_chance']:.2f}  "
            f"recov={bp['recovery_chance']:.2f}  "
            f"resist={bp['gain_resistance_chance']:.2f}"
        )

    if not results:
        console.print("\n[red]No successful runs.[/red]")
        return 1

    console.rule("[bold green]Aggregate[/bold green]")
    table = Table(title=f"Per-parameter recovery across {len(results)} runs")
    table.add_column("Parameter")
    table.add_column("Truth", justify="right")
    table.add_column("Mean ± SD", justify="right")
    table.add_column("Min / Max", justify="right")
    table.add_column("Rel. err.", justify="right")
    for name, truth in GROUND_TRUTH.items():
        vals = [r["best_params"].get(name) for r in results
                if r["best_params"].get(name) is not None]
        if not vals:
            table.add_row(name, f"{truth:.2f}", "—", "—", "—")
            continue
        m = statistics.mean(vals)
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        rel = abs(m - truth) / truth if truth != 0 else float("nan")
        table.add_row(
            name, f"{truth:.2f}",
            f"{m:.3f} ± {sd:.3f}",
            f"{min(vals):.3f} / {max(vals):.3f}",
            f"{rel:.1%}",
        )
    console.print(table)

    mses = [r["mse"] for r in results if r.get("mse") is not None]
    if mses:
        m_mse = statistics.mean(mses)
        sd_mse = statistics.stdev(mses) if len(mses) > 1 else 0.0
        console.print(
            f"\n[bold]Calibration MSE:[/bold] "
            f"mean={m_mse:.1f} ± {sd_mse:.1f}  "
            f"min={min(mses):.1f}  max={max(mses):.1f}"
        )

    walls = [r["wall"] for r in results]
    console.print(
        f"[dim]Wall time: mean={statistics.mean(walls):.0f}s, "
        f"total={sum(walls):.0f}s[/dim]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
