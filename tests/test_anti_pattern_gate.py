"""Tests for AntiPatternGate — the first concrete Gate (ADR-013).

Covers: the Verdict shape, judge() agreeing with the wrapped scan(),
tier-honest rendering, and the self_test audit surface actually
discriminating (clean passes, catalogued bad caught).
"""
from __future__ import annotations

from abm_auto.codegen.anti_pattern_gate import AntiPatternGate
from abm_auto.codegen.anti_patterns import scan
from abm_auto.verification.gate import Gate, Verdict


def test_gate_satisfies_protocol() -> None:
    g = AntiPatternGate()
    # runtime_checkable Protocol — structural conformance
    assert isinstance(g, Gate)
    assert g.name == "anti_pattern"
    assert g.family == "source_code"
    assert g.tier == "verification"


def test_clean_code_passes() -> None:
    g = AntiPatternGate()
    v = g.judge({"core/model.py": "class M:\n    def setup(self):\n        pass\n"})
    assert isinstance(v, Verdict)
    assert v.passed is True
    assert v.tier == "verification"
    assert v.reasons == []
    assert v.salient_number is None  # anti-pattern is boolean, no score


def test_bad_code_fails_with_reason() -> None:
    g = AntiPatternGate()
    v = g.judge({"core/model.py": "from abm_auto.runtime import NetworkGrid\n"})
    assert v.passed is False
    assert v.tier == "verification"
    assert any("NetworkGrid" in r for r in v.reasons)
    assert v.evidence == {"issue_count": len(v.reasons)}


def test_judge_agrees_with_underlying_scan() -> None:
    """The adapter must not drift from the catalogue it wraps."""
    g = AntiPatternGate()
    for code in (
        {"core/model.py": "class M:\n    pass\n"},                       # clean
        {"core/model.py": "from abm_auto.runtime import NetworkGrid\n"}, # bad
        {"core/agent.py": "self.network = WattsStrogatzNetwork(k=6)\n"}, # bad
    ):
        scan_issues = scan(code)
        v = g.judge(code)
        assert v.passed == (not scan_issues)
        assert v.reasons == scan_issues


def test_render_is_tier_honest() -> None:
    g = AntiPatternGate()
    passed = g.judge({"core/model.py": "class M:\n    pass\n"}).render()
    # a verification Gate that passes may say "verified"
    assert "verified" in passed and "PASS" in passed
    failed = g.judge({"core/model.py": "from abm_auto.runtime import NetworkGrid\n"}).render()
    assert "FAIL" in failed


def test_self_test_passes() -> None:
    """The audit surface: the Gate still discriminates correctly."""
    assert AntiPatternGate().self_test() is True


def test_non_py_files_ignored() -> None:
    g = AntiPatternGate()
    # scan() only inspects .py; a bad pattern in a .md must not trip the gate
    v = g.judge({"README.md": "from abm_auto.runtime import NetworkGrid\n"})
    assert v.passed is True
