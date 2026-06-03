"""Tests for the Synthesis Phase deterministic plumbing (ADR-015).

Pins the trust law with NO LLM: an operator is internalized only when an
INDEPENDENT library oracle passes the candidate; buggy synthesis is rejected;
a generator cannot supply its own oracle (self-certification is structural).
"""
from __future__ import annotations

from abm_auto.codegen.coverage_gate import Mechanism
from abm_auto.codegen.synthesis_phase import SynthesisPhase, self_test


def _good(x):
    return 2 * x + 1


def _buggy(x):
    return x


def test_self_test_passes() -> None:
    assert self_test() is True


def test_correct_candidate_is_internalized_and_covers() -> None:
    gap = Mechanism("belief", "bayesian_filter")
    s = SynthesisPhase()
    r = s.attempt(gap, _good, oracle_paradigm="affine_recovery")
    assert r.outcome == "internalized"
    assert s.covers(gap)               # re-gate now operator-covered


def test_buggy_synthesis_is_rejected_by_the_oracle() -> None:
    """Load-bearing: the independent oracle actually gates — a wrong operator
    cannot be internalized on the generator's word."""
    gap = Mechanism("belief", "bayesian_filter")
    s = SynthesisPhase()
    r = s.attempt(gap, _buggy, oracle_paradigm="affine_recovery")
    assert r.outcome == "rejected"
    assert not s.covers(gap)           # NOT internalized


def test_unverifiable_gap_is_proposed_not_internalized() -> None:
    s = SynthesisPhase()
    gan = Mechanism("gan", "generative_model")
    r = s.attempt(gan, _good, oracle_paradigm="adversarial_fidelity")
    assert r.outcome == "proposed"
    assert not s.covers(gan)


def test_self_certification_is_structurally_impossible() -> None:
    """Load-bearing: a correct candidate naming its OWN unaudited paradigm is
    still only proposed — there is no API slot for a caller-supplied oracle, so
    a generator cannot certify itself."""
    gap = Mechanism("belief", "bayesian_filter")
    s = SynthesisPhase()
    r = s.attempt(gap, _good, oracle_paradigm="my_own_oracle")
    assert r.outcome == "proposed"
    assert not s.covers(gap)


def test_attempt_has_no_caller_oracle_parameter() -> None:
    """The trust law, enforced by the signature: `attempt` accepts an oracle
    paradigm NAME, never an oracle callable from the caller."""
    import inspect

    params = inspect.signature(SynthesisPhase.attempt).parameters
    assert "oracle_paradigm" in params
    assert not any("oracle" in p and p != "oracle_paradigm" for p in params)
