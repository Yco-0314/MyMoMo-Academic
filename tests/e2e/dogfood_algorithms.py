"""Dogfood α + β + ε on the virus-on-a-network calibration problem.

Three independent experiments validating today's algorithm work
against a real handcrafted simulator + multi-seed observed.csv.
None of them mutate the production calibrator yet (that's the wire-up
task #59); this script runs each algorithm standalone against the
same workspace and reports findings to docs/dogfood/.

Pass criteria
-------------

α — trajectory_features:
    Calibration with the new 12-D summary statistic produces MSE
    within 2× of the full_trajectory baseline (44.5 ± 19.8). If much
    worse, the summary throws away too much signal. If much better,
    we have a free win.

β — profile_likelihood + fisher_info_eigen:
    At the MAP from α, the profile for recovery_chance should be
    sharply identified (curvature > 0.5) because earlier work showed
    recovery dominates the trajectory shape. Fisher eigendecomposition
    should report the smallest eigenvalue's eigenvector loadings.

ε — verify_execution:
    Against the handcrafted model at MAP (which is known-correct),
    the execution verifier should produce zero mismatches. This
    validates the GOOD case — verifier isn't false-positive on
    correct code. A future task #G dogfood against a buggy model
    would validate the BAD case.

Usage:
    python tests/e2e/dogfood_algorithms.py [N_alpha=3]
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO))

from abm_auto import config
from abm_auto.calibration.calibrator import fit_from_files
from abm_auto.calibration.identifiability_profile import (
    fisher_info_eigen,
    profile_likelihood,
)
from abm_auto.calibration.posterior import (
    run_final_validation_sim,
    write_best_params,
)
from abm_auto.calibration.simulator import SimulatorWrapper
from abm_auto.calibration.summary_stats import (
    full_trajectory,
    trajectory_features,
)
from abm_auto.llm import make_client
from abm_auto.runner.executor import Executor
from abm_auto.runner.workspace import Workspace
from abm_auto.verification.execution_verifier import verify_execution


MODEL_DIR = REPO / "examples" / "calibration_challenge_virus" / "handcrafted_model"
OBSERVED = REPO / "examples" / "calibration_challenge_virus" / "observed.csv"
STORY = REPO / "examples" / "calibration_challenge_virus" / "story.md"
REPORT = REPO / "docs" / "dogfood" / f"{time.strftime('%Y-%m-%d')}-algorithms.md"

PARAMS_SPECS = [
    {"name": "virus_spread_chance",    "min": 0,  "max": 20,  "unit": "percent"},
    {"name": "recovery_chance",        "min": 0,  "max": 5,   "unit": "percent"},
    {"name": "gain_resistance_chance", "min": 0,  "max": 100, "unit": "percent"},
]
TARGETS = ["susceptible", "infected", "resistant"]
GROUND_TRUTH = {
    "virus_spread_chance": 4.4,
    "recovery_chance": 2.5,
    "gain_resistance_chance": 25.0,
}
FULL_TRAJ_BASELINE_MSE = 44.5  # from commit 00ad49b


# ── Helpers ────────────────────────────────────────────────────────────


def _score_mse(observed_csv: Path, sim_csv: Path) -> float | None:
    """Compute aggregate MSE between observed.csv and a sim CSV."""
    try:
        from benchmark_calibration_challenge import score_calibration_mse
        res = score_calibration_mse(observed_csv, sim_csv)
        return res.get("aggregate_mse")
    except Exception as e:
        print(f"  MSE scoring failed: {e}")
        return None


def _setup_workspace_with_model(name: str) -> tuple[Workspace, Executor, SimulatorWrapper]:
    """Build a workspace with the handcrafted model pre-installed."""
    ws = Workspace.create(name=name)
    shutil.copytree(MODEL_DIR, ws.model_dir, dirs_exist_ok=True)
    # Wipe stale output
    out = ws.model_dir / "data" / "output"
    if out.exists():
        shutil.rmtree(out)
    executor = Executor(ws, timeout=120)
    sim = SimulatorWrapper(ws, executor, summary_fn=full_trajectory)
    return ws, executor, sim


def _gt_relative_errors(best_params: dict[str, float]) -> dict[str, float]:
    return {
        name: abs(best_params.get(name, 0) - truth) / truth * 100
        for name, truth in GROUND_TRUTH.items() if truth != 0
    }


# ── α experiment ───────────────────────────────────────────────────────


def exp_alpha(n_runs: int = 3) -> dict[str, Any]:
    """Calibrate n_runs × with `trajectory_features` summary; score final sims."""
    print(f"\n=== α: trajectory_features × {n_runs} runs ===")
    results = []
    for i in range(n_runs):
        name = f"alpha_dogfood_{int(time.time())}_{i}"
        t0 = time.time()
        result, ws = fit_from_files(
            model_dir=MODEL_DIR,
            observed_csv=OBSERVED,
            params_specs=PARAMS_SPECS,
            targets=TARGETS,
            max_sims=100,
            summary_fn=trajectory_features,
            workspace_name=name,
        )
        if not result.ok:
            print(f"  [{i+1}/{n_runs}] FAILED: {result.reason}")
            continue
        # Final validation sim
        write_best_params(ws, result)
        executor = Executor(ws, timeout=120)
        sim = SimulatorWrapper(ws, executor, base_run_id=99000)
        final_csv = run_final_validation_sim(sim, result.best_params, ws)
        mse = _score_mse(OBSERVED, final_csv) if final_csv else None
        wall = time.time() - t0
        rel_errs = _gt_relative_errors(result.best_params)
        print(f"  [{i+1}/{n_runs}] MSE={mse} wall={wall:.0f}s "
              f"virus={result.best_params['virus_spread_chance']:.2f} "
              f"recov={result.best_params['recovery_chance']:.2f} "
              f"resist={result.best_params['gain_resistance_chance']:.2f}")
        results.append({
            "best_params": result.best_params,
            "mse": mse,
            "wall": wall,
            "rel_errs": rel_errs,
            "workspace": str(ws.path),
        })

    mses = [r["mse"] for r in results if r.get("mse") is not None]
    aggregate = {
        "n_runs": len(results),
        "mse_mean": float(np.mean(mses)) if mses else None,
        "mse_std": float(np.std(mses)) if len(mses) > 1 else 0.0,
        "mse_min": float(min(mses)) if mses else None,
        "mse_max": float(max(mses)) if mses else None,
        "baseline_mse": FULL_TRAJ_BASELINE_MSE,
        "verdict": None,
    }
    if aggregate["mse_mean"] is not None:
        ratio = aggregate["mse_mean"] / FULL_TRAJ_BASELINE_MSE
        if ratio < 1.2:
            aggregate["verdict"] = f"PASS — within 1.2× of baseline (ratio={ratio:.2f})"
        elif ratio < 2.0:
            aggregate["verdict"] = f"OK — within 2× of baseline (ratio={ratio:.2f})"
        else:
            aggregate["verdict"] = f"WORSE — {ratio:.2f}× baseline (summary may lose too much signal)"
    print(f"\n  α aggregate: MSE={aggregate['mse_mean']} ± {aggregate['mse_std']}  "
          f"baseline={FULL_TRAJ_BASELINE_MSE}  verdict={aggregate['verdict']}")
    return {"per_run": results, "aggregate": aggregate}


# ── β experiment ───────────────────────────────────────────────────────


def exp_beta(map_params: dict[str, float]) -> dict[str, Any]:
    """Profile likelihood + Fisher eigen at α's MAP."""
    print(f"\n=== β: profile_likelihood + fisher_info_eigen at MAP ===")
    print(f"  MAP: {map_params}")

    ws, executor, sim = _setup_workspace_with_model(f"beta_dogfood_{int(time.time())}")
    sim.summary_fn = trajectory_features
    observed = pd.read_csv(OBSERVED)
    obs_stats = trajectory_features(observed, TARGETS)
    priors = {p["name"]: {"min": p["min"], "max": p["max"]} for p in PARAMS_SPECS}

    print("  Running profile_likelihood (3 × 10 grid = 30 sims) ...")
    t0 = time.time()
    profile = profile_likelihood(
        sim, priors, map_params, TARGETS, obs_stats,
        n_grid=10, summary_fn=trajectory_features,
    )
    print(f"    done in {time.time()-t0:.0f}s")
    flat = profile.unidentifiable_params(threshold=0.1)
    for name, prof in profile.per_param.items():
        verdict = "FLAT" if prof.curvature < 0.1 else "identified"
        print(f"    {name}: MAP={prof.map_value:.3f} curvature={prof.curvature:.3f} → {verdict}")

    print("  Running fisher_info_eigen (1 + 2*3² = 19 sims) ...")
    t0 = time.time()
    fisher = fisher_info_eigen(
        sim, priors, map_params, TARGETS, obs_stats,
        summary_fn=trajectory_features,
    )
    print(f"    done in {time.time()-t0:.0f}s")
    if fisher is None:
        print("    Fisher failed (simulator returned None somewhere)")
        return {"profile": profile.to_markdown(), "fisher": "FAILED"}

    print(f"    eigenvalues: {fisher.eigenvalues}")
    flat_dirs = fisher.flat_directions()
    for eig, direction in flat_dirs:
        dir_str = ", ".join(f"{n}={c:+.3f}" for n, c in direction.items())
        print(f"    flat eigenvalue {eig:.4f}: {dir_str}")

    return {
        "map_params": map_params,
        "profile_md": profile.to_markdown(),
        "profile_unidentifiable": flat,
        "fisher_md": fisher.to_markdown(),
        "fisher_eigenvalues": fisher.eigenvalues.tolist(),
        "fisher_flat_count": len(flat_dirs),
        "workspace": str(ws.path),
    }


# ── ε experiment ───────────────────────────────────────────────────────


def exp_epsilon(map_params: dict[str, float]) -> dict[str, Any]:
    """Run sim at MAP, extract claims from story.md, verify execution direction."""
    print(f"\n=== ε: verify_execution at MAP ===")

    ws, executor, _ = _setup_workspace_with_model(f"epsilon_dogfood_{int(time.time())}")
    # Run final sim once
    sim_wrap = SimulatorWrapper(ws, executor, base_run_id=99000)
    final_csv = run_final_validation_sim(sim_wrap, map_params, ws)
    if final_csv is None:
        print("  FAILED: could not produce sim CSV")
        return {"verdict": "FAILED — no sim output"}

    # Get LLM caller via a base agent
    client = make_client(
        provider=config.LLM_PROVIDER,
        api_key=config.get_api_key(),
        base_url=config.get_base_url(),
        timeout=300,
    )

    def llm_caller(system: str, user: str, max_tokens: int = 800, model: str | None = None) -> str:
        """Direct LLM call mirroring BaseAgent.call_llm shape."""
        effective_model = model or config.DEFAULT_MODEL
        return client.create(
            model=effective_model,
            max_tokens=max_tokens,
            system=system,
            user=user,
        )

    story_text = STORY.read_text(encoding="utf-8")
    t0 = time.time()
    result = verify_execution(story_text, final_csv, TARGETS, llm_caller)
    wall = time.time() - t0

    print(f"  done in {wall:.0f}s")
    print(f"  Claims extracted ({len(result.claims)}):")
    for claim in result.claims:
        print(f"    - {claim.target}: {claim.direction}  ({claim.rationale[:60]})")
    print(f"  Actual classifications:")
    for actual in result.actuals:
        print(f"    - {actual.target}: {actual.direction}  "
              f"(peak_ratio={actual.peak_ratio:.2f}, monotonicity={actual.monotonicity:.2f})")
    print(f"  Mismatches: {len(result.mismatches)}")
    for target, expected, actual in result.mismatches:
        print(f"    ✗ {target}: story says {expected!r}, sim shows {actual!r}")

    verdict = "PASS (zero mismatches on known-correct sim)" if result.is_valid \
        else f"FAIL ({len(result.mismatches)} mismatches — verifier false-positive OR sim genuinely off)"
    return {
        "claims": [{"target": c.target, "direction": c.direction, "rationale": c.rationale}
                   for c in result.claims],
        "actuals": [{"target": a.target, "direction": a.direction,
                      "peak_ratio": a.peak_ratio, "monotonicity": a.monotonicity}
                     for a in result.actuals],
        "mismatches": [{"target": t, "expected": e, "actual": a}
                       for t, e, a in result.mismatches],
        "is_valid": result.is_valid,
        "verdict": verdict,
        "workspace": str(ws.path),
    }


# ── Report rendering ───────────────────────────────────────────────────


def render_report(alpha: dict, beta: dict, epsilon: dict) -> str:
    lines = [
        "# Dogfood report — α + β + ε on the virus-on-a-network calibration",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}  ",
        f"**Story**: `examples/calibration_challenge_virus/story.md`  ",
        f"**Observed**: multi-seed (commit 00ad49b)  ",
        f"**Ground truth**: virus=4.4 / recov=2.5 / resist=25.0",
        "",
        "## TL;DR",
        "",
    ]
    agg = alpha["aggregate"]
    lines += [
        f"- **α** ({agg['n_runs']} runs): MSE = "
        f"{agg['mse_mean']:.1f} ± {agg['mse_std']:.1f} "
        f"(baseline {FULL_TRAJ_BASELINE_MSE}) — **{agg['verdict']}**",
        f"- **β** profile: {len(beta.get('profile_unidentifiable', []))} flat params, "
        f"Fisher: {beta.get('fisher_flat_count', '?')} flat directions",
        f"- **ε** verify_execution: {epsilon['verdict']}",
        "",
    ]

    # α detail
    lines += [
        "## α: trajectory_features SummaryStats adapter",
        "",
        "| Run | MSE | Wall (s) | virus | recov | resist |",
        "|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(alpha["per_run"], start=1):
        bp = r["best_params"]
        mse_s = f"{r['mse']:.1f}" if r["mse"] is not None else "—"
        lines.append(
            f"| {i} | {mse_s} | {r['wall']:.0f} | "
            f"{bp['virus_spread_chance']:.3f} | "
            f"{bp['recovery_chance']:.3f} | "
            f"{bp['gain_resistance_chance']:.3f} |"
        )
    lines += [
        "",
        f"**Aggregate MSE**: {agg['mse_mean']:.1f} ± {agg['mse_std']:.1f}  ",
        f"**vs full_trajectory baseline** ({FULL_TRAJ_BASELINE_MSE}): "
        f"ratio = {agg['mse_mean']/FULL_TRAJ_BASELINE_MSE:.2f}×",
        "",
    ]

    # β detail
    lines += ["## β: profile_likelihood + fisher_info_eigen", ""]
    lines += [f"**MAP used**: `{beta.get('map_params', {})}`", ""]
    lines.append(beta.get("profile_md", "(profile failed)"))
    lines.append("")
    lines.append(beta.get("fisher_md", "(fisher failed)"))
    lines.append("")

    # ε detail
    lines += ["## ε: verify_execution", ""]
    lines.append(f"**Verdict**: {epsilon['verdict']}")
    lines.append("")
    if epsilon.get("claims"):
        lines += ["### LLM-extracted claims", ""]
        lines.append("| Target | Direction | Rationale |")
        lines.append("|---|---|---|")
        for c in epsilon["claims"]:
            lines.append(f"| `{c['target']}` | `{c['direction']}` | {c['rationale']} |")
        lines.append("")
    if epsilon.get("actuals"):
        lines += ["### Actual sim trajectory classifications", ""]
        lines.append("| Target | Direction | Peak ratio | Monotonicity |")
        lines.append("|---|---|---|---|")
        for a in epsilon["actuals"]:
            lines.append(f"| `{a['target']}` | `{a['direction']}` | "
                         f"{a['peak_ratio']:.2f} | {a['monotonicity']:.2f} |")
        lines.append("")
    if epsilon.get("mismatches"):
        lines += ["### Mismatches", ""]
        for m in epsilon["mismatches"]:
            lines.append(f"- `{m['target']}`: story says `{m['expected']}`, "
                         f"sim shows `{m['actual']}`")
        lines.append("")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────


def main() -> int:
    n_alpha = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    alpha = exp_alpha(n_runs=n_alpha)
    if not alpha["per_run"]:
        print("\nα failed — no successful runs to seed β/ε with a MAP")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(render_report(alpha, {}, {"verdict": "skipped"}), encoding="utf-8")
        return 1

    # Use first run's best_params as MAP for β + ε
    map_params = alpha["per_run"][0]["best_params"]

    beta = exp_beta(map_params)
    epsilon = exp_epsilon(map_params)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render_report(alpha, beta, epsilon), encoding="utf-8")
    print(f"\n→ Report: {REPORT}")

    # JSON dump for forensics
    json_path = REPORT.with_suffix(".json")
    json_path.write_text(json.dumps({
        "alpha": alpha,
        "beta": beta,
        "epsilon": epsilon,
    }, indent=2, default=str), encoding="utf-8")
    print(f"→ Raw data: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
