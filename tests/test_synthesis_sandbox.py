"""Tests for sandboxed candidate verification (ADR-015 option B).

Real subprocesses: a correct candidate PASSES, a buggy one FAILS, a hanging one
is killed by the timeout, code with no `build` fails, and an unaudited paradigm
is never trusted. Then the sandboxed search internalizes only a candidate that
passes the AUDITED oracle in the isolated process.
"""
from __future__ import annotations

from abm_auto.codegen.coverage_gate import Mechanism
from abm_auto.codegen.synthesis_phase import SynthesisPhase, verify_in_subprocess

_GOOD_Q = """
class Q:
    def __init__(self, ns, na):
        self.Q = [[0.0] * na for _ in range(ns)]
    def update(self, s, a, r, s2):
        self.Q[s][a] += 0.5 * (r + 0.9 * max(self.Q[s2]) - self.Q[s][a])
    def best_action(self, s):
        return max(range(len(self.Q[s])), key=lambda a: self.Q[s][a])
def build(ns, na):
    return Q(ns, na)
"""

_BUGGY_Q = """
class Q:
    def __init__(self, ns, na): pass
    def update(self, s, a, r, s2): pass
    def best_action(self, s): return 0
def build(ns, na):
    return Q(ns, na)
"""

_HANG = "def build(ns, na):\n    while True:\n        pass\n"
_NO_BUILD = "answer = 42\n"

_RL = Mechanism("policy", "reinforcement_learning")


# ── verify_in_subprocess ─────────────────────────────────────────────────────


def test_correct_candidate_passes_in_sandbox() -> None:
    assert verify_in_subprocess(_GOOD_Q, "tabular_q_learning", timeout=20) is True


def test_buggy_candidate_fails_in_sandbox() -> None:
    assert verify_in_subprocess(_BUGGY_Q, "tabular_q_learning", timeout=20) is False


def test_hanging_candidate_is_killed_by_timeout() -> None:
    assert verify_in_subprocess(_HANG, "tabular_q_learning", timeout=2) is False


def test_code_without_build_fails() -> None:
    assert verify_in_subprocess(_NO_BUILD, "tabular_q_learning", timeout=20) is False


def test_unaudited_paradigm_never_passes() -> None:
    assert verify_in_subprocess(_GOOD_Q, "adversarial_fidelity", timeout=20) is False


# ── the sandboxed search ─────────────────────────────────────────────────────


def test_sandboxed_search_internalizes_correct_code() -> None:
    s = SynthesisPhase()
    r = s.synthesize_sandboxed(_RL, oracle_paradigm="tabular_q_learning",
                               draft_code=lambda fb: _GOOD_Q, timeout=20)
    assert r.outcome == "internalized" and s.covers(_RL)


def test_sandboxed_search_rejects_buggy_code() -> None:
    s = SynthesisPhase()
    r = s.synthesize_sandboxed(_RL, oracle_paradigm="tabular_q_learning",
                               draft_code=lambda fb: _BUGGY_Q, max_tries=2, timeout=20)
    assert r.outcome == "rejected" and not s.covers(_RL)


def test_sandboxed_search_succeeds_on_retry() -> None:
    calls = {"n": 0}

    def draft_code(feedback):
        calls["n"] += 1
        return _BUGGY_Q if calls["n"] == 1 else _GOOD_Q

    s = SynthesisPhase()
    r = s.synthesize_sandboxed(_RL, oracle_paradigm="tabular_q_learning",
                               draft_code=draft_code, max_tries=4, timeout=20)
    assert r.outcome == "internalized" and calls["n"] == 2


def test_sandboxed_search_without_audited_oracle_is_proposed() -> None:
    s = SynthesisPhase()
    gan = Mechanism("gan", "generative_model")
    r = s.synthesize_sandboxed(gan, oracle_paradigm="adversarial_fidelity",
                               draft_code=lambda fb: _GOOD_Q)
    assert r.outcome == "proposed" and not s.covers(gan)


# ── the LLM drafter's deterministic parsing (the LLM call itself is the seam) ──


def test_extract_python_fenced_block() -> None:
    from abm_auto.agents.coverage_synthesizer import extract_python
    assert extract_python("here:\n```python\ndef build():\n    return 1\n```\nok") \
        == "def build():\n    return 1"


def test_extract_python_unfenced_with_build() -> None:
    from abm_auto.agents.coverage_synthesizer import extract_python
    assert "def build" in extract_python("def build(ns, na):\n    return None")


def test_extract_python_empty_on_prose() -> None:
    from abm_auto.agents.coverage_synthesizer import extract_python
    assert extract_python("I cannot help with that.") == ""
