"""Tests the closed self-extension loop (ADR-015 wired into ADR-014).

Part 1: the gate's classify/check consult the synthesis `internalized` registry,
so an autonomously-synthesized operator counts as covered on re-gate.
Part 2: the CoverageGatePhase, with synthesis enabled, PROMOTES a verifiable
(stdlib-tier) mechanism to an operator via a (here hand-written) drafter +
sandbox verification, and the re-check then sees it as tier-1 covered.
"""
from __future__ import annotations

from abm_auto.codegen.coverage_gate import CoverageGate, Mechanism, classify
from abm_auto.codegen.synthesis_phase import SynthesisPhase
from abm_auto.pipeline.phases.coverage import CoverageGatePhase

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


# ── Part 1: re-gate consults the internalized registry ───────────────────────


def test_internalized_capability_classifies_as_operator() -> None:
    m = Mechanism("policy", "reinforcement_learning")        # normally uncovered
    assert classify(m)[0] == "uncovered"
    internalized = {"reinforcement_learning": "Synthesized_reinforcement_learning"}
    assert classify(m, internalized) == ("operator", "Synthesized_reinforcement_learning")


def test_check_passes_once_capability_is_internalized() -> None:
    m = Mechanism("policy", "reinforcement_learning")
    assert not CoverageGate().check([m]).passed
    assert CoverageGate().check([m], internalized={"reinforcement_learning": "Syn"}).passed


# ── Part 2: the phase promotes a verifiable mechanism (closed loop) ───────────


class _StubDrafter:
    """Stands in for the LLM OperatorSynthesizer — returns known-good code so the
    loop is provable without an LLM (the sandbox verification is real)."""
    def draft_code(self, mechanism, oracle_paradigm, feedback=None):
        return _GOOD_Q


def test_phase_promotes_verifiable_mechanism_to_operator() -> None:
    # a stdlib-tier mechanism: RL tagged with the tabular-Q oracle paradigm
    m = Mechanism("q", "reinforcement_learning", markers=frozenset({"reward"}),
                  std_algorithm="tabular_q_learning")
    assert classify(m)[0] == "stdlib"

    synthesis = SynthesisPhase()
    phase = CoverageGatePhase(synthesizer=_StubDrafter(), synthesis=synthesis,
                              enable_synthesis=True)
    phase._promote_verifiable([m], object())     # ctx unused beyond best-effort audit

    # internalized + the re-gate now sees a tier-1 operator
    assert "reinforcement_learning" in synthesis.internalized
    assert classify(m, synthesis.internalized)[0] == "operator"
    assert CoverageGate().check([m], internalized=synthesis.internalized).passed


def test_promotion_is_off_by_default() -> None:
    """enable_synthesis defaults False — no generated code runs unless opted in."""
    phase = CoverageGatePhase()
    assert phase.enable_synthesis is False
    assert phase.synthesis is None
