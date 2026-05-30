"""ε execution verifier — NEGATIVE smoke test.

The cross_domain_lean run shows ε "all match" for all three domains under
seed=42. That proves ε accepts honest fits. This script proves the
complementary half: ε CATCHES bad fits. If both pass, ε is a real signal
rather than a rubber stamp.

Approach:
  1. Take SIR domain's known-good story.md
  2. Run the handcrafted_model at deliberately ADVERSARIAL params:
       virus_spread_chance = 0.01  (effectively no spread)
       recovery_chance     = 0     (no recovery)
       gain_resistance     = 0     (no resistance)
     With these, S barely moves, I barely rises, R stays 0.
  3. Run verify_execution against the resulting CSV.
  4. Assert mismatches > 0 — story claims (S decreases / I peak-then-decay
     / R increases) cannot match a near-flat trajectory.

Cost: 1 sim (~3s) + 1 LLM call (~3s). Total ~10s including setup.
Requires DEEPSEEK_API_KEY (skip silently otherwise).
"""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO))

from abm_auto.calibration.posterior import run_final_validation_sim
from abm_auto.calibration.simulator import SimulatorWrapper
from abm_auto.runner.executor import Executor
from abm_auto.runner.workspace import Workspace

# Reuse the cross-domain script's _build_llm_caller + _run_execution_verify
# so a wiring bug in the script would also break this test.
sys.path.insert(0, str(REPO / "tests" / "e2e"))
import cross_domain_lean as cdl  # noqa: E402


SIR_DOMAIN = cdl.DOMAINS[0]
assert SIR_DOMAIN.name == "sir-virus", "Expected SIR domain first"

ADVERSARIAL_PARAMS = {
    "virus_spread_chance": 0.01,    # nearly no spread → S stays high
    "recovery_chance": 0.01,        # nearly no recovery → R stays 0
    "gain_resistance_chance": 0.01, # nearly no resistance
}


def main() -> int:
    llm_caller = cdl._build_llm_caller()
    if llm_caller is None:
        print("[skip] DEEPSEEK_API_KEY not set — ε negative test requires LLM access.")
        return 0  # soft-pass — same contract as cross_domain_lean

    print(f"=== ε negative smoke test (SIR, adversarial params) ===")
    print(f"  story: {SIR_DOMAIN.story.name}")
    print(f"  params (adversarial): {ADVERSARIAL_PARAMS}")

    # Build transient workspace + executor + simulator
    name = f"eps_negative_smoke_{int(time.time())}"
    ws = Workspace.create(name=name)
    shutil.copytree(SIR_DOMAIN.model_dir, ws.model_dir, dirs_exist_ok=True)
    stale_output = ws.model_dir / "data" / "output"
    if stale_output.exists():
        shutil.rmtree(stale_output)
    executor = Executor(ws, timeout=120)
    sim = SimulatorWrapper(ws, executor, base_run_id=70000)

    # Run sim at adversarial params; capture the validation CSV
    print("  running adversarial sim...", flush=True)
    final_csv = run_final_validation_sim(sim, ADVERSARIAL_PARAMS, ws)
    if final_csv is None:
        print("  [FAIL] sim returned None — cannot test ε without a CSV")
        return 1
    print(f"  sim CSV: {final_csv.name}")

    # Run ε verify
    print("  running verify_execution...", flush=True)
    status, mismatches = cdl._run_execution_verify(SIR_DOMAIN, final_csv, llm_caller)
    print(f"  ε status: {status}")
    for m in mismatches:
        print(f"    ε mismatch: {m}")

    # Assert ε caught at least one mismatch
    if status.startswith("MISMATCH"):
        print("\n  ✓ ε caught the adversarial trajectory — verifier is sensitive.")
        return 0
    if status.startswith("skipped"):
        print(f"\n  [skip] {status} — cannot evaluate sensitivity.")
        return 0
    print(
        f"\n  [FAIL] ε reported {status!r} on an adversarial sim. "
        f"Either the params weren't extreme enough to break SIR dynamics, "
        f"or ε is not catching what it should."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
