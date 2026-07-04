"""CBHG grammar prototype tests: parse (incl. malformed gate), deterministic compile, and the
provenance audit (CLEAN vs CAVEATED, reusing mymomo's honesty vocabulary)."""
from __future__ import annotations

import numpy as np
import pytest

from abm_auto.cbhg import audit_rules, compile_model, parse_rule, parse_rules


def test_parse_roundtrip_with_citation():
    r = parse_rule("In tumor, oxygen increases proliferation; half-max 0.5, Hill 4, max 3.0; cite Smith2020.")
    assert r.cell_type == "tumor" and r.signal == "oxygen" and r.target == "proliferation"
    assert r.direction == "increases" and r.sign == 1
    assert (r.half_max, r.hill, r.max_response) == (0.5, 4.0, 3.0)
    assert r.citation == "Smith2020"


def test_parse_decrease_without_citation():
    r = parse_rule("In tumor, drug decreases proliferation; half-max 0.3, Hill 2, max 2.0.")
    assert r.direction == "decreases" and r.sign == -1
    assert r.citation is None


def test_malformed_rule_raises():
    with pytest.raises(ValueError):
        parse_rule("oxygen makes tumor grow a lot")


def test_parse_rules_skips_comments_and_blanks():
    text = "# a comment\n\nIn tumor, oxygen increases proliferation; half-max 0.5, Hill 4, max 3.0.\n"
    rules = parse_rules(text)
    assert len(rules) == 1


def test_compile_run_sign_and_shape():
    rules = parse_rules(
        "In tumor, oxygen increases growth; half-max 0.5, Hill 4, max 3.0; cite A.\n"
        "In tumor, drug decreases growth; half-max 0.5, Hill 4, max 3.0; cite B.\n"
    )
    model = compile_model(rules)
    n = 100
    cell_types = np.array(["tumor"] * n)
    out = model.run(cell_types, {"oxygen": np.ones(n), "drug": np.zeros(n)})
    assert set(out) == {"growth"}
    assert out["growth"].shape == (n,)
    # oxygen high (increases) + drug zero (no decrease) -> net positive growth
    assert np.all(out["growth"] > 0)


def test_compile_respects_cell_type():
    rules = parse_rules("In tumor, oxygen increases growth; half-max 0.5, Hill 4, max 3.0; cite A.")
    model = compile_model(rules)
    cell_types = np.array(["tumor", "stroma"])
    out = model.run(cell_types, {"oxygen": np.array([1.0, 1.0])})
    assert out["growth"][0] > 0      # tumor responds
    assert out["growth"][1] == 0     # stroma has no matching rule


def test_run_missing_signal_raises():
    model = compile_model(parse_rules("In tumor, oxygen increases growth; half-max 0.5, Hill 4, max 3.0."))
    with pytest.raises(KeyError):
        model.run(np.array(["tumor"]), {"drug": np.array([1.0])})


def test_audit_clean_when_all_cited():
    rules = parse_rules("In tumor, oxygen increases growth; half-max 0.5, Hill 4, max 3.0; cite Smith2020.")
    a = audit_rules(rules)
    assert a.status == "CLEAN" and a.ungrounded == []


@pytest.mark.parametrize("bad", [
    "In tumor, oxygen increases growth; half-max -0.5, Hill 4, max 3.0.",   # half-max <= 0
    "In tumor, oxygen increases growth; half-max 0.5, Hill -4, max 3.0.",   # Hill <= 0
    "In tumor, oxygen increases growth; half-max 0, Hill 4, max 3.0.",      # half-max == 0
    "In tumor, oxygen increases growth; half-max 0.5, Hill 4, max -2.0.",   # max < 0
])
def test_physically_invalid_params_raise(bad):
    # silently compiling a NaN/inf model is the worst failure for this layer; reject instead
    with pytest.raises(ValueError):
        parse_rule(bad)


def test_scientific_notation_parses():
    r = parse_rule("In tumor, oxygen increases growth; half-max 1e-3, Hill 2, max 1.5e1; cite A.")
    assert r.half_max == 1e-3 and r.max_response == 15.0


@pytest.mark.parametrize("cite", ["cite .", "cite TODO", "cite x", "cite ???"])
def test_placeholder_citation_is_not_grounded(cite):
    rules = parse_rules(f"In tumor, oxygen increases growth; half-max 0.5, Hill 4, max 3.0; {cite}.")
    a = audit_rules(rules)
    assert a.status == "CAVEATED"
    assert len(a.ungrounded) == 1


def test_audit_caveated_flags_ungrounded():
    rules = parse_rules(
        "In tumor, oxygen increases growth; half-max 0.5, Hill 4, max 3.0; cite Smith2020.\n"
        "In tumor, drug decreases growth; half-max 0.3, Hill 2, max 2.0.\n"
    )
    a = audit_rules(rules)
    assert a.status == "CAVEATED"
    assert len(a.ungrounded) == 1 and a.ungrounded[0].signal == "drug"
    assert "verified" not in a.render().lower()
