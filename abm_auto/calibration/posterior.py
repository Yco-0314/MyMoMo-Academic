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
    diagnostics_md: str = "",
) -> Optional[Path]:
    """LLM-generated human summary of the posterior + optional diagnostics.

    Args:
        call_llm: callable matching BaseAgent.call_llm(system, user, max_tokens).
                  When None, no LLM section is added but the diagnostics
                  section (β + ε) still writes if provided.
        diagnostics_md: pre-rendered markdown from β (profile_likelihood,
                  fisher_info_eigen) and ε (verify_execution). Appended to
                  the calibration report under a "## Diagnostics" header.
                  When empty, no diagnostics section is written.

    Returns the path written, or None if skipped/failed.
    """
    body_parts: list[str] = []

    if call_llm is not None:
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
            llm_md = call_llm(system, prompt, 800)
            if llm_md and llm_md.strip():
                body_parts.append(llm_md)
        except Exception:
            pass

    if diagnostics_md and diagnostics_md.strip():
        body_parts.append("\n\n---\n\n## Diagnostics\n\n" + diagnostics_md)

    if not body_parts:
        return None

    path = workspace.path / "calibration_report.md"
    path.write_text("\n".join(body_parts), encoding="utf-8")
    return path


def run_diagnostics(
    workspace,
    simulator: SimulatorWrapper,
    priors: dict,
    map_params: dict,
    targets: list,
    obs_stats,
    *,
    summary_fn=None,
    story_text: str = "",
    final_sim_csv: Optional[Path] = None,
    call_llm: Optional[Callable[[str, str, int], str]] = None,
    profile_grid: int = 10,
    enable_profile: bool = True,
    enable_fisher: bool = True,
    enable_execution: bool = True,
) -> str:
    """Run the α + β + ε diagnostics suite, return concatenated markdown.

    Each block is best-effort: errors are caught and replaced with a
    short failure note so partial diagnostics still ship. Total cost
    at default settings on a 3-param problem:
      - profile_likelihood: 3 × 10 = 30 sims (~7s at 250ms/sim)
      - fisher_info_eigen: 1 + 2×3² = 19 sims (~5s)
      - verify_execution: 1 LLM call (~3s)

    ~15s total overhead at end of calibration.

    `summary_fn` is optional. When provided, it overrides the simulator's
    default summary_fn for the duration of the diagnostics — usually
    full_trajectory for maximum signal during identifiability analysis.
    """
    blocks: list[str] = []

    if enable_profile or enable_fisher:
        from abm_auto.calibration.identifiability_profile import (
            fisher_info_eigen,
            profile_likelihood,
        )
        original_summary = simulator.summary_fn if hasattr(simulator, "summary_fn") else None
        if summary_fn is not None and hasattr(simulator, "summary_fn"):
            simulator.summary_fn = summary_fn

        if enable_profile:
            try:
                profile = profile_likelihood(
                    simulator, priors, map_params, targets, obs_stats,
                    n_grid=profile_grid,
                    summary_fn=summary_fn or original_summary,
                )
                blocks.append(profile.to_markdown())
            except Exception as e:
                blocks.append(f"## Profile likelihood\n\n_(failed: {e})_\n")

        if enable_fisher:
            try:
                fisher = fisher_info_eigen(
                    simulator, priors, map_params, targets, obs_stats,
                    summary_fn=summary_fn or original_summary,
                )
                if fisher is not None:
                    blocks.append(fisher.to_markdown())
                else:
                    blocks.append("## Fisher information eigendecomposition\n\n"
                                  "_(failed: simulator returned None at one of "
                                  "the finite-difference points)_\n")
            except Exception as e:
                blocks.append(f"## Fisher information eigendecomposition\n\n_(failed: {e})_\n")

        if original_summary is not None and hasattr(simulator, "summary_fn"):
            simulator.summary_fn = original_summary

    if enable_execution and call_llm is not None and final_sim_csv is not None and story_text:
        try:
            from abm_auto.verification.execution_verifier import verify_execution
            verify_result = verify_execution(story_text, final_sim_csv, targets, call_llm)
            blocks.append(_render_execution_verification(verify_result))
        except Exception as e:
            blocks.append(f"## Execution fidelity\n\n_(failed: {e})_\n")

    return "\n\n".join(blocks)


def _render_execution_verification(result) -> str:
    lines = ["## Execution fidelity (LLM-claim vs sim-trajectory direction)", ""]
    if not result.claims:
        lines.append("_(LLM emitted no claims for any target — skipped.)_")
        return "\n".join(lines) + "\n"
    lines.append(f"- Claims extracted: **{len(result.claims)}**")
    lines.append(f"- Mismatches: **{len(result.mismatches)}**")
    if result.is_valid:
        lines.append("- Verdict: **PASS** (no contradiction between story and sim trajectory)")
    else:
        lines.append("- Verdict: **MISMATCH DETECTED** — see below")
    lines += ["", "### Per-target", "",
              "| Target | LLM claim | Sim actual | Status |",
              "|---|---|---|---|"]
    actual_by_target = {a.target: a for a in result.actuals}
    mismatch_targets = {t for t, _e, _a in result.mismatches}
    for claim in result.claims:
        actual = actual_by_target.get(claim.target)
        actual_dir = actual.direction if actual else "—"
        if claim.target in mismatch_targets:
            status = "✗ mismatch"
        elif claim.direction == "unclear" or (actual and actual.direction == "unclear"):
            status = "~ skipped (unclear)"
        else:
            status = "✓ match"
        lines.append(f"| `{claim.target}` | `{claim.direction}` | `{actual_dir}` | {status} |")
    return "\n".join(lines) + "\n"


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

    Lets downstream scorers (Calibration MSE benchmark, reviewers) read a
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
