"""Tests for the real oracle library + the bounded synthesis search (ADR-015).

The oracles (tabular-Q / Kalman / LP) each PASS a reference-correct candidate and
REJECT a buggy one. The bounded search internalizes only a candidate that passes
the INDEPENDENT library oracle — correct → internalize, buggy → reject after the
budget, and a retry succeeds when a later draft is correct. No LLM; the draft is
hand-written so the loop is provable.
"""
from __future__ import annotations

from abm_auto.codegen import synthesis_oracles as so
from abm_auto.codegen.coverage_gate import Mechanism
from abm_auto.codegen.synthesis_phase import SynthesisPhase


# ── the oracle library ───────────────────────────────────────────────────────


def test_oracle_self_test_passes() -> None:
    assert so.self_test() is True


def test_tabular_q_oracle_discriminates() -> None:
    assert so.oracle_tabular_q(lambda ns, na: so._RefQ(ns, na)) is True
    assert so.oracle_tabular_q(so._BuggyQ) is False


def test_kalman_oracle_discriminates() -> None:
    assert so.oracle_kalman(so._RefKalman) is True
    assert so.oracle_kalman(so._BuggyKalman) is False


def test_linear_program_oracle_discriminates() -> None:
    assert so.oracle_linear_program(so._ref_lp) is True
    assert so.oracle_linear_program(so._buggy_lp) is False


def test_real_oracles_registered_in_library() -> None:
    s = SynthesisPhase()
    for paradigm in ("tabular_q_learning", "kalman_filter", "linear_program"):
        assert paradigm in s.oracles


# ── the bounded search ───────────────────────────────────────────────────────

_RL = Mechanism("policy", "reinforcement_learning")


def test_search_internalizes_a_correct_candidate() -> None:
    s = SynthesisPhase()
    r = s.synthesize(_RL, oracle_paradigm="tabular_q_learning",
                     draft=lambda fb: (lambda ns, na: so._RefQ(ns, na)))
    assert r.outcome == "internalized"
    assert s.covers(_RL)


def test_search_rejects_a_buggy_candidate_after_budget() -> None:
    s = SynthesisPhase()
    r = s.synthesize(_RL, oracle_paradigm="tabular_q_learning",
                     draft=lambda fb: so._BuggyQ, max_tries=3)
    assert r.outcome == "rejected"
    assert not s.covers(_RL)


def test_search_succeeds_on_a_later_try() -> None:
    """A buggy first draft, a correct second — the oracle prunes the first, the
    search keeps going, the second is internalized (the DataMaster explore loop
    with our independent oracle as the pruning signal)."""
    calls = {"n": 0}

    def draft(feedback):
        calls["n"] += 1
        if calls["n"] == 1:
            assert feedback is None
            return so._BuggyQ
        assert feedback is not None             # failure fed back on retry
        return lambda ns, na: so._RefQ(ns, na)

    s = SynthesisPhase()
    r = s.synthesize(_RL, oracle_paradigm="tabular_q_learning", draft=draft, max_tries=4)
    assert r.outcome == "internalized" and calls["n"] == 2
    assert s.covers(_RL)


def test_search_without_audited_oracle_is_proposed() -> None:
    s = SynthesisPhase()
    gan = Mechanism("gan", "generative_model")
    r = s.synthesize(gan, oracle_paradigm="adversarial_fidelity",
                     draft=lambda fb: (lambda: None))
    assert r.outcome == "proposed"
    assert not s.covers(gan)
