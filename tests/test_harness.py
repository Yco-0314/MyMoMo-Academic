"""Tests for Harness — tier-aware orchestration of Gates (ADR-013).

Proves the molecule works end-to-end on the real five Gates: family
routing, skip-on-absent-family, and — the load-bearing part — tier-
separated aggregation that never confuses "structurally wrong"
(verification fail) with "no signal" (refutation fail).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from abm_auto.analysis.critical_slowing_down import critical_slowing_down
from abm_auto.analysis.null_gate import NullGate
from abm_auto.calibration.diagnostics_halt_gate import DiagnosticsHaltGate
from abm_auto.codegen.anti_pattern_gate import AntiPatternGate
from abm_auto.codegen.structural_fidelity_gate import (
    StructuralFidelityGate,
    StructuralFidelityInput,
)
from abm_auto.verification.execution_diff_gate import (
    ExecutionDiffGate,
    ExecutionDiffInput,
)
from abm_auto.verification.execution_verifier import QualitativeClaim
from abm_auto.verification.harness import Harness, HarnessReport


def _stat(s: np.ndarray) -> float:
    return critical_slowing_down(s).ews_strength


def _rising(n: int = 200) -> np.ndarray:
    rng = np.random.default_rng(0)
    x = np.zeros(n)
    a = np.linspace(0.1, 0.95, n)
    for t in range(1, n):
        x[t] = a[t] * x[t - 1] + rng.normal(0, 0.1)
    return x


def _all_gates():
    return [
        AntiPatternGate(),
        StructuralFidelityGate(),
        DiagnosticsHaltGate(),
        NullGate(_stat, seed=1),
        ExecutionDiffGate(),
    ]


def _decreasing_csv(tmp: Path) -> Path:
    csv = tmp / "sim.csv"
    csv.write_text("tick,susceptible\n" + "\n".join(f"{t},{100 - 4 * t}" for t in range(20)) + "\n")
    return csv


def test_skip_on_absent_family() -> None:
    """A Gate whose family isn't in artifacts is SKIPPED, not failed."""
    rep = Harness().run([AntiPatternGate()], artifacts={})  # no source_code
    assert rep.verdicts == []
    assert rep.skipped == ["anti_pattern"]
    assert rep.verification_clear is True  # vacuously — nothing ran


def test_healthy_run_all_clear(tmp_path: Path) -> None:
    art = {
        "source_code": {"core/model.py": "class M:\n    pass\n"},
        "spec_and_code": StructuralFidelityInput({"scenario_params": [], "agent_state_vars": []}, {}),
        "diagnostics_signal": {"n_params": 3, "n_flat_params": 0, "n_eps_claims": 3, "n_eps_mismatches": 0},
        "scalar_trajectory": _rising(),
        "trajectory_vs_claims": ExecutionDiffInput(
            [QualitativeClaim("susceptible", "monotonic_decrease")],
            _decreasing_csv(tmp_path), ["susceptible"]),
    }
    rep = Harness().run(_all_gates(), art)
    assert isinstance(rep, HarnessReport)
    assert rep.verification_clear is True
    # all three refutation gates survive: rising beats null, sim matches
    # claim, and clean diagnostics (no flat params, no eps mismatch) is
    # "not refuted as broken". DiagnosticsHaltGate is refutation tier too.
    assert set(rep.refutation_survived) == {
        "surrogate_null", "execution_diff", "diagnostics_halt",
    }
    assert rep.refutation_failed == []


def test_verification_defect_is_hard_door(tmp_path: Path) -> None:
    """Bad code → verification door reads DEFECT, regardless of refutation."""
    art = {
        "source_code": {"core/model.py": "from abm_auto.runtime import NetworkGrid\n"},
        "scalar_trajectory": _rising(),  # this still survives its null
    }
    rep = Harness().run(_all_gates(), art)
    assert rep.verification_clear is False
    assert any(v.gate_name == "anti_pattern" for v in rep.verification_failures)


def test_tiers_do_not_collapse(tmp_path: Path) -> None:
    """The load-bearing property: a refutation FAIL (no signal) must NOT
    pull the verification door to DEFECT, and a verification DEFECT must
    NOT be reported as a mere 'no signal'. They are separate axes."""
    white = np.random.default_rng(2).normal(0, 1, 200)
    art = {
        # verification: clean → door stays CLEAR
        "source_code": {"core/model.py": "class M:\n    pass\n"},
        # refutation: white noise → no signal (a failure, but NOT a defect)
        "scalar_trajectory": white,
    }
    rep = Harness().run(_all_gates(), art)
    assert rep.verification_clear is True          # clean code → door clear
    assert "surrogate_null" in rep.refutation_failed  # no signal recorded
    # the refutation failure did NOT contaminate the verification door
    assert rep.verification_failures == []


def test_diagnostics_all_flat_is_refutation_failure() -> None:
    """All-flat diagnostics is a refutation failure (no-signal/ broken),
    recorded in the refutation column, not the verification door."""
    art = {"diagnostics_signal": {"n_params": 3, "n_flat_params": 3,
                                  "n_eps_claims": 0, "n_eps_mismatches": 0}}
    rep = Harness().run([DiagnosticsHaltGate()], art)
    assert "diagnostics_halt" in rep.refutation_failed
    assert rep.verification_clear is True  # no verification gate ran


def test_render_is_tier_separated(tmp_path: Path) -> None:
    art = {
        "source_code": {"core/model.py": "class M:\n    pass\n"},
        "scalar_trajectory": _rising(),
    }
    rendered = Harness().run(_all_gates(), art).render()
    assert "verification (hard door)" in rendered
    assert "refutation (evidence)" in rendered
    # honest wording: refutation survivors say "not refuted", never "verified"
    assert "verified" not in rendered


def test_deterministic() -> None:
    art = {"scalar_trajectory": _rising()}
    r1 = Harness().run([NullGate(_stat, seed=1)], art)
    r2 = Harness().run([NullGate(_stat, seed=1)], art)
    assert r1.refutation_survived == r2.refutation_survived
