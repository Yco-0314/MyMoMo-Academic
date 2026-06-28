"""Real-DEM P5 prior-experience calibration diagnostics."""
from __future__ import annotations

from pathlib import Path

import pytest

from abm_auto.gis import _anshuka_p5_calibration as p5


def test_calibration_selects_least_restrictive_passing_prior(monkeypatch):
    scores = {
        None: 7.5,
        0.0: 0.0,
        0.25: 1.9,
        0.5: 2.8,
        0.75: 6.8,
        1.0: 7.7,
    }

    def fake_eval(world, *, prior_experience_frac, **kwargs):
        return {
            "prior_experience_frac": prior_experience_frac,
            "max_abs_delta_evac": scores[prior_experience_frac],
            "beliefs": {},
        }

    monkeypatch.setattr(p5, "evaluate_p5_collaboration_deltas", fake_eval)
    out = p5.calibrate_p5_prior_experience(object(), target_abs_delta=5.0)
    assert out["baseline"]["max_abs_delta_evac"] == pytest.approx(7.5)
    assert out["best"]["prior_experience_frac"] == 0.5
    assert out["best"]["max_abs_delta_evac"] == pytest.approx(2.8)
    assert out["meets_target"] is True


def test_p5_real_dem_gate_fails_without_synthetic_fallback(tmp_path):
    ok, msg = p5.p5_prior_experience_real_dem_gate(dem_path=tmp_path / "missing.tif")
    assert ok is False
    assert "DEM not found" in msg
    assert "no synthetic fallback" in msg


@pytest.mark.skipif(
    not Path("data/anshuka_ba/ba_dem_utm.tif").exists(),
    reason="local Ba DEM artifact is not present",
)
def test_p5_real_dem_gate_passes_on_local_ba_dem():
    ok, msg = p5.p5_prior_experience_real_dem_gate(
        dem_path="data/anshuka_ba/ba_dem_utm.tif",
        grid_size=100,
        n_iter=10,
        target_abs_delta=5.0,
    )
    assert ok, msg
    assert "real-DEM P5" in msg
    assert "best_prior=0.5" in msg
    assert "not a verdict rewrite" in msg
