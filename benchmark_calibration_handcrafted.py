"""
Calibration-only benchmark: BayesianCalibrator + MSE on a hand-crafted simulator.

Why this exists (vs. benchmark_calibration_challenge.py):
  The full-pipeline benchmark exercises ModeDetect → Hypothesis → Design → Codegen
  → Verify → Sim → Calibrate. The codegen step is brittle (DeepSeek hallucinates
  Melodie API), causing 50%+ pipeline failures BEFORE calibration even runs.

  This script bypasses codegen entirely:
    1. Pre-built workspace = examples/calibration_challenge_virus/handcrafted_model
    2. Pre-built observed data = examples/calibration_challenge_virus/observed.csv
    3. Pre-built ResearchSpec (originate + has_calibration_data=True + 3 params)
    4. Run BayesianCalibrator directly via Executor
    5. Score MSE on the calibrated trajectory

  Cleanly separates "is calibration broken?" from "is codegen broken?".

Ground truth (Milan calibration_challenge_results.pdf p9):
  virus_spread_chance    = 4.4    (% per neighbour per tick)
  recovery_chance        = 0.3    (% per infected per check)
  gain_resistance_chance = 25.0   (% at recovery)
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Reuse scoring helpers from the other benchmark
from benchmark_calibration_challenge import GROUND_TRUTH, assess, score_milan_mse

console = Console()


def setup_workspace(name: str) -> Path:
    """Create a workspace with the hand-crafted model + observed data pre-installed."""
    from abm_auto.runner.workspace import Workspace

    repo = Path(__file__).parent
    src_model = repo / "examples" / "calibration_challenge_virus" / "handcrafted_model"
    src_observed = repo / "examples" / "calibration_challenge_virus" / "observed.csv"

    ws = Workspace.create(name=name)

    # 1. Copy hand-crafted model
    shutil.copytree(src_model, ws.path / "model", dirs_exist_ok=True)

    # 2. Wipe any stale output from previous standalone runs of the example
    output_dir = ws.path / "model" / "data" / "output"
    if output_dir.exists():
        shutil.rmtree(output_dir)

    # 3. Inject observed data
    data_dir = ws.path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(src_observed, data_dir / "observed.csv")

    # 4. Pre-populate research_spec.json so BayesianCalibrator activates with
    #    the right allowlist. ModeDetector is skipped — we already know.
    spec = {
        "mode": "originate",
        "paper_ref": "",
        "phenomenon": "Virus on a network (Milan calibration challenge)",
        "has_calibration_data": True,
        "calibration_data_path": "data/observed.csv",
        "calibration_targets": ["susceptible", "infected", "resistant"],
        "calibration_params": [
            "virus_spread_chance", "recovery_chance", "gain_resistance_chance",
        ],
        # Story-declared ranges + units. Calibrator uses these to build priors
        # instead of inferring ±50% from the CSV default — fixes unit drift.
        "calibration_param_specs": [
            {"name": "virus_spread_chance",    "min": 0,  "max": 20,  "unit": "percent"},
            {"name": "recovery_chance",        "min": 0,  "max": 5,   "unit": "percent"},
            {"name": "gain_resistance_chance", "min": 0,  "max": 100, "unit": "percent"},
        ],
        "confidence": 1.0,
        "viability_max_assumptions": 15,
        "viability_max_missing_elements": 6,
        "viability_llm_question": "",
    }
    (ws.path / "research_spec.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 5. Story + minimal design (so audit ledger has context, not required)
    ws.write_story(
        (repo / "examples" / "calibration_challenge_virus" / "story.md")
        .read_text(encoding="utf-8")
    )

    return ws.path


def run_benchmark(max_sims: int = 50) -> int:
    console.rule("[bold blue]Calibration-only Benchmark (handcrafted sim)[/bold blue]")

    workspace_path = setup_workspace(f"calibration_handcrafted_{int(time.time())}")
    console.print(f"Workspace: {workspace_path}")
    console.print(f"Ground truth: {GROUND_TRUTH}")
    console.print(f"Max ABC samples: {max_sims}")

    # Build minimal dependencies for BayesianCalibrator
    from abm_auto.runner.workspace import Workspace
    from abm_auto.runner.executor import Executor
    from abm_auto.agents.bayesian_calibrator import BayesianCalibrator
    from abm_auto.agents.mode_detector import ResearchSpec
    from abm_auto import config as cfg
    from abm_auto.llm import make_client

    ws = Workspace.load(workspace_path)
    spec = ResearchSpec.from_dict(json.loads((ws.path / "research_spec.json").read_text()))
    executor = Executor(ws, timeout=120)
    client = make_client(
        provider=cfg.LLM_PROVIDER, api_key=cfg.get_api_key(),
        base_url=cfg.get_base_url(), timeout=300,
    )

    # ── Sanity sim at ground truth (proves the handcrafted simulator works) ──
    console.rule("[cyan]Sanity check: simulate at ground-truth params[/cyan]")
    from abm_auto.calibration.simulator import SimulatorWrapper
    sim_wrap = SimulatorWrapper(ws, executor, base_run_id=99000)
    sim_wrap.write_scenario_params({
        "virus_spread_chance": 4.4,
        "recovery_chance": 0.3,
        "gain_resistance_chance": 25.0,
    })
    success, _ = executor.run(99000)  # sentinel run id
    if not success:
        console.print("[bold red]Sanity sim failed — handcrafted simulator is broken.[/bold red]")
        return 1

    sanity_csvs = ws.list_result_csvs(99000)
    env_csv = next((c for c in sanity_csvs if "environment" in c.name.lower()), sanity_csvs[0] if sanity_csvs else None)
    if env_csv is None:
        console.print("[bold red]No output from sanity sim.[/bold red]")
        return 1
    shutil.copy(env_csv, ws.path / "sanity_groundtruth_sim.csv")
    sanity_mse = score_milan_mse(ws.path / "data" / "observed.csv", env_csv)
    console.print(f"[dim]Sanity MSE (ground-truth params): "
                  f"{sanity_mse.get('milan_formula_mse', 'N/A'):.2f}[/dim]")

    # ── Real calibration ──
    console.rule("[cyan]Calibration[/cyan]")
    t0 = time.time()
    bc = BayesianCalibrator(client, ws, model=cfg.DEFAULT_MODEL, lang="en")
    result = bc.run(executor, spec=spec, max_sims=max_sims)
    wall = time.time() - t0
    console.print(f"\n[dim]Calibration finished in {wall:.1f}s[/dim]")

    if not result.ok:
        console.print(f"[bold red]Calibration failed: {result.reason}[/bold red]")
        return 2

    # ── Score against ground truth ──
    console.rule("[cyan]Scoring[/cyan]")
    rows = assess(result.best_params, GROUND_TRUTH)
    table = Table(title="Parameter recovery vs. ground truth")
    table.add_column("Parameter"); table.add_column("Truth", justify="right")
    table.add_column("Estimated", justify="right"); table.add_column("Rel. error", justify="right")
    table.add_column("Tier")
    for name, truth, est, rel_err, tier in rows:
        truth_s = f"{truth:.2f}"
        est_s = f"{est:.3f}" if est is not None else "—"
        rel_s = f"{rel_err:.1%}" if rel_err is not None else "—"
        table.add_row(name, truth_s, est_s, rel_s, tier)
    console.print(table)

    # ── MSE on calibrated trajectory ──
    final_sim = ws.path / "calibration_final_sim.csv"
    if not final_sim.exists():
        console.print("[yellow]No calibration_final_sim.csv — MSE skipped.[/yellow]")
        return 0
    mse = score_milan_mse(ws.path / "data" / "observed.csv", final_sim)
    if "error" in mse:
        console.print(f"[yellow]MSE error: {mse['error']}[/yellow]")
        return 0

    mse_table = Table(title="Milan MSE (calibrated trajectory vs observed)")
    mse_table.add_column("Column"); mse_table.add_column("MSE", justify="right")
    for col, m in mse["per_column_mse"].items():
        mse_table.add_row(col, f"{m:.2f}")
    mse_table.add_row("[bold]Milan formula MSE[/bold]",
                      f"[bold]{mse['milan_formula_mse']:.2f}[/bold]")
    mse_table.add_row("[dim]Sanity MSE (ground-truth)[/dim]",
                      f"[dim]{sanity_mse.get('milan_formula_mse', float('nan')):.2f}[/dim]")
    console.print(mse_table)

    # Compare: calibrated should be ≤ sanity (otherwise calibration found a worse-than-truth fit)
    cal_mse = mse["milan_formula_mse"]
    truth_mse = sanity_mse.get("milan_formula_mse", float("inf"))
    if cal_mse <= truth_mse:
        console.print(f"\n[bold green]✓ Calibration found fit AT LEAST as good as ground truth "
                      f"({cal_mse:.2f} ≤ {truth_mse:.2f})[/bold green]")
    else:
        ratio = cal_mse / truth_mse if truth_mse > 0 else float("inf")
        console.print(f"\n[bold yellow]⚠ Calibration MSE = {cal_mse:.2f}, "
                      f"ground-truth MSE = {truth_mse:.2f} ({ratio:.1f}x worse)[/bold yellow]")
        console.print("[dim]   This is the identifiability ceiling — algorithm couldn't beat truth.[/dim]")

    return 0


if __name__ == "__main__":
    sys.exit(run_benchmark(max_sims=int(sys.argv[1]) if len(sys.argv) > 1 else 50))
