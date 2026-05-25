"""Posterior output utilities.

After a backend produces a CalibrationResult, these helpers persist it:
  - write_posterior_summary  →  posterior_summary.csv
  - write_best_params        →  best_params.json
  - write_calibration_report →  calibration_report.md  (LLM-written, optional)
  - apply_best_params        →  mutates SimulatorScenarios.csv + params_history
  - run_final_validation_sim →  one sim at best_params → calibration_final_sim.csv

All free functions. They take exactly the inputs they need (workspace,
result, simulator) and have no class state.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from abm_auto.calibration.simulator import SimulatorWrapper
from abm_auto.calibration.types import CalibrationResult


def write_posterior_summary(workspace, result: CalibrationResult) -> Path:
    """posterior_summary.csv with per-param mean/std/CIs."""
    path = workspace.path / "posterior_summary.csv"
    result.posterior_summary.to_csv(path)
    return path


def write_best_params(workspace, result: CalibrationResult) -> Path:
    """best_params.json — what downstream MSE scorers consume."""
    path = workspace.path / "best_params.json"
    path.write_text(json.dumps(result.best_params, indent=2), encoding="utf-8")
    return path


def write_calibration_report(
    workspace,
    result: CalibrationResult,
    call_llm: Optional[Callable[[str, str, int], str]] = None,
) -> Optional[Path]:
    """LLM-generated human summary of the posterior.

    Args:
        call_llm: callable matching BaseAgent.call_llm(system, user, max_tokens).
                  When None, no report is written (graceful skip).

    Returns the path written, or None if skipped/failed.
    """
    if call_llm is None:
        return None
    try:
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
        md = call_llm(system, prompt, 800)
        path = workspace.path / "calibration_report.md"
        path.write_text(md, encoding="utf-8")
        return path
    except Exception:
        return None


def apply_best_params(workspace, simulator: SimulatorWrapper, best_params: dict) -> None:
    """Write best_params to SimulatorScenarios.csv (so downstream phases see
    the calibrated values) and append a row to params_history.json so
    reviewers can see calibration happened.
    """
    simulator.write_scenario_params(best_params)
    try:
        workspace.append_params_history(
            run=99999,
            params=best_params,
            hypothesis="Bayesian calibration posterior mean",
        )
    except Exception:
        pass


def run_final_validation_sim(
    simulator: SimulatorWrapper, best_params: dict, workspace,
) -> Optional[Path]:
    """One sim at best_params, saved at calibration_final_sim.csv.

    Lets downstream scorers (Milan-style MSE benchmark, reviewers) read a
    deterministic "this is what the calibrated model produces" CSV without
    guessing which iter ran with which params.
    """
    try:
        simulator.write_scenario_params(best_params)
        run_id = 30000  # sentinel ID, well outside ABC's run_id range
        success, _ = simulator.executor.run(run_id)
        if not success:
            return None
        csvs = workspace.list_result_csvs(run_id)
        if not csvs:
            return None
        # Pick the environment-level CSV (S/I/R counts), fall back to first.
        source = next(
            (c for c in csvs if "environment" in c.name.lower()),
            csvs[0],
        )
        target = workspace.path / "calibration_final_sim.csv"
        target.write_bytes(source.read_bytes())
        return target
    except Exception:
        return None
