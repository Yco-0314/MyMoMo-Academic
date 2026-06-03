"""Integration test for the W3 Layer-2 asset copy (ADR-013).

The codegen phase must copy a declared ReferenceAsset's data file from the
workspace assets dir into the generated model's data/input/, so the generated
model's RuleTable.from_csv can load it. A declared-but-missing asset must fail
fast with a clear error.
"""
from __future__ import annotations

import types

import pytest

from abm_auto.codegen.mechanism_spec import (
    MechanismSpec,
    ReferenceAsset,
    ScenarioParam,
)
from abm_auto.pipeline.phases.codegen import _copy_reference_assets
from abm_auto.runner.workspace import Workspace
from abm_auto.runtime import RuleTable

_CSV = "c1,c2,item,given,point\n0,0,1,1,0\n0,0,2,1,0\n1,2,9,0,5\n"


def _spec() -> MechanismSpec:
    return MechanismSpec(
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=10),
            ScenarioParam(name="periods", type="int", default=5),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="step",
        targets=["x"],
        reference_assets=[ReferenceAsset(
            name="rules", filename="rules.csv", output_col="item",
            input_cols=["c1", "c2"], given_col="given", weight_col="point")],
    )


def test_asset_copied_from_assets_dir(tmp_path) -> None:
    ws = Workspace(tmp_path)
    ws.assets_dir.mkdir(parents=True, exist_ok=True)
    (ws.assets_dir / "rules.csv").write_text(_CSV)

    _copy_reference_assets(types.SimpleNamespace(workspace=ws), _spec())

    dest = ws.model_dir / "data" / "input" / "rules.csv"
    assert dest.exists()
    # and the generated model would load it correctly
    t = RuleTable.from_csv(str(dest), input_cols=["c1", "c2"], output_col="item",
                           given_col="given", weight_col="point")
    assert t.combine([t.index_of(1), t.index_of(2)]) == t.index_of(9)


def test_asset_copied_from_workspace_root_fallback(tmp_path) -> None:
    ws = Workspace(tmp_path)
    (ws.path / "rules.csv").write_text(_CSV)   # dropped next to STORY.md, not in assets/

    _copy_reference_assets(types.SimpleNamespace(workspace=ws), _spec())

    assert (ws.model_dir / "data" / "input" / "rules.csv").exists()


def test_missing_asset_fails_fast(tmp_path) -> None:
    ws = Workspace(tmp_path)   # no file anywhere
    with pytest.raises(FileNotFoundError, match="rules.csv"):
        _copy_reference_assets(types.SimpleNamespace(workspace=ws), _spec())


def test_no_assets_is_a_noop(tmp_path) -> None:
    ws = Workspace(tmp_path)
    spec = MechanismSpec(
        scenario_params=[ScenarioParam(name="agent_num", type="int", default=10),
                         ScenarioParam(name="periods", type="int", default=5)],
        n_agents_param="agent_num", periods_param="periods",
        env_step_pseudocode="step", targets=["x"],
    )
    _copy_reference_assets(types.SimpleNamespace(workspace=ws), spec)   # must not raise
    assert not (ws.model_dir / "data" / "input").exists()
