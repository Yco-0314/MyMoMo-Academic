"""Tests for the declarative GIS capability parameter schema.

Each renderable capability declares its render params (name/type/default/range/
unit/doc) as data, the single source consumed by both the extractor prompt and
GISModelSpec.validate(). validate() now rejects unknown / mistyped / out-of-range
params instead of silently substituting a default (the render branches' old
behaviour).
"""
from __future__ import annotations

import pytest

from abm_auto.gis._capabilities import resolve_capability
from abm_auto.gis._extractor import _renderable_capability_table
from abm_auto.gis._model_spec import GISModelSpec


def test_capability_declares_its_params():
    cap = resolve_capability("raster", "sir")
    assert {p.name for p in cap.params} == {"steps"}
    cap2 = resolve_capability("coupled", "social_spatial_contagion")
    assert {p.name for p in cap2.params} == {"n_agents", "side", "beta", "steps"}


def test_valid_param_accepted():
    GISModelSpec(spatial_type="raster", mechanism="sir", params={"steps": 40}).validate()


def test_unknown_param_rejected():
    spec = GISModelSpec(spatial_type="raster", mechanism="sir", params={"stteps": 5})
    with pytest.raises(ValueError, match="unknown param 'stteps'"):
        spec.validate()


def test_param_valid_for_one_capability_is_rejected_for_another():
    # steps is valid for raster_sir; flood_evacuation only takes threshold.
    GISModelSpec(spatial_type="raster", mechanism="sir", params={"steps": 5}).validate()
    bad = GISModelSpec(spatial_type="network", mechanism="flood_evacuation", params={"steps": 5})
    with pytest.raises(ValueError, match="unknown param"):
        bad.validate()


def test_mistyped_param_rejected():
    spec = GISModelSpec(spatial_type="raster", mechanism="sir", params={"steps": "not-an-int"})
    with pytest.raises(ValueError, match="must be int"):
        spec.validate()


def test_out_of_range_param_rejected():
    # beta is a probability with range 0..1.
    spec = GISModelSpec(
        spatial_type="coupled", mechanism="social_spatial_contagion", params={"beta": 2.0}
    )
    with pytest.raises(ValueError, match="<= 1"):
        spec.validate()


def test_seed_in_params_accepted_everywhere():
    # seed is a spec-level field; tolerated (and ignored) if duplicated into params,
    # on a capability that declares no 'seed' param.
    GISModelSpec(
        spatial_type="network", mechanism="flood_evacuation", params={"seed": 9}
    ).validate()


def test_extractor_prompt_lists_per_capability_params():
    table = _renderable_capability_table()
    assert "params:" in table
    assert "steps(int=" in table       # types + defaults are surfaced
    assert "beta(float=" in table
