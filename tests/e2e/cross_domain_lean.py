"""Cross-domain LEAN calibration E2E — SIR + Opinion + Schelling.

Catches the kind of cross-domain regression that broke Opinion + Schelling
on 2026-05-29 dogfood: calibration backend assumes SIR-shaped trajectories,
fails silently on different column counts / dynamics.

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

from abm_auto.calibration.calibrator import fit_from_files
from abm_auto.calibration.posterior import (
    run_final_validation_sim,
    write_best_params,
)
from abm_auto.calibration.simulator import SimulatorWrapper
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


def _score_mse(observed: Path, simulated: Path) -> float | None:
    try:
        from benchmark_calibration_challenge import score_calibration_mse
        res = score_calibration_mse(observed, simulated)
        return res.get("aggregate_mse")
    except Exception as e:
        print(f"    score_mse failed: {e}", flush=True)
        return None


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
    return DomainResult(
        domain=domain.name, wall_seconds=wall,
        best_params=result.best_params, mse=mse,
        threshold=domain.mse_threshold,
        verdict=verdict, failure_reason=reason,
    )


def main() -> int:
    results: list[DomainResult] = []
    for domain in DOMAINS:
        results.append(run_domain(domain))

    print("\n" + "=" * 60, flush=True)
    print("Cross-domain LEAN calibration summary", flush=True)
    print("=" * 60, flush=True)
    print(f"{'Domain':<26} {'Verdict':<8} {'MSE':<10} {'Threshold':<10} {'Wall (s)':<8}", flush=True)
    print("-" * 60, flush=True)
    n_fail = 0
    for r in results:
        mse_s = f"{r.mse:.3f}" if r.mse is not None else "—"
        print(f"{r.domain:<26} {r.verdict:<8} {mse_s:<10} {r.threshold:<10} {r.wall_seconds:.0f}", flush=True)
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
        }
        for r in results
    ], indent=2, default=str), encoding="utf-8")
    print(f"\nSummary: {summary_path}", flush=True)

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
