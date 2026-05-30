"""Byte-equal regression fixture for Engine Phase 1 (Scenario extraction).

ADR-009 phase 1 swaps `Melodie.Scenario` for a standalone
`abm_auto.runtime._scenario.Scenario`. The swap is only safe if the
resulting sim trajectories are byte-identical to the pre-swap version
on a fixed seed + fixed params — a Scenario subclass that silently
changes attribute-load order, deep-copy semantics, or attribute lookup
would change the trajectory without raising an error.

This fixture captures the reference CSV BEFORE the swap (Melodie.Scenario
still in use). After the swap lands, the same script re-runs and the
test PASSES iff the CSV is byte-identical to the reference.

To regenerate the reference (after a deliberate intended change):

    REGENERATE_REF=1 python tests/e2e/test_engine_phase1_baseline.py

Or via pytest:

    REGENERATE_REF=1 pytest tests/e2e/test_engine_phase1_baseline.py

Fixed inputs:
  - SIR handcrafted_model (canonical reference)
  - best_params from cross_domain_lean's seeded baseline
    (virus 4.115, recovery 3.545, gain_resistance 29.117)
  - scenario.seed = 0 (model-internal RNG seed lives in scenario.py)
  - Single run, no calibration loop

Wall time: ~3-5 seconds.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO))

from abm_auto.calibration.posterior import run_final_validation_sim
from abm_auto.calibration.simulator import SimulatorWrapper
from abm_auto.runner.executor import Executor
from abm_auto.runner.workspace import Workspace


# Reference params chosen to be SIR's cross_domain_lean seeded best.
# These produce a deterministic trajectory under scenario.seed=0.
REFERENCE_PARAMS = {
    "virus_spread_chance": 4.114565187299529,
    "recovery_chance": 3.5453668619314618,
    "gain_resistance_chance": 29.11713388275542,
}

REFERENCE_CSV = REPO / "tests" / "e2e" / "fixtures" / "engine_phase1_sir_reference.csv"

MODEL_DIR = REPO / "examples" / "calibration_challenge_virus" / "handcrafted_model"


def _produce_sim_csv(workspace_name: str) -> Path:
    """Run SIR handcrafted_model at REFERENCE_PARAMS once. Return output path."""
    ws = Workspace.create(name=workspace_name)
    shutil.copytree(MODEL_DIR, ws.model_dir, dirs_exist_ok=True)
    stale = ws.model_dir / "data" / "output"
    if stale.exists():
        shutil.rmtree(stale)

    executor = Executor(ws, timeout=120)
    sim = SimulatorWrapper(ws, executor, base_run_id=60000)
    final_csv = run_final_validation_sim(sim, REFERENCE_PARAMS, ws)
    assert final_csv is not None, "run_final_validation_sim returned None"
    return final_csv


def _regenerate_reference() -> None:
    """Write the reference CSV from the current Scenario implementation."""
    REFERENCE_CSV.parent.mkdir(parents=True, exist_ok=True)
    final_csv = _produce_sim_csv("engine_phase1_baseline_regen")
    shutil.copyfile(final_csv, REFERENCE_CSV)
    print(f"Reference regenerated: {REFERENCE_CSV} ({REFERENCE_CSV.stat().st_size} bytes)")


def test_sir_baseline_byte_equal() -> None:
    """SIR handcrafted_model at REFERENCE_PARAMS must produce a byte-equal CSV.

    If the reference is missing, fails with instructions to regenerate.
    If the produced CSV differs from reference, fails with the first
    differing line for inspection.

    Why byte-equal not MSE-equal: an MSE threshold tolerates ~10% drift,
    which would hide subtle Scenario-swap bugs (e.g., off-by-one in
    attribute initialization, RNG seed propagation). A byte-equal gate
    on a fixed-seed run catches them immediately.
    """
    if not REFERENCE_CSV.exists():
        pytest.fail(
            f"Reference CSV missing at {REFERENCE_CSV}.\n"
            f"Run with REGENERATE_REF=1 to create it:\n"
            f"  REGENERATE_REF=1 python tests/e2e/test_engine_phase1_baseline.py"
        )

    produced = _produce_sim_csv("engine_phase1_baseline_check")
    ref_bytes = REFERENCE_CSV.read_bytes()
    new_bytes = produced.read_bytes()

    if ref_bytes == new_bytes:
        return  # PASS

    # Byte diff — find first differing line for context
    ref_lines = ref_bytes.decode().splitlines()
    new_lines = new_bytes.decode().splitlines()
    for i, (a, b) in enumerate(zip(ref_lines, new_lines)):
        if a != b:
            pytest.fail(
                f"CSV byte mismatch at line {i + 1}:\n"
                f"  reference: {a!r}\n"
                f"  produced:  {b!r}\n"
                f"Either intentional (regenerate via REGENERATE_REF=1) or "
                f"a Scenario-swap regression (investigate __init__/setup/copy)."
            )
    # Same prefix, different length
    pytest.fail(
        f"CSV length differs: reference {len(ref_lines)} lines, "
        f"produced {len(new_lines)} lines."
    )


def main() -> int:
    if os.environ.get("REGENERATE_REF") == "1":
        _regenerate_reference()
        return 0
    # Standalone run: just exercise the test
    try:
        test_sir_baseline_byte_equal()
        print("✓ byte-equal check PASS")
        return 0
    except SystemExit:
        raise
    except Exception as e:
        print(f"FAIL: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
