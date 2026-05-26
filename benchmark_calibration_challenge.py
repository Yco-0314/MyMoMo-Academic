"""
Benchmark: BEHAVE 2025 Calibration Challenge.

Runs abm-auto end-to-end on the "Virus on a Network" calibration challenge
from BEHAVE 2025 Advanced Week, then compares estimated parameters against the
published ground truth.

Ground truth (from calibration_challenge_results.pdf, page 9):
  virus-spread-chance     = 4.4
  recovery-chance         = 0.3
  gain-resistance-chance  = 25

Empirical data: 250 ticks of (susceptible, infected, resistant) counts,
total population 150.

What this benchmark proves / disproves:
  1. Can abm-auto in originate mode generate runnable SIR-on-network code?
  2. Can BayesianCalibrator (PyMC SMC or ABC fallback) recover the true
     parameters from a 250-tick time series?
  3. How close is the recovered MAP estimate to ground truth?

Outputs:
  workspace/<id>/  — the full pipeline workspace
  benchmark_calibration_summary.md  — human-readable scorecard
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


GROUND_TRUTH = {
    "virus_spread_chance": 4.4,
    "recovery_chance": 0.3,
    "gain_resistance_chance": 25.0,
}

# Acceptable absolute error tier
# (rough categorisation — challenge had no formal "pass" threshold)
TIER_BOUNDS = [
    ("excellent (within 10% relative)", 0.10),
    ("good (within 25% relative)", 0.25),
    ("rough (within 50% relative)", 0.50),
    ("miss (>50% off)", float("inf")),
]


def assess(estimated: dict, truth: dict) -> dict:
    """Compute per-parameter relative error and overall tier."""
    rows = []
    for name, true_val in truth.items():
        est = estimated.get(name)
        if est is None:
            rows.append((name, true_val, None, None, "missing"))
            continue
        rel_err = abs(est - true_val) / true_val if true_val != 0 else abs(est)
        tier = next(label for label, ub in TIER_BOUNDS if rel_err <= ub)
        rows.append((name, true_val, est, rel_err, tier))
    return rows


# Calibration MSE: mean over all (tick, column) of (observed - simulated)^2
# across columns {susceptible, infected, resistant}.
# This is what the original calibration_challenge_results.pdf scored on.
_COLUMN_ALIASES = {
    # observed col → list of acceptable simulator col names (case-insensitive)
    "susceptible": ["susceptible", "count_s", "s", "count_susceptible", "n_susceptible"],
    "infected":    ["infected",    "count_i", "i", "count_infected",    "n_infected"],
    "resistant":   ["resistant",   "count_r", "r", "count_resistant",   "n_resistant", "recovered", "count_recovered"],
}
_TICK_ALIASES = ["tick", "period", "step", "time", "t"]


def score_calibration_mse(observed_path: Path, simulated_path: Path) -> dict:
    """Compute Calibration MSE: mean squared error per column, plus aggregate.

    Returns dict:
      {
        "observed_rows": int,
        "simulated_rows": int,
        "aligned_rows": int,
        "per_column_mse": {"susceptible": float, "infected": float, "resistant": float},
        "mean_mse": float,           # mean across the 3 columns
        "aggregate_mse": float,  # exactly the formula on calibration_challenge_results.pdf p2
        "note": str,
      }
    """
    import pandas as pd
    import numpy as np

    obs = pd.read_csv(observed_path)
    sim = pd.read_csv(simulated_path)

    # Resolve column names case-insensitively
    obs_cols = {c.lower(): c for c in obs.columns}
    sim_cols = {c.lower(): c for c in sim.columns}

    # Tick column
    obs_tick = next((obs_cols[a] for a in _TICK_ALIASES if a in obs_cols), None)
    sim_tick = next((sim_cols[a] for a in _TICK_ALIASES if a in sim_cols), None)

    if obs_tick is None or sim_tick is None:
        return {"error": f"tick column not found (obs={list(obs.columns)}, sim={list(sim.columns)})"}

    # Resolve metric columns
    metric_map = {}  # observed col name → simulator col name
    for obs_name, sim_candidates in _COLUMN_ALIASES.items():
        if obs_name not in obs_cols:
            continue
        for sim_alias in sim_candidates:
            if sim_alias in sim_cols:
                metric_map[obs_cols[obs_name]] = sim_cols[sim_alias]
                break

    if not metric_map:
        return {"error": f"no matching metric columns (obs={list(obs.columns)}, sim={list(sim.columns)})"}

    # Align by tick — inner join on tick value
    merged = pd.merge(
        obs[[obs_tick] + list(metric_map.keys())],
        sim[[sim_tick] + list(metric_map.values())],
        left_on=obs_tick, right_on=sim_tick,
        how="inner", suffixes=("_obs", "_sim"),
    )

    if merged.empty:
        return {
            "error": f"no overlap on tick (obs ticks ∈ [{obs[obs_tick].min()}, {obs[obs_tick].max()}], "
                     f"sim ticks ∈ [{sim[sim_tick].min()}, {sim[sim_tick].max()}])"
        }

    per_column_mse = {}
    total_se = 0.0
    total_n = 0
    for obs_name, sim_name in metric_map.items():
        # Suffix handling: if obs_name == sim_name, pandas added _obs / _sim
        obs_col = f"{obs_name}_obs" if obs_name == sim_name else obs_name
        sim_col = f"{sim_name}_sim" if obs_name == sim_name else sim_name
        diff_sq = (merged[obs_col].astype(float) - merged[sim_col].astype(float)) ** 2
        per_column_mse[obs_name] = float(diff_sq.mean())
        total_se += float(diff_sq.sum())
        total_n += len(diff_sq)

    return {
        "observed_rows": len(obs),
        "simulated_rows": len(sim),
        "aligned_rows": len(merged),
        "per_column_mse": per_column_mse,
        "mean_mse": float(np.mean(list(per_column_mse.values()))),
        "aggregate_mse": total_se / total_n if total_n else float("nan"),
        "column_mapping": {k: v for k, v in metric_map.items()},
    }


def run_benchmark() -> int:
    repo_root = Path(__file__).parent
    story_path = repo_root / "examples" / "calibration_challenge_virus" / "story.md"
    observed_src = repo_root / "examples" / "calibration_challenge_virus" / "observed.csv"

    assert story_path.exists(), f"Story not found: {story_path}"
    assert observed_src.exists(), f"Observed data not found: {observed_src}"

    console.rule("[bold blue]Calibration Challenge Benchmark[/bold blue]")
    console.print(f"Story:    {story_path}")
    console.print(f"Observed: {observed_src} ({observed_src.stat().st_size} bytes)")
    console.print(f"Ground truth: {GROUND_TRUTH}")

    # Import pipeline
    from abm_auto.pipeline import Pipeline

    # Stage 1: build pipeline (creates workspace, copies story)
    console.rule("[cyan]Stage 1: Build pipeline + inject calibration data[/cyan]")
    pipeline = Pipeline(
        story_path=story_path,
        iterations=3,           # ≥3 so calibrate-or-optimize branch fires after iter 1 success
        peer_review=False,
        mode_override="reproduce",  # Milan data is plain SIR (no hypothesis-driven mechanism added); reproduce mode is the fair comparison
        auto_lit_review=False,
        workspace_name=f"benchmark_calibration_{int(time.time())}",
    )

    # Inject observed data into workspace BEFORE pipeline.run()
    data_dir = pipeline.workspace.path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(observed_src, data_dir / "observed.csv")
    console.print(f"  [green]✓ observed.csv injected at {data_dir / 'observed.csv'}[/green]")

    # Stage 2: run pipeline
    console.rule("[cyan]Stage 2: Run pipeline[/cyan]")
    t0 = time.time()
    try:
        workspace_path = pipeline.run()
    except Exception as e:
        console.print(f"[bold red]Pipeline crashed: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return 1
    wall_seconds = time.time() - t0
    console.print(f"\n[dim]Pipeline finished in {wall_seconds:.1f}s[/dim]")

    # Stage 3: collect outputs
    console.rule("[cyan]Stage 3: Inspect outputs[/cyan]")

    # Look for best_params.json (written by BayesianCalibrator on success)
    best_params_path = workspace_path / "best_params.json"
    posterior_summary_path = workspace_path / "posterior_summary.csv"
    calibration_report_path = workspace_path / "calibration_report.md"
    research_spec_path = workspace_path / "research_spec.json"
    audit_path = workspace_path / "audit_ledger.md"

    artifacts = {
        "best_params.json":         best_params_path.exists(),
        "posterior_summary.csv":    posterior_summary_path.exists(),
        "calibration_report.md":    calibration_report_path.exists(),
        "research_spec.json":       research_spec_path.exists(),
        "audit_ledger.md":          audit_path.exists(),
        "DESIGN.md":                (workspace_path / "DESIGN.md").exists(),
        "report.md":                (workspace_path / "report.md").exists(),
    }
    console.print("\nArtifact presence:")
    for name, present in artifacts.items():
        mark = "✓" if present else "✗"
        color = "green" if present else "red"
        console.print(f"  [{color}]{mark}[/{color}] {name}")

    # Check if calibration actually ran
    if research_spec_path.exists():
        spec = json.loads(research_spec_path.read_text())
        console.print(f"\nResearchSpec: mode={spec.get('mode')}, "
                      f"has_calibration_data={spec.get('has_calibration_data')}, "
                      f"calibration_targets={spec.get('calibration_targets')}")

    # Stage 4: score
    console.rule("[cyan]Stage 4: Compare to ground truth[/cyan]")

    if not best_params_path.exists():
        console.print("[bold red]No best_params.json — calibration did not run.[/bold red]")
        console.print("[yellow]Likely cause: pipeline used heuristic OptimizerAgent, "
                      "not BayesianCalibrator. Check audit_ledger.md for diagnosis.[/yellow]")
        write_summary(workspace_path, wall_seconds, [], None, "calibration_not_run")
        return 2

    estimated = json.loads(best_params_path.read_text())
    rows = assess(estimated, GROUND_TRUTH)

    # ── Stage 4b: Calibration MSE on simulated trajectory ──
    mse_result = None
    final_sim_path = workspace_path / "calibration_final_sim.csv"
    if final_sim_path.exists():
        mse_result = score_calibration_mse(observed_src, final_sim_path)
        if "error" in mse_result:
            console.print(f"[yellow]MSE scoring skipped: {mse_result['error']}[/yellow]")
        else:
            mse_table = Table(title="Calibration MSE (observed vs. simulated at best_params)")
            mse_table.add_column("Column")
            mse_table.add_column("MSE", justify="right")
            for col, mse in mse_result["per_column_mse"].items():
                mse_table.add_row(col, f"{mse:.2f}")
            mse_table.add_row("[bold]Aggregate MSE[/bold]",
                              f"[bold]{mse_result['aggregate_mse']:.2f}[/bold]")
            console.print(mse_table)
            console.print(
                f"[dim]Aligned {mse_result['aligned_rows']} ticks "
                f"(observed has {mse_result['observed_rows']}, "
                f"simulated has {mse_result['simulated_rows']})[/dim]"
            )
    else:
        console.print(f"[yellow]No calibration_final_sim.csv — MSE scoring skipped[/yellow]")

    table = Table(title="Parameter recovery vs. ground truth")
    table.add_column("Parameter")
    table.add_column("Truth", justify="right")
    table.add_column("Estimated", justify="right")
    table.add_column("Rel. error", justify="right")
    table.add_column("Tier")
    for name, truth, est, rel_err, tier in rows:
        truth_s = f"{truth:.2f}"
        est_s = f"{est:.2f}" if est is not None else "—"
        rel_s = f"{rel_err:.1%}" if rel_err is not None else "—"
        table.add_row(name, truth_s, est_s, rel_s, tier)
    console.print(table)

    # Aggregate tier
    tiers = [r[4] for r in rows if r[4] != "missing"]
    if not tiers:
        agg_tier = "no_estimates"
    elif all("excellent" in t for t in tiers):
        agg_tier = "excellent"
    elif all("excellent" in t or "good" in t for t in tiers):
        agg_tier = "good"
    elif any("miss" in t for t in tiers):
        agg_tier = "partial"
    else:
        agg_tier = "rough"

    console.print(f"\n[bold]Aggregate tier: {agg_tier.upper()}[/bold]")

    write_summary(workspace_path, wall_seconds, rows, estimated, agg_tier, mse_result)
    return 0


def write_summary(workspace_path: Path, wall_seconds: float, rows, estimated,
                  agg_tier: str, mse_result=None):
    """Write benchmark_calibration_summary.md to repo root."""
    repo_root = Path(__file__).parent
    summary_path = repo_root / "benchmark_calibration_summary.md"

    lines = [
        "# Calibration Challenge Benchmark Result",
        "",
        f"**Workspace**: `{workspace_path}`",
        f"**Wall time**: {wall_seconds:.1f}s",
        f"**Aggregate tier**: **{agg_tier.upper()}**",
        "",
        "## Per-parameter scoring",
        "",
        "| Parameter | Truth | Estimated | Rel. error | Tier |",
        "|---|---|---|---|---|",
    ]
    if rows:
        for name, truth, est, rel_err, tier in rows:
            est_s = f"{est:.3f}" if est is not None else "—"
            rel_s = f"{rel_err:.1%}" if rel_err is not None else "—"
            lines.append(f"| `{name}` | {truth} | {est_s} | {rel_s} | {tier} |")
    else:
        lines.append("| _calibration did not run_ | — | — | — | — |")

    lines += ["", "## Ground truth (from BEHAVE 2025 calibration_challenge_results.pdf)", ""]
    for k, v in GROUND_TRUTH.items():
        lines.append(f"- `{k}` = {v}")

    if mse_result and "error" not in mse_result:
        lines += [
            "",
            "## Calibration MSE (observed vs. simulated at best_params)",
            "",
            "This is the metric the original BEHAVE 2025 calibration challenge used.",
            "It is **decoupled from parameter identifiability** — measures whether the",
            "calibrated model REPRODUCES THE OBSERVED DYNAMICS, regardless of whether",
            "our generated simulator's params map 1:1 to the source NetLogo model.",
            "",
            "| Column | MSE |",
            "|---|---|",
        ]
        for col, mse in mse_result["per_column_mse"].items():
            lines.append(f"| `{col}` | {mse:.2f} |")
        lines += [
            f"| **Aggregate MSE** | **{mse_result['aggregate_mse']:.2f}** |",
            "",
            f"Aligned {mse_result['aligned_rows']} ticks "
            f"(observed: {mse_result['observed_rows']}, "
            f"simulated: {mse_result['simulated_rows']}).",
        ]
    elif mse_result and "error" in mse_result:
        lines += [
            "",
            f"## Calibration MSE: ERROR — {mse_result['error']}",
        ]

    lines += [
        "",
        "## Notes",
        "",
        f"- BayesianCalibrator estimated: `{estimated}`" if estimated else "- BayesianCalibrator did NOT run.",
        "- See workspace's `audit_ledger.md` for full pipeline trace.",
        "- See workspace's `calibration_report.md` (if present) for posterior summary.",
        "- See workspace's `calibration_final_sim.csv` for the trajectory used in MSE.",
    ]

    summary_path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"\n[dim]Summary written to {summary_path}[/dim]")


if __name__ == "__main__":
    sys.exit(run_benchmark())
