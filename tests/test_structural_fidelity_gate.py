"""Tests for StructuralFidelityGate — spec-vs-code as a Gate (ADR-013).

The structural-scan logic itself is already pinned by
tests/test_structural_fidelity.py (against its own reference `_scan`).
These tests cover the Gate wrapper: Protocol conformance, Verdict shape,
that the Gate's pure `_scan` does not drift from that reference, and the
self_test audit surface.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from abm_auto.codegen.structural_fidelity_gate import (
    StructuralFidelityGate,
    StructuralFidelityInput,
    _scan,
)
from abm_auto.verification.gate import Gate, Verdict

_ALIGNED_SPEC = {
    "scenario_params": [{"name": "beta", "default": 0.3}],
    "agent_state_vars": [{"name": "state", "type": "int"}],
    "topology": None,
}
_ALIGNED_CODE = {
    "core/scenario.py": "class S:\n    def setup(self):\n        self.beta = 0.3\n",
    "core/agent.py": "class A:\n    def setup(self):\n        self.state = 0\n",
    "core/model.py": "class M:\n    pass\n",
}


def test_gate_satisfies_protocol() -> None:
    g = StructuralFidelityGate()
    assert isinstance(g, Gate)
    assert g.name == "structural_fidelity"
    assert g.family == "spec_and_code"
    assert g.tier == "verification"


def test_aligned_passes() -> None:
    g = StructuralFidelityGate()
    v = g.judge(StructuralFidelityInput(_ALIGNED_SPEC, _ALIGNED_CODE))
    assert isinstance(v, Verdict)
    assert v.passed is True
    assert v.reasons == []


def test_missing_scenario_param_caught() -> None:
    g = StructuralFidelityGate()
    code = dict(_ALIGNED_CODE, **{"core/scenario.py": "class S:\n    pass\n"})
    v = g.judge(StructuralFidelityInput(_ALIGNED_SPEC, code))
    assert v.passed is False
    assert any("beta" in r for r in v.reasons)


def test_grid_network_contradiction_caught() -> None:
    g = StructuralFidelityGate()
    spec = {"scenario_params": [], "agent_state_vars": [],
            "topology": {"type": "watts_strogatz"}}
    code = {
        "core/agent.py": "class A(GridAgent):\n    pass\n",
        "core/model.py": "class M:\n    def setup(self):\n        self.network = self.create_network()\n",
    }
    v = g.judge(StructuralFidelityInput(spec, code))
    assert v.passed is False
    assert any("Grid/Network contradiction" in r for r in v.reasons)


def test_scan_does_not_drift_from_reference() -> None:
    """The Gate's pure _scan must agree with the reference _scan already
    pinned in tests/test_structural_fidelity.py (no logic drift)."""
    spec = importlib.util.spec_from_file_location(
        "tsf_ref", str(Path(__file__).parent / "test_structural_fidelity.py")
    )
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)

    cases = [
        ({"scenario_params": [{"name": "agent_num"}], "agent_state_vars": []},
         {"core/scenario.py": "self.agent_num_max = 100\n"}),  # word-boundary
        ({"scenario_params": [], "agent_state_vars": [{"name": "happiness"}, {"name": "state"}]},
         {"core/agent.py": "self.state = 0\n"}),
        ({"scenario_params": [], "agent_state_vars": [], "topology": {"type": "ws"}},
         {"core/agent.py": "class H(GridAgent):\n    pass\n",
          "core/model.py": "self.network.setup_agent_connections(agent_lists=[self.agents])\n"}),
        ({"scenario_params": [], "agent_state_vars": []}, {}),
    ]
    for sp, cf in cases:
        assert len(_scan(sp, cf)) == len(ref._scan(sp, cf))


def test_empty_spec_passes() -> None:
    g = StructuralFidelityGate()
    assert g.judge(StructuralFidelityInput({}, {})).passed is True


def test_self_test_passes() -> None:
    assert StructuralFidelityGate().self_test() is True
