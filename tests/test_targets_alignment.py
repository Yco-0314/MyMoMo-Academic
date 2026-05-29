"""Unit test for the targets-alignment validator + the templated-targets
prompt block in CoderAgent.

The validator + prompt block together address the 2026-05-29 dogfood
"targets desync" failure mode: Stage-2 JSON declared
`targets: [count_s, count_i, count_r]` but the LLM-written
environment.py used `susceptible/infected/resistant`. DataCollector
silently produced zero columns; sanity check fired; GVR cascaded; pipeline
exited 1.

These tests pin both halves of the fix.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def test_targets_validator_scan_catches_missing_attrs(tmp_path: Path) -> None:
    """Reproduce the dogfood bug: spec says count_s/i/r but env.py uses
    susceptible/infected/resistant. The regex scan must flag all three
    as missing.
    """
    env_src = (
        "from abm_auto.runtime import Environment\n\n"
        "class VirusEnvironment(Environment):\n"
        "    def step(self, agents, network, scenario):\n"
        "        self.susceptible = sum(1 for a in agents if a.state == 'S')\n"
        "        self.infected = sum(1 for a in agents if a.state == 'I')\n"
        "        self.resistant = sum(1 for a in agents if a.state == 'R')\n"
    )
    targets = ["count_s", "count_i", "count_r"]
    missing = []
    for target in targets:
        pattern = re.compile(rf"\bself\.{re.escape(target)}\s*[:=]")
        if not pattern.search(env_src):
            missing.append(target)
    # All three should be flagged because env.py uses the OTHER names
    assert set(missing) == set(targets)


def test_targets_validator_passes_aligned_env() -> None:
    """When env.py sets the templated targets, the scan finds them all."""
    env_src = (
        "class VirusEnvironment(Environment):\n"
        "    def step(self, agents, network, scenario):\n"
        "        self.count_s = sum(1 for a in agents if a.state == 'S')\n"
        "        self.count_i: int = sum(1 for a in agents if a.state == 'I')\n"
        "        self.count_r = sum(1 for a in agents if a.state == 'R')\n"
    )
    targets = ["count_s", "count_i", "count_r"]
    missing = [
        t for t in targets
        if not re.compile(rf"\bself\.{re.escape(t)}\s*[:=]").search(env_src)
    ]
    assert missing == []


def test_targets_validator_handles_typed_assignment() -> None:
    """`self.count_s: int = 0` should count as a valid assignment."""
    env_src = "self.count_s: int = 0\n"
    pattern = re.compile(r"\bself\.count_s\s*[:=]")
    assert pattern.search(env_src) is not None


def test_targets_validator_word_boundary_strict() -> None:
    """`self.count_solar` must NOT match when scanning for `count_s`."""
    env_src = "self.count_solar = 42\n"
    pattern = re.compile(r"\bself\.count_s\s*[:=]")
    assert pattern.search(env_src) is None


def test_templated_targets_block_renders_when_spec_present(tmp_path: Path) -> None:
    """CoderAgent._build_templated_targets_block reads mechanism_spec.json
    and renders a prompt block listing every target as required env attr.
    """
    # Minimal MechanismSpec on disk
    spec = {
        "project_name": "Test",
        "model_class_name": "TestModel",
        "agent_class_name": "Person",
        "environment_class_name": "TestEnv",
        "scenario_class_name": "TestScenario",
        "data_collector_class_name": "TestDC",
        "topology": {"type": "watts_strogatz", "params": {"k": 6, "p": 0.1}},
        "n_agents_param": "agent_num",
        "periods_param": "periods",
        "scenario_params": [
            {"name": "periods", "type": "int", "default": 100, "unit": "ticks"},
            {"name": "agent_num", "type": "int", "default": 50, "unit": "count"},
        ],
        "agent_state_vars": [{"name": "state", "type": "int", "init": "0"}],
        "targets": ["alpha", "beta_count", "gamma"],
        "env_step_pseudocode": "do stuff",
    }
    # Synthesize a workspace-like object that exposes path + read methods
    spec_path = tmp_path / "mechanism_spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    class _FakeWorkspace:
        path = tmp_path

    # Build minimal CoderAgent — only need the method, no LLM
    from abm_auto.agents.coder import CoderAgent
    agent = CoderAgent.__new__(CoderAgent)
    agent.workspace = _FakeWorkspace()

    block = agent._build_templated_targets_block()
    assert "TEMPLATED DATA COLLECTOR" in block
    assert "TestEnv.step" in block
    # All three targets must appear in the prompt block
    for target in ("alpha", "beta_count", "gamma"):
        assert f"self.{target}" in block


def test_templated_targets_block_empty_when_spec_absent(tmp_path: Path) -> None:
    """Without mechanism_spec.json (legacy codegen path), the block is empty
    so CoderAgent's prompt doesn't get spurious constraints."""
    class _FakeWorkspace:
        path = tmp_path   # no mechanism_spec.json present

    from abm_auto.agents.coder import CoderAgent
    agent = CoderAgent.__new__(CoderAgent)
    agent.workspace = _FakeWorkspace()
    assert agent._build_templated_targets_block() == ""
