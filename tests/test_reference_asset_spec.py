"""Tests for ReferenceAsset + RuleTable (ADR-013 W3 harvest).

The reference-data channel harvested from the Yaman recipe tree. Pins: spec
validation (required cols, kind, dup names), JSON roundtrip, and the runtime
operator's parse / densify / combine / given / level behaviour — including
that it reproduces the hand-written task.py result on the real recipe tree.
"""
from __future__ import annotations

from abm_auto.codegen.mechanism_spec import (
    MechanismSpec,
    ReferenceAsset,
    ScenarioParam,
)
from abm_auto.runtime import RuleTable
from abm_auto.runtime._rule_table import self_test as rule_table_self_test


def _base(**overrides) -> MechanismSpec:
    kw = dict(
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=50),
            ScenarioParam(name="periods", type="int", default=150),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="one generation",
        targets=["repertoire_size"],
    )
    kw.update(overrides)
    return MechanismSpec(**kw)


def _asset(**overrides) -> ReferenceAsset:
    kw = dict(name="rules", filename="rules_tidied.csv", output_col="item",
              input_cols=["c1", "c2", "c3"], given_col="given",
              weight_col="point", label_col="name_simplified")
    kw.update(overrides)
    return ReferenceAsset(**kw)


# ── spec validation ──────────────────────────────────────────────────────


def test_no_reference_assets_is_the_common_case() -> None:
    spec = _base()
    assert spec.reference_assets == []
    assert spec.validate() == []


def test_valid_reference_asset() -> None:
    assert _base(reference_assets=[_asset()]).validate() == []


def test_output_col_required() -> None:
    assert any("output_col" in e for e in _base(reference_assets=[_asset(output_col="")]).validate())


def test_input_cols_required() -> None:
    assert any("input_cols" in e for e in _base(reference_assets=[_asset(input_cols=[])]).validate())


def test_filename_required() -> None:
    assert any("filename" in e for e in _base(reference_assets=[_asset(filename="")]).validate())


def test_unsupported_kind_rejected() -> None:
    assert any("kind" in e for e in _base(reference_assets=[_asset(kind="graphml")]).validate())


def test_bad_name_rejected() -> None:
    assert any("not a valid identifier" in e
               for e in _base(reference_assets=[_asset(name="2rules")]).validate())


def test_duplicate_asset_name_rejected() -> None:
    assert any("duplicate" in e
               for e in _base(reference_assets=[_asset(), _asset()]).validate())


def test_json_roundtrip_preserves_asset() -> None:
    spec = _base(reference_assets=[_asset(description="Totem tree")])
    back = MechanismSpec.from_json(spec.to_json())
    a = back.reference_assets[0]
    assert a.name == "rules"
    assert a.input_cols == ["c1", "c2", "c3"]
    assert a.output_col == "item"
    assert back.validate() == []


def test_none_default_roundtrips_empty() -> None:
    assert MechanismSpec.from_json(_base().to_json()).reference_assets == []


# ── runtime operator ─────────────────────────────────────────────────────


def test_runtime_self_test_passes() -> None:
    assert rule_table_self_test() is True


def test_from_rows_combine_and_given() -> None:
    rows = [
        {"a": "0", "b": "0", "out": "1", "g": "1"},
        {"a": "0", "b": "0", "out": "2", "g": "1"},
        {"a": "1", "b": "2", "out": "9", "g": "0"},
    ]
    t = RuleTable.from_rows(rows, input_cols=["a", "b"], output_col="out", given_col="g")
    assert t.n_items == 3
    assert t.combine([t.index_of(1), t.index_of(2)]) == t.index_of(9)
    assert t.combine([t.index_of(1)]) is None
    assert set(t.given_indices()) == {t.index_of(1), t.index_of(2)}


def test_reproduces_real_yaman_tree() -> None:
    """The general operator must reproduce the hand-written task.py result on
    the real OSF recipe tree — the level distribution from the paper."""
    import os
    csv_path = os.path.join(
        os.path.dirname(__file__), "..", "examples",
        "reproduce_yaman_semantic_innovation", "reference_data", "rules_tidied.csv",
    )
    if not os.path.exists(csv_path):
        import pytest
        pytest.skip("Yaman reference_data/rules_tidied.csv not present")
    t = RuleTable.from_csv(csv_path, input_cols=["c1", "c2", "c3"], output_col="item",
                           given_col="given", weight_col="point", label_col="name_simplified")
    assert t.n_items == 184
    assert len(t.given_indices()) == 6
    assert t.level_counts() == [6, 4, 2, 2, 2, 3, 3, 7, 11, 48, 96]
    axe = t.combine([t.index_of(12), t.index_of(14), t.index_of(17)])
    assert t.label_of(axe) == "axe"
