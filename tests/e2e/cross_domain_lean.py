"""Cross-domain LEAN calibration E2E — SIR + Opinion + Schelling.

Catches the kind of cross-domain regression that broke Opinion + Schelling
on 2026-05-29 dogfood: calibration backend assumes SIR-shaped trajectories,
fails silently on different column counts / dynamics.

Wave B (2026-05-31): each domain also runs profile_likelihood after the
fit to sanity-check identifiability. Schelling's MSE 0.000 raised the
question "is this fit honest or is the loss landscape degenerate?";
the diag pass distinguishes the two by sweeping each parameter and
reporting the profile curvature.

Why lean (not full Pipeline)
----------------------------
Earlier smoke test with full Pipeline (--external-model) showed ~29 min
WALL PER DOMAIN — 90 min for three domains is too slow for daily CI.
The bulk of that time is Designer / MechanismExtractor / Reporter LLM
calls, which the existing dogfood (SIR through full Pipeline) already
exercises. For cross-domain we only need to catch CALIBRATION-LAYER
regressions; fit_from_files runs each domain in ~100s.

The full-Pipeline dogfood (SIR) catches Pipeline-orchestration
regressions. This script catches calibration-layer regressions across
three different dynamical regimes. The two together cover most of the
"will it work on a different domain?" surface.

Per-domain MSE thresholds (margin above the seed=42 deterministic
baseline so transient sim noise doesn't false-fail):

  SIR (virus):    200   (seeded baseline ≈ 152; gate vs broken-state 1480)
  Opinion:        0.5   (seeded baseline ≈ 0.025)
  Schelling:      0.5   (seeded baseline 0.000)

These thresholds catch CALIBRATION-LAYER regressions (the kind that
turned MSE 47 into 1480 on 2026-05-28), not minor RF surrogate noise.

Total cost in CI: ~5 min wall, zero LLM cost (no LLM calls in lean path).

Usage:
    python tests/e2e/cross_domain_lean.py
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO))

# Pin RNG for reproducible CI. The RF screening backend draws prior
# samples via np.random.uniform; without a fixed seed the per-domain
# MSE varies run-to-run by 3-4× (SIR observed range 36–133 across
# unseeded runs). 42 is the seed under which thresholds were calibrated.
np.random.seed(42)

import pandas as pd

from abm_auto.calibration.calibrator import fit_from_files
from abm_auto.calibration.identifiability_profile import (
    ProfileResult,
    profile_likelihood,
)
from abm_auto.calibration.posterior import (
    run_final_validation_sim,
    write_best_params,
)
from abm_auto.calibration.simulator import SimulatorWrapper
from abm_auto.calibration.summary_stats import full_trajectory
from abm_auto.runner.executor import Executor


@dataclass
class Domain:
    name: str
    model_dir: Path
    observed: Path
    params_specs: list
    targets: list[str]
    mse_threshold: float


DOMAINS: list[Domain] = [
    Domain(
        name="sir-virus",
        model_dir=REPO / "examples/calibration_challenge_virus/handcrafted_model",
        observed=REPO / "examples/calibration_challenge_virus/observed.csv",
        params_specs=[
            {"name": "virus_spread_chance",    "min": 0,  "max": 20,  "unit": "percent"},
            {"name": "recovery_chance",        "min": 0,  "max": 5,   "unit": "percent"},
            {"name": "gain_resistance_chance", "min": 0,  "max": 100, "unit": "percent"},
        ],
        targets=["susceptible", "infected", "resistant"],
        mse_threshold=200.0,
    ),
    Domain(
        name="opinion-deffuant",
        model_dir=REPO / "examples/calibration_challenge_opinion/handcrafted_model",
        observed=REPO / "examples/calibration_challenge_opinion/observed.csv",
        params_specs=[
            {"name": "confidence_threshold", "min": 0.05, "max": 0.50, "unit": "probability"},
            {"name": "convergence_rate",     "min": 0.05, "max": 0.50, "unit": "probability"},
        ],
        targets=["mean_opinion", "opinion_variance", "n_clusters"],
        mse_threshold=0.5,
    ),
    Domain(
        name="schelling-segregation",
        model_dir=REPO / "examples/calibration_challenge_schelling/handcrafted_model",
        observed=REPO / "examples/calibration_challenge_schelling/observed.csv",
        params_specs=[
            {"name": "tolerance", "min": 0.10, "max": 0.80, "unit": "probability"},
        ],
        targets=["n_unhappy", "segregation_index", "fraction_segregated"],
        mse_threshold=0.5,
    ),
]


@dataclass
class DomainResult:
    domain: str
    wall_seconds: float
    best_params: dict | None
    mse: float | None
    threshold: float
    verdict: str
    failure_reason: str = ""
    diag_status: str = ""        # "all identified" | "FLAT: <p1>, <p2>" | "skipped" | "error"
    diag_flat_params: list[str] = None   # list of flat param names (Wave B)
    diag_report_path: str = ""


def _score_mse(observed: Path, simulated: Path) -> float | None:
    try:
        from benchmark_calibration_challenge import score_calibration_mse
        res = score_calibration_mse(observed, simulated)
        return res.get("aggregate_mse")
    except Exception as e:
        print(f"    score_mse failed: {e}", flush=True)
        return None


# Curvature threshold below which `profile_likelihood` flags a param as
# FLAT (unidentifiable). Picked to match `ProfileResult.unidentifiable_params`'s
# default 0.1. Schelling's 1-param tolerance is the first test case —
# with MSE 0.000 in the cross-domain baseline, the question is whether
# the loss is genuinely insensitive to tolerance (flat) or whether
# every tolerance sweep produces near-zero MSE (also flat, but for
# different reasons).
_FLAT_CURVATURE_THRESHOLD = 0.1


def _run_diagnostics(
    workspace,
    executor,
    domain: Domain,
    best_params: dict,
    observed: pd.DataFrame,
) -> tuple[str, list[str], Path | None]:
    """Run profile_likelihood per param; return (status, flat_params, report_path).

    Cost: n_params × 15 grid sims per domain (≈12-45s extra). Worth the
    overhead because identifiability artifacts (Schelling MSE 0.000) are
    the kind of thing pure MSE thresholds can't catch — a calibration
    can be "successful" by MSE while the parameter is actually
    underdetermined.
    """
    priors = {
        s["name"]: {"min": float(s["min"]), "max": float(s["max"])}
        for s in domain.params_specs
    }
    sim = SimulatorWrapper(
        workspace, executor,
        base_run_id=80000,
        summary_fn=full_trajectory,
        expected_rows=len(observed),
    )
    obs_stats = full_trajectory(observed, domain.targets)
    try:
        profile: ProfileResult = profile_likelihood(
            sim, priors, best_params, domain.targets, obs_stats,
            n_grid=15, summary_fn=full_trajectory,
        )
    except Exception as e:
        return f"error: {type(e).__name__}: {e}", [], None

    flat = profile.unidentifiable_params(threshold=_FLAT_CURVATURE_THRESHOLD)
    md = profile.to_markdown()
    report_path = workspace.path / "diagnostics_profile.md"
    report_path.write_text(md, encoding="utf-8")
    status = "all identified" if not flat else f"FLAT: {', '.join(flat)}"
    return status, flat, report_path


def run_domain(domain: Domain) -> DomainResult:
    """Lean fit_from_files + final validation sim per domain."""
    print(f"\n=== {domain.name} ===", flush=True)
    name = f"cross_domain_lean_{domain.name}_{int(time.time())}"
    t0 = time.time()
    try:
        result, ws = fit_from_files(
            model_dir=domain.model_dir,
            observed_csv=domain.observed,
            params_specs=domain.params_specs,
            targets=domain.targets,
            max_sims=100,
            workspace_name=name,
        )
    except Exception as e:
        return DomainResult(
            domain=domain.name, wall_seconds=time.time() - t0,
            best_params=None, mse=None,
            threshold=domain.mse_threshold,
            verdict="ERROR", failure_reason=f"fit_from_files raised: {type(e).__name__}: {e}",
        )

    if not result.ok:
        return DomainResult(
            domain=domain.name, wall_seconds=time.time() - t0,
            best_params=None, mse=None,
            threshold=domain.mse_threshold,
            verdict="FAIL", failure_reason=f"fit not OK: {result.reason}",
        )

    write_best_params(ws, result)
    executor = Executor(ws, timeout=120)
    sim = SimulatorWrapper(ws, executor, base_run_id=99000)
    final_csv = run_final_validation_sim(sim, result.best_params, ws)
    wall = time.time() - t0
    if final_csv is None:
        return DomainResult(
            domain=domain.name, wall_seconds=wall,
            best_params=result.best_params, mse=None,
            threshold=domain.mse_threshold,
            verdict="FAIL", failure_reason="final validation sim returned None",
        )

    mse = _score_mse(domain.observed, final_csv)
    if mse is None:
        return DomainResult(
            domain=domain.name, wall_seconds=wall,
            best_params=result.best_params, mse=None,
            threshold=domain.mse_threshold,
            verdict="FAIL", failure_reason="MSE scoring returned None",
        )
    verdict = "PASS" if mse <= domain.mse_threshold else "FAIL"
    reason = "" if verdict == "PASS" else f"MSE {mse:.3f} > threshold {domain.mse_threshold}"

    # Wave B: profile_likelihood sanity. Adds ~12-45s/domain.
    print(f"  running profile_likelihood ({len(domain.params_specs)}×15 sims)...", flush=True)
    observed_df = pd.read_csv(domain.observed)
    diag_status, diag_flat, diag_path = _run_diagnostics(
        ws, executor, domain, result.best_params, observed_df,
    )
    wall = time.time() - t0  # include diag wall

    return DomainResult(
        domain=domain.name, wall_seconds=wall,
        best_params=result.best_params, mse=mse,
        threshold=domain.mse_threshold,
        verdict=verdict, failure_reason=reason,
        diag_status=diag_status,
        diag_flat_params=diag_flat,
        diag_report_path=str(diag_path) if diag_path else "",
    )


def main() -> int:
    results: list[DomainResult] = []
    for domain in DOMAINS:
        results.append(run_domain(domain))

    print("\n" + "=" * 60, flush=True)
    print("Cross-domain LEAN calibration summary", flush=True)
    print("=" * 60, flush=True)
    print(f"{'Domain':<26} {'Verdict':<8} {'MSE':<10} {'Wall':<6} {'Diag':<30}", flush=True)
    print("-" * 80, flush=True)
    n_fail = 0
    for r in results:
        mse_s = f"{r.mse:.3f}" if r.mse is not None else "—"
        diag_s = r.diag_status[:28] if r.diag_status else "—"
        print(f"{r.domain:<26} {r.verdict:<8} {mse_s:<10} {r.wall_seconds:<5.0f} {diag_s}", flush=True)
        if r.verdict != "PASS":
            n_fail += 1
            print(f"  reason: {r.failure_reason}", flush=True)

    summary_path = REPO / "docs" / "dogfood" / f"cross-domain-lean-{int(time.time())}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps([
        {
            "domain": r.domain, "verdict": r.verdict,
            "mse": r.mse, "threshold": r.threshold,
            "wall_seconds": r.wall_seconds,
            "best_params": r.best_params,
            "failure_reason": r.failure_reason,
            "diag_status": r.diag_status,
            "diag_flat_params": r.diag_flat_params or [],
            "diag_report_path": r.diag_report_path,
        }
        for r in results
    ], indent=2, default=str), encoding="utf-8")
    print(f"\nSummary: {summary_path}", flush=True)

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
