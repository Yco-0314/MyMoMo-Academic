"""Tests for the Coverage Gate LLM-extraction half (ADR-014 1b).

The LLM call is evidence; the deterministic parts (parse, validate, recall
floor, merge) are what's pinned here — no LLM. Plus the integration property
that matters most: an LLM record that tries to FLATTEN (claims supervised but
shows a reward marker) is still rejected by the gate.
"""
from __future__ import annotations

from abm_auto.agents.coverage_extractor import (
    _parse_json_list,
    _to_mechanism,
    records_to_mechanisms,
)
from abm_auto.codegen.coverage_gate import (
    CoverageGate,
    Mechanism,
    classify,
    merge_mechanisms,
    recall_floor,
)


# ── JSON parsing ───────────────────────────────────────────────────────────


def test_parse_fenced_json_block() -> None:
    text = 'prose\n```json\n[{"name":"m","capability":"ordinary_logic"}]\n```\ntail'
    assert _parse_json_list(text) == [{"name": "m", "capability": "ordinary_logic"}]


def test_parse_bare_list() -> None:
    assert _parse_json_list('[{"capability":"ordinary_logic"}]') == [{"capability": "ordinary_logic"}]


def test_parse_garbage_is_empty() -> None:
    assert _parse_json_list("no json here") == []
    assert _parse_json_list("") == []
    assert _parse_json_list("```json\nnot json\n```") == []


# ── record validation ──────────────────────────────────────────────────────


def test_unknown_capability_is_dropped() -> None:
    assert _to_mechanism({"capability": "quantum_magic"}, 0) is None


def test_learned_predictor_gets_contract_triple() -> None:
    m = _to_mechanism({"name": "sm", "capability": "learned_predictor",
                       "training_signal": "supervised_pairs"}, 0)
    assert (m.input_kind, m.output_kind, m.training_signal) == (
        "single_item", "item_distribution", "supervised_pairs")
    assert classify(m)[0] == "operator"          # matches FeedforwardLearner


def test_learned_predictor_without_signal_defaults_supervised() -> None:
    """The Yaman false-halt regression: the LLM omits training_signal for a
    plain learner. It must default to supervised_pairs → operator-covered, not
    false-halt every FeedforwardLearner model."""
    m = _to_mechanism({"name": "semantic_model", "capability": "learned_predictor"}, 0)
    assert m.training_signal == "supervised_pairs"
    assert classify(m)[0] == "operator"


def test_reward_marker_still_overrides_omitted_signal() -> None:
    """Defaulting to supervised must NOT launder an RL learner: a reward marker
    CORROBORATED by the prose still forces reward_td via the gate backstop →
    not operator-covered."""
    m = _to_mechanism({"name": "policy", "capability": "learned_predictor",
                       "markers": ["reward"]}, 0,
                      "the policy is trained from reward via reinforcement learning")
    assert "reward" in m.markers                       # corroborated → kept
    assert classify(m)[0] != "operator"


def test_uncorroborated_marker_is_dropped() -> None:
    """A marker the prose does NOT support (the LLM hallucinating
    'encoder_decoder' on a plain 1-hidden-layer net) is dropped, so it cannot
    false-halt a covered operator. This is the Yaman false-halt fix."""
    m = _to_mechanism({"name": "semantic_model", "capability": "learned_predictor",
                       "markers": ["encoder_decoder"]}, 0,
                      "a feedforward neural network with one hidden layer")
    assert m.markers == frozenset()                    # hallucinated marker dropped
    assert classify(m)[0] == "operator"


def test_bad_std_and_signal_are_sanitised() -> None:
    m = _to_mechanism({"capability": "bayesian_filter", "training_signal": "telepathy",
                       "std_algorithm": "made_up"}, 0)
    assert m.training_signal is None and m.std_algorithm is None


def test_records_to_mechanisms_drops_invalid_keeps_valid() -> None:
    recs = [{"capability": "ordinary_logic"}, {"capability": "nope"},
            {"capability": "generative_model", "markers": ["adversarial"]}]
    mechs = records_to_mechanisms(recs)
    assert [m.capability for m in mechs] == ["ordinary_logic", "generative_model"]


# ── recall floor + merge ───────────────────────────────────────────────────


def test_recall_floor_catches_gan() -> None:
    floor = recall_floor("the model trains a GAN with a discriminator network")
    assert [m.capability for m in floor] == ["generative_model"]


def test_recall_floor_silent_on_ordinary() -> None:
    assert recall_floor("agents move to a random empty cell each tick") == []


def test_merge_adds_floor_only_when_capability_absent() -> None:
    primary = [Mechanism("x", "ordinary_logic")]
    floor = [Mechanism("floor:generative_model", "generative_model",
                       markers=frozenset({"adversarial"}))]
    merged = merge_mechanisms(primary, floor)
    assert len(merged) == 2
    # if the primary already has the capability, the floor is not double-added
    primary2 = [Mechanism("gan", "generative_model", markers=frozenset({"adversarial"}))]
    assert len(merge_mechanisms(primary2, floor)) == 1


# ── the integration property: an LLM that tries to flatten is still caught ──


def test_llm_record_flattening_rl_is_rejected_by_the_gate() -> None:
    """The LLM claims a reward-driven learner is 'supervised_pairs', but emits an
    honest reward marker. The gate's deterministic backstop overrides the label
    → NOT operator-covered. Evidence cannot launder a verdict."""
    rec = {"name": "policy", "capability": "learned_predictor",
           "training_signal": "supervised_pairs", "markers": ["reward"]}
    m = _to_mechanism(rec, 0, "the agent learns a policy from reward (q-learning)")
    assert classify(m)[0] != "operator"
    assert not CoverageGate().check([m]).passed


def test_gan_record_from_llm_halts() -> None:
    rec = {"name": "gen", "capability": "generative_model",
           "markers": ["adversarial", "multi_network"]}
    m = _to_mechanism(rec, 0)
    assert not CoverageGate().check([m]).passed
