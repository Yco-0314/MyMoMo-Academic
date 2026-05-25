"""Run handcrafted-sim calibration N times, report variance.

Measures how stable BayesianCalibrator is across independent runs (each gets a
fresh ABC sample, so estimates vary by RNG seed).

Usage:
    python benchmark_calibration_stability.py [N=5] [max_sims=30]
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

REPO = Path(__file__).parent
PYTHON = "/home/user/Documents/Social Simulation /abm-auto/.venv/bin/python"
GROUND_TRUTH = {
    "virus_spread_chance": 4.4,
    "recovery_chance": 0.3,
    "gain_resistance_chance": 25.0,
}

console = Console()


def run_one(max_sims: int) -> dict | None:
    """Run handcrafted benchmark once, return best_params + MSE."""
    t0 = time.time()
    result = subprocess.run(
        [PYTHON, "benchmark_calibration_handcrafted.py", str(max_sims)],
        cwd=REPO, capture_output=True, text=True, timeout=900,
    )
    wall = time.time() - t0

    if result.returncode != 0:
        console.print(f"  [red]Run failed (exit {result.returncode})[/red]")
        return None

    # Find the latest handcrafted workspace
    workspaces = sorted((REPO / "workspace").glob("calibration_handcrafted_*"),
                        key=lambda p: p.stat().st_mtime)
    if not workspaces:
        return None
    ws = workspaces[-1]

    best_path = ws / "best_params.json"
    if not best_path.exists():
        return None

    out = {
        "wall_seconds": wall,
        "best_params": json.loads(best_path.read_text()),
        "workspace": str(ws),
    }

    # MSE from calibration_final_sim
    final_sim = ws / "calibration_final_sim.csv"
    if final_sim.exists():
        # Reuse Milan MSE scorer
        sys.path.insert(0, str(REPO))
        from benchmark_calibration_challenge import score_milan_mse
        observed = REPO / "examples" / "calibration_challenge_virus" / "observed.csv"
        mse_res = score_milan_mse(observed, final_sim)
        if "milan_formula_mse" in mse_res:
            out["mse"] = mse_res["milan_formula_mse"]
            out["mse_per_column"] = mse_res["per_column_mse"]
    return out


def main():
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    max_sims = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    console.rule(f"[bold blue]Stability benchmark: {n_runs} runs × {max_sims} ABC samples[/bold blue]")
    console.print(f"Ground truth: {GROUND_TRUTH}")

    results: list[dict] = []
    for i in range(1, n_runs + 1):
        console.rule(f"[cyan]Run {i}/{n_runs}[/cyan]")
        r = run_one(max_sims)
        if r is None:
            console.print(f"[yellow]Run {i} produced no result; skipping[/yellow]")
            continue
        results.append(r)
        bp = r["best_params"]
        mse = r.get("mse", float("nan"))
        console.print(
            f"  wall={r['wall_seconds']:.0f}s, MSE={mse:.0f}, "
            f"virus={bp.get('virus_spread_chance', '?'):.3f}, "
            f"recov={bp.get('recovery_chance', '?'):.3f}, "
            f"resist={bp.get('gain_resistance_chance', '?'):.3f}"
        )

    if not results:
        console.print("[red]No successful runs.[/red]")
        return 1

    # ── Aggregate ──
    console.rule("[bold green]Aggregate[/bold green]")

    n = len(results)
    table = Table(title=f"Per-parameter recovery across {n} runs")
    table.add_column("Parameter"); table.add_column("Truth", justify="right")
    table.add_column("Mean ± SD", justify="right")
    table.add_column("Min / Max", justify="right")
    table.add_column("Mean rel. err.", justify="right")

    for name, truth in GROUND_TRUTH.items():
        vals = [r["best_params"].get(name) for r in results if r["best_params"].get(name) is not None]
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

    # MSE summary
    mses = [r["mse"] for r in results if "mse" in r]
    if mses:
        m_mse = statistics.mean(mses)
        sd_mse = statistics.stdev(mses) if len(mses) > 1 else 0.0
        console.print(f"\n[bold]Milan MSE across runs:[/bold] "
                      f"mean={m_mse:.1f} ± {sd_mse:.1f}, "
                      f"min={min(mses):.1f}, max={max(mses):.1f}")

    walls = [r["wall_seconds"] for r in results]
    console.print(f"[dim]Wall time: mean={statistics.mean(walls):.0f}s, "
                  f"total={sum(walls):.0f}s[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
