"""P5 prior-experience gate for Anshuka collaboration uptake.

The mechanism is default-off so locked reproductions keep their historical behavior.
When enabled, social information uptake requires prior experience in addition to belief.
"""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.gis._anshuka_2026 import (
    mean_outcome,
    prior_experience_collaboration_gate,
    run_scenario,
)
from abm_auto.gis._anshuka_real import RealWorld, run_scenario_real


def _base_kwargs(**overrides):
    kw = dict(
        belief=0.1,
        alarm_t=0,
        onset_steps=20,
        mobility_good_frac=0.7,
        n_agents=100,
        max_steps=150,
    )
    kw.update(overrides)
    return kw


def _evac_lift(*, prior_experience_frac):
    off = mean_outcome(
        n_iter=10,
        base_seed=0,
        **_base_kwargs(collaboration=False, prior_experience_frac=prior_experience_frac),
    )
    on = mean_outcome(
        n_iter=10,
        base_seed=0,
        **_base_kwargs(collaboration=True, prior_experience_frac=prior_experience_frac),
    )
    return on["evac"] - off["evac"]


def test_default_behavior_keeps_locked_synthetic_golden():
    r = run_scenario(
        belief=0.4,
        alarm_t=0,
        onset_steps=20,
        mobility_good_frac=0.7,
        collaboration=False,
        seed=0,
    )
    assert (r.evacuated, r.incapacitated) == (91, 9)


def test_prior_experience_gate_reduces_collaboration_lift():
    legacy_lift = _evac_lift(prior_experience_frac=None)
    gated_lift = _evac_lift(prior_experience_frac=0.0)
    assert legacy_lift >= 4.0
    assert gated_lift <= 1.0
    assert gated_lift < legacy_lift


@pytest.mark.parametrize("bad", [True, False, -0.1, 1.1])
def test_prior_experience_frac_rejects_invalid_values(bad):
    with pytest.raises(ValueError, match="prior_experience_frac"):
        run_scenario(
            belief=0.4,
            alarm_t=0,
            onset_steps=20,
            mobility_good_frac=0.7,
            collaboration=True,
            prior_experience_frac=bad,
            seed=0,
        )


def test_real_scenario_forwards_prior_experience_without_changing_default():
    elev = np.tile(np.linspace(-1.0, 7.0, 30), (30, 1))
    water = np.zeros((30, 30), dtype=int)
    water[:, 0] = 1
    world = RealWorld(
        grid_size=30,
        elev=elev,
        initial_water=water,
        homes=[(12, 8), (14, 9), (16, 10)],
        shelters=[(5, 28)],
        source="synthetic-test",
    )
    default = run_scenario_real(
        world=world,
        belief=0.4,
        alarm_t=0,
        onset_steps=20,
        mobility_good_frac=0.7,
        collaboration=True,
        seed=0,
        verify_real=False,
    )
    gated = run_scenario_real(
        world=world,
        belief=0.4,
        alarm_t=0,
        onset_steps=20,
        mobility_good_frac=0.7,
        collaboration=True,
        prior_experience_frac=0.0,
        seed=0,
        verify_real=False,
    )
    assert default.evacuated + default.incapacitated + default.still_moving == 100
    assert gated.evacuated + gated.incapacitated + gated.still_moving == 100


def test_prior_experience_collaboration_gate_passes_with_boundary_text():
    ok, msg = prior_experience_collaboration_gate()
    assert ok, msg
    assert "prior-experience" in msg
    assert "not a real Anshuka reproduction fix" in msg
