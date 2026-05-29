"""Diagnose the BayesianCalibrator '0 successful sims' bug.

The 2026-05-29 Layer-3 dogfood found calibrator's 100 sample sims all
returned None silently. With the instrumentation patch on
SimulatorWrapper.simulate (commit pending), each failure is now logged
WITH KIND. This script invokes simulate() 5 times against the dogfood
workspace's generated model — output shows the FIRST failure kind, which
is the root cause.

Usage:
    python tests/e2e/diagnose_calibrator_zero_sims.py [workspace_path]

Default workspace: most recent dogfood_codegen_* dir under workspace/
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO))

from abm_auto.calibration.simulator import SimulatorWrapper
from abm_auto.runner.executor import Executor
from abm_auto.runner.workspace import Workspace


def find_latest_dogfood() -> Path | None:
    candidates = sorted(
        (REPO / "workspace").glob("dogfood_codegen_*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def main() -> int:
    ws_path = Path(sys.argv[1]) if len(sys.argv) > 1 else find_latest_dogfood()
    if not ws_path or not ws_path.exists():
        print(f"ERROR: workspace not found ({ws_path})")
        return 1
    print(f"Workspace: {ws_path}")

    ws = Workspace.load(ws_path)
    executor = Executor(ws, timeout=60)
    sim = SimulatorWrapper(ws, executor, base_run_id=99000)

    # Priors matching the BEHAVE virus story spec
    priors = {
        "virus_spread_chance": {"min": 0.0, "max": 20.0},
        "recovery_chance":     {"min": 0.0, "max": 5.0},
        "gain_resistance_chance": {"min": 0.0, "max": 100.0},
    }
    targets = ["susceptible", "infected", "resistant"]

    print(f"\nRunning 5 simulate() calls with random priors:")
    rng = np.random.default_rng(42)
    for i in range(5):
        params = {
            name: float(rng.uniform(p["min"], p["max"]))
            for name, p in priors.items()
        }
        print(f"\n[{i+1}/5] params = {params}")
        result = sim.simulate(params, targets)
        if result is None:
            kind = getattr(sim, "_last_failure_kind", "<unknown>")
            print(f"  → FAIL (kind={kind})")
        else:
            print(f"  → OK (vector shape {result.shape}, "
                  f"sum {result.sum():.1f})")

    print(f"\nFinal _logged_failure_kinds: "
          f"{getattr(sim, '_logged_failure_kinds', '<none>')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
