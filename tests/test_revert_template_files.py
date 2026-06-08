"""Tests for _revert_template_files — template-ownership restoration (F1).

The Hawk-Dove e2e re-run caught the GVR Sanity_fix editing the DO-NOT-EDIT
model.py with no re-restore. _revert_template_files now self-gates on spec
validity, returns the revert count, and is called after every fix. These pin
its contract: restore the 5 template files, leave LLM-owned files alone, and
no-op on a missing OR invalid-but-parseable spec (so an LLM-owned model.py is
never clobbered).
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from abm_auto.codegen.mechanism_spec import AgentStateVar, MechanismSpec, ScenarioParam
from abm_auto.codegen.template_generator import generate_all
from abm_auto.pipeline.phases.codegen import _revert_template_files


def _valid_spec() -> MechanismSpec:
    return MechanismSpec(
        topology=None,
        scenario_params=[
            ScenarioParam(name="agent_num", type="int", default=100),
            ScenarioParam(name="periods", type="int", default=200),
        ],
        n_agents_param="agent_num",
        periods_param="periods",
        env_step_pseudocode="agents act",
        targets=["count"],
        agent_state_vars=[AgentStateVar(name="state", type="int", init="0")],
    )


def _ctx(tmp_path):
    model_dir = tmp_path / "model"
    (model_dir / "core").mkdir(parents=True)
    ctx = SimpleNamespace(workspace=SimpleNamespace(path=tmp_path, model_dir=model_dir))
    return ctx, model_dir


def test_restores_mangled_template_file_and_keeps_llm_files(tmp_path) -> None:
    ctx, model_dir = _ctx(tmp_path)
    (tmp_path / "mechanism_spec.json").write_text(_valid_spec().to_json())
    # the LLM (Verifier fix) mangled the template-owned model.py; env.py is
    # LLM-owned and must survive the restore.
    (model_dir / "core" / "model.py").write_text("# MANGLED BY VERIFIER\n")
    (model_dir / "core" / "environment.py").write_text("# LLM env body — keep me\n")

    reverted = _revert_template_files(ctx, editor="test")

    assert reverted >= 1
    assert "template_generator. DO NOT EDIT" in (model_dir / "core" / "model.py").read_text()
    assert (model_dir / "core" / "environment.py").read_text() == "# LLM env body — keep me\n"


def test_noop_when_already_canonical(tmp_path) -> None:
    ctx, model_dir = _ctx(tmp_path)
    spec = _valid_spec()
    (tmp_path / "mechanism_spec.json").write_text(spec.to_json())
    for rel, content in generate_all(spec).items():
        target = model_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    assert _revert_template_files(ctx, editor="test") == 0


def test_noop_on_missing_spec(tmp_path) -> None:
    ctx, _ = _ctx(tmp_path)
    assert _revert_template_files(ctx, editor="test") == 0


def test_noop_on_invalid_spec_keeps_llm_model(tmp_path) -> None:
    """Invalid-but-parseable spec → templates were NOT used; model.py is
    LLM-owned and must NOT be clobbered (the trap the validity self-gate closes)."""
    ctx, model_dir = _ctx(tmp_path)
    d = _valid_spec().to_dict()
    d["scenario_params"][0]["name"] = "1nope"   # not an identifier → validate() fails
    (tmp_path / "mechanism_spec.json").write_text(json.dumps(d))
    (model_dir / "core" / "model.py").write_text("# LLM-OWNED model — keep\n")

    assert _revert_template_files(ctx, editor="test") == 0
    assert (model_dir / "core" / "model.py").read_text() == "# LLM-OWNED model — keep\n"
