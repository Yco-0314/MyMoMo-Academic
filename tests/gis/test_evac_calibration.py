"""Tests for ladder #5 — evacuation outcome calibration + parameter recovery.

Honest scope: proves the calibration CAPABILITY works (belief recovered from outcomes via
base ABC), NOT a tuning of the #10 reproduction to the paper.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.gis._evac_calibration import (
    EvacOutcomeObjective,
    belief_recovery_gate,
    diagnose_evac_calibration,
    evac_calibration_diagnostic_gate,
    run_evac_calibration,
)

_FIXED = dict(alarm_t=0, onset_steps=20, mobility_good_frac=0.7,
              collaboration=False, n_agents=100, max_steps=150)


def test_objective_returns_evac_incap_and_is_deterministic():
    obj = EvacOutcomeObjective(fixed=_FIXED, n_iter=5, base_seed=0)
    s1 = obj.simulate({"belief": 0.5})
    s2 = obj.simulate({"belief": 0.5})
    assert s1.shape == (2,)                 # [evac, incap]
    assert np.allclose(s1, s2)              # same params + base_seed -> identical
    assert abs(s1[0] + s1[1] - 100) < 1e-6  # evac + incap = n_agents (slow-onset, all resolve)


def test_objective_rejects_wrong_targets():
    with pytest.raises(ValueError, match="evac"):
        EvacOutcomeObjective(fixed=_FIXED).simulate({"belief": 0.5}, targets=["spatial_loss"])


def test_belief_is_recovered_from_outcomes():
    # parameter recovery: a known belief -> observed outcome -> ABC recovers it
    ok, msg = belief_recovery_gate(true_belief=0.55, tol=0.15, max_sims=250, n_iter=8, seed=42)
    assert ok, msg


def test_run_evac_calibration_reports_backend_and_calls():
    truth = EvacOutcomeObjective(fixed=_FIXED, n_iter=6, base_seed=0)
    observed = truth.simulate({"belief": 0.4})
    out = run_evac_calibration(observed, {"belief": {"min": 0.0, "max": 1.0}}, _FIXED,
                               max_sims=120, n_iter=6, seed=7)
    assert out["ok"] is True
    assert out["backend"].startswith("evac-outcome+")
    assert out["n_simulator_calls"] > 0
    assert 0.0 <= out["best_params"]["belief"] <= 1.0


def test_diagnose_evac_calibration_reports_best_fit_residuals():
    truth = EvacOutcomeObjective(fixed=_FIXED, n_iter=6, base_seed=0)
    observed = truth.simulate({"belief": 0.45})
    out = diagnose_evac_calibration(
        observed,
        {"belief": {"min": 0.0, "max": 1.0}},
        _FIXED,
        max_sims=180,
        n_iter=6,
        seed=11,
        residual_tol=8.0,
    )
    assert out["ok"] is True
    assert out["calibration"]["ok"] is True
    assert out["observed_stats"] == pytest.approx(observed.tolist())
    assert len(out["best_fit_stats"]) == 2
    assert len(out["residuals"]) == 2
    assert out["mae"] >= 0.0
    assert out["rmse"] >= 0.0
    assert out["max_abs_error"] <= 8.0
    assert out["within_tolerance"] is True
    assert "synthetic" in out["diagnostic"]
    assert "not a real Anshuka" in out["diagnostic"]


def test_diagnose_evac_calibration_rejects_wrong_observed_shape():
    with pytest.raises(ValueError, match="observed_stats"):
        diagnose_evac_calibration(
            [1.0, 2.0, 3.0],
            {"belief": {"min": 0.0, "max": 1.0}},
            _FIXED,
        )


def test_evac_calibration_diagnostic_gate_passes_with_boundary_text():
    ok, msg = evac_calibration_diagnostic_gate(
        true_belief=0.55,
        belief_tol=0.15,
        residual_tol=8.0,
        max_sims=220,
        n_iter=7,
        seed=42,
    )
    assert ok, msg
    assert "residual" in msg
    assert "not a real Anshuka reproduction fix" in msg
