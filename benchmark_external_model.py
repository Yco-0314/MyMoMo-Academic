"""
Benchmark: full pipeline with --external-model (bypassing codegen).

Validates the new external-model branch added in commit af72ab6: when a
prebuilt Python model is supplied, Phase 1d / 2 / 3 are skipped and the
model directory is copied into workspace/model/. Phase 4+ runs against
the supplied model with ZERO LLM-mediated codegen randomness.

Why this benchmark exists (vs. the two existing ones):

  benchmark_calibration_handcrafted.py:
    - Skips ALL pipeline phases, calls BayesianCalibrator directly.
    - Tests calibration algorithms in isolation.
    - Fastest (~30s per run).

  benchmark_calibration_challenge.py:
    - Runs the FULL pipeline with LLM-generated code.
    - Tests the whole stack including codegen.
    - Slowest (~5-7 min per run, codegen-failure-prone).

  benchmark_external_model.py (THIS file):
    - Runs the full pipeline with prebuilt model (no codegen).
    - Tests: does Phase -1 / 0.5 / 1 / 1c / 1b still work? Does the
      external-model branch correctly skip 1d/2/3? Does Phase 4+ run
      the supplied model unchanged? Does calibration succeed?
    - Medium speed (~3-4 min per run, no codegen-retry randomness).
    - Variance in MSE across runs should be from ABC sampling ONLY,
      not from LLM codegen — so this benchmark is a cleaner test of
      calibration stability under realistic pipeline conditions.

Ground truth (inferred from observed.csv; see benchmark_calibration_challenge
docstring for the typo finding — paper printed recovery_chance=0.3 but data
requires ~2.5):
  virus_spread_chance    = 4.4    (% per neighbour per tick)
  recovery_chance        = 2.5    (% per infected per check)
  gain_resistance_chance = 25.0   (% at recovery)

Usage:
    python benchmark_external_model.py [N=3] [max_sims=30]
"""
from __future__ import annotations

import json
import shutil
import statistics
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Reuse scoring helpers
from benchmark_calibration_challenge import GROUND_TRUTH, assess, score_calibration_mse

console = Console()

REPO = Path(__file__).parent
EXAMPLE_DIR = REPO / "examples" / "calibration_challenge_virus"
STORY_PATH = EXAMPLE_DIR / "story.md"
MODEL_PATH = EXAMPLE_DIR / "handcrafted_model"
OBSERVED_PATH = EXAMPLE_DIR / "observed.csv"


def run_one(max_sims: int, run_idx: int) -> dict | None:
    """Run the full pipeline once with --external-model, return harvested results."""
    from abm_auto.pipeline import Pipeline

    t0 = time.time()

    pipeline = Pipeline(
        story_path=STORY_PATH,
        iterations=2,                  # ≥2 so the calibrate-or-optimize branch fires
                                       # (Pipeline guards Phase 6 with `i < iterations`)
        peer_review=False,
        mode_override="reproduce",     # not generating a new story; reproducing a published challenge
        auto_lit_review=False,         # skip Phase 0 net call
        external_model_path=str(MODEL_PATH),
        workspace_name=f"external_model_bench_{int(time.time())}_{run_idx}",
    )

    # Inject observed data into the workspace data/ (no CLI flag for this yet —
    # done inline because the formal contract is "observed.csv lives at
    # workspace/data/observed.csv"; we just satisfy it ourselves).
    data_dir = pipeline.workspace.path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(OBSERVED_PATH, data_dir / "observed.csv")

    try:
        workspace_path = pipeline.run()
    except Exception as e:
        console.print(f"  [bold red]Pipeline crashed: {e}[/bold red]")
        return None
    wall = time.time() - t0

    bp_path = workspace_path / "best_params.json"
    if not bp_path.exists():
        return {
            "workspace": str(workspace_path),
            "wall_seconds": wall,
            "best_params": None,
            "mse": None,
            "reason": "no best_params.json",
        }

    best_params = json.loads(bp_path.read_text())

    final_sim = workspace_path / "calibration_final_sim.csv"
    mse_val = None
    if final_sim.exists():
        mse_res = score_calibration_mse(OBSERVED_PATH, final_sim)
        if "aggregate_mse" in mse_res:
            mse_val = mse_res["aggregate_mse"]

    return {
        "workspace": str(workspace_path),
        "wall_seconds": wall,
        "best_params": best_params,
        "mse": mse_val,
    }


def main():
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    max_sims = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    console.rule(f"[bold blue]External-model pipeline benchmark: {n_runs} runs[/bold blue]")
    console.print(f"Story:      {STORY_PATH}")
    console.print(f"Model:      {MODEL_PATH}")
    console.print(f"Observed:   {OBSERVED_PATH}")
    console.print(f"Ground truth: {GROUND_TRUTH}")
    console.print(f"Each run ≈ 3-4 min; total ≈ {n_runs * 3.5:.0f} min")

    results: list[dict] = []
    for i in range(1, n_runs + 1):
        console.rule(f"[cyan]Run {i}/{n_runs}[/cyan]")
        r = run_one(max_sims, i)
        if r is None:
            console.print("  [red]Run crashed; skipping[/red]")
            continue
        results.append(r)
        bp = r.get("best_params") or {}
        mse = r.get("mse")
        mse_s = f"{mse:.0f}" if mse is not None else "—"
        console.print(
            f"  wall={r['wall_seconds']:.0f}s  MSE={mse_s}  "
            f"virus={bp.get('virus_spread_chance', '?')}  "
            f"recov={bp.get('recovery_chance', '?')}  "
            f"resist={bp.get('gain_resistance_chance', '?')}"
        )

    if not results:
        console.print("\n[red]No successful runs.[/red]")
        return 1

    # ── Aggregate ──
    console.rule("[bold green]Aggregate[/bold green]")
    successful = [r for r in results if r.get("best_params")]

    if successful:
        table = Table(title=f"Per-parameter recovery across {len(successful)} runs")
        table.add_column("Parameter")
        table.add_column("Truth", justify="right")
        table.add_column("Mean ± SD", justify="right")
        table.add_column("Min / Max", justify="right")
        table.add_column("Rel. err.", justify="right")
        for name, truth in GROUND_TRUTH.items():
            vals = [r["best_params"].get(name) for r in successful
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

    mses = [r["mse"] for r in successful if r.get("mse") is not None]
    if mses:
        m_mse = statistics.mean(mses)
        sd_mse = statistics.stdev(mses) if len(mses) > 1 else 0.0
        console.print(f"\n[bold]Calibration MSE:[/bold] "
                      f"mean={m_mse:.1f} ± {sd_mse:.1f}  "
                      f"min={min(mses):.1f}  max={max(mses):.1f}")

    walls = [r["wall_seconds"] for r in results]
    console.print(f"[dim]Wall time: mean={statistics.mean(walls):.0f}s, "
                  f"total={sum(walls):.0f}s[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
