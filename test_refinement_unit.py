"""Unit tests for the refinement (GVR) module.

Pure-function module, so 100% testable with mock generators/validators —
no LLM calls, no I/O, no workspace dependencies.
"""
from __future__ import annotations

from abm_auto.refinement import (
    refine, ValidationOutcome, RefinementResult, _pick_best, Attempt,
    build_cumulative_feedback,
)


def test_accepts_first_attempt():
    """If validator says OK on first try, no retry happens."""
    calls = []

    def gen(feedback):
        calls.append(feedback)
        return "artifact-1"

    def val(artifact):
        return ValidationOutcome(ok=True)

    r = refine(gen, val, max_iters=3, verbose=False)
    assert r.accepted is True
    assert r.exhausted is False
    assert r.n_attempts == 1
    assert r.artifact == "artifact-1"
    assert calls == [None]   # generator called once, no feedback


def test_succeeds_on_third_attempt():
    """Validator fails twice, passes third time → accepted, 3 attempts logged."""
    iters = {"n": 0}

    def gen(feedback):
        iters["n"] += 1
        return f"artifact-{iters['n']}"

    def val(artifact):
        # Pass only on attempt 3
        return ValidationOutcome(ok=(artifact == "artifact-3"), reasons=["bad"] if artifact != "artifact-3" else [])

    r = refine(gen, val, max_iters=5, verbose=False)
    assert r.accepted is True
    assert r.n_attempts == 3
    assert r.artifact == "artifact-3"
    assert r.attempts[1].feedback_used is not None  # iter 2 got feedback from iter 1
    assert "Previous attempt was rejected" in r.attempts[1].feedback_used


def test_exhausts_and_returns_best():
    """All attempts fail → exhausted, returns the attempt with fewest reasons."""
    def gen(feedback):
        # Each attempt is a different artifact
        return f"a{(feedback or 'first')[:5]}"

    val_calls = {"n": 0}

    def val(artifact):
        val_calls["n"] += 1
        # iter 1: 3 reasons; iter 2: 1 reason (best); iter 3: 2 reasons
        if val_calls["n"] == 1:
            return ValidationOutcome(ok=False, reasons=["x", "y", "z"])
        elif val_calls["n"] == 2:
            return ValidationOutcome(ok=False, reasons=["only-one"])
        else:
            return ValidationOutcome(ok=False, reasons=["a", "b"])

    r = refine(gen, val, max_iters=3, verbose=False)
    assert r.accepted is False
    assert r.exhausted is True
    assert r.n_attempts == 3
    # Best should be iter 2 (fewest reasons)
    assert r.attempts[1].outcome.reasons == ["only-one"]
    # The returned artifact must match iter 2's
    assert r.artifact == r.attempts[1].artifact


def test_feedback_threading():
    """Validator failure text is passed as feedback to the next generator call."""
    feedbacks_received = []

    def gen(feedback):
        feedbacks_received.append(feedback)
        return "x"

    def val(artifact):
        return ValidationOutcome(ok=False, reasons=["test-reason-A", "test-reason-B"])

    refine(gen, val, max_iters=2, verbose=False)
    # First call: no feedback
    assert feedbacks_received[0] is None
    # Second call: feedback contains both reasons
    assert "test-reason-A" in feedbacks_received[1]
    assert "test-reason-B" in feedbacks_received[1]


def test_cumulative_feedback_empty():
    """build_cumulative_feedback with no failures returns empty string."""
    assert build_cumulative_feedback([]) == ""


def test_cumulative_feedback_single_attempt():
    """Single failure: fall back to to_feedback() output (no history yet)."""
    a = Attempt(
        iteration=1, artifact="x",
        outcome=ValidationOutcome(ok=False, reasons=["one reason"]),
        feedback_used=None,
    )
    out = build_cumulative_feedback([a])
    # Should match what to_feedback would produce
    assert "one reason" in out
    assert "DO NOT repeat" not in out  # only added when ≥ 2 attempts


def test_cumulative_feedback_multiple_attempts_includes_all():
    """≥ 2 failures: feedback lists each attempt and forbids repetition."""
    attempts = [
        Attempt(1, "x1", ValidationOutcome(ok=False, reasons=["KeyError: gen_num"]), None),
        Attempt(2, "x2", ValidationOutcome(ok=False, reasons=["KeyError: generation_num"]), "fb"),
    ]
    out = build_cumulative_feedback(attempts)
    assert "attempt 3" in out.lower()  # next will be iter 3
    assert "2 previous attempts" in out.lower()
    assert "gen_num" in out
    assert "generation_num" in out
    assert "DO NOT repeat" in out


def test_cumulative_feedback_truncates_long_reasons():
    """Per-attempt reason text is truncated to keep context manageable."""
    huge_reason = "x" * 5000
    attempts = [
        Attempt(1, "a", ValidationOutcome(ok=False, reasons=[huge_reason]), None),
        Attempt(2, "b", ValidationOutcome(ok=False, reasons=["second"]), "fb"),
    ]
    out = build_cumulative_feedback(attempts, max_reason_chars=300)
    # Total output should be far smaller than 5000 chars
    assert len(out) < 1500
    assert "truncated" in out  # the marker should appear


def test_refine_uses_cumulative_feedback_on_iter_3():
    """Integration: by iter 3, the generator's feedback contains BOTH prior failures."""
    feedbacks_received: list[str] = []

    def gen(fb):
        feedbacks_received.append(fb or "")
        return "x"

    val_calls = {"n": 0}

    def val(_):
        val_calls["n"] += 1
        return ValidationOutcome(ok=False, reasons=[f"failure-{val_calls['n']}"])

    refine(gen, val, max_iters=3, verbose=False)

    # iter 1: no feedback
    assert feedbacks_received[0] == ""
    # iter 2: feedback mentions failure-1 only (single-attempt mode)
    assert "failure-1" in feedbacks_received[1]
    # iter 3: feedback mentions BOTH failure-1 AND failure-2 + DO NOT repeat
    assert "failure-1" in feedbacks_received[2]
    assert "failure-2" in feedbacks_received[2]
    assert "DO NOT repeat" in feedbacks_received[2]


def test_audit_writes_per_iteration():
    """When audit ledger is provided, refine writes one event per attempt + one on exhaust."""
    events: list[dict] = []

    class MockAudit:
        def info(self, **kwargs):
            events.append({"type": "info", **kwargs})
        def raise_issue(self, **kwargs):
            events.append({"type": "raise", **kwargs})

    def gen(f):
        return "x"

    def val(a):
        return ValidationOutcome(ok=False, reasons=["bad"])

    refine(gen, val, max_iters=2, audit=MockAudit(), actor="TestActor", phase="Phase X", verbose=False)

    # 2 info events (one per attempt) + 1 raise on exhaust = 3 total
    assert len(events) == 3
    assert events[0]["type"] == "info"
    assert events[1]["type"] == "info"
    assert events[2]["type"] == "raise"
    assert events[2]["actor"] == "TestActor"
    assert events[2]["phase"] == "Phase X"


def test_audit_no_raise_on_success():
    """Successful refine writes info events but no raise."""
    events = []

    class MockAudit:
        def info(self, **kwargs):
            events.append({"type": "info"})
        def raise_issue(self, **kwargs):
            events.append({"type": "raise"})

    def gen(f):
        return "x"

    def val(a):
        return ValidationOutcome(ok=True)

    refine(gen, val, max_iters=3, audit=MockAudit(), verbose=False)

    # 1 info, 0 raise (accepted on iter 1)
    assert any(e["type"] == "info" for e in events)
    assert not any(e["type"] == "raise" for e in events)


def test_pick_best_minimum_reasons():
    """_pick_best picks the attempt with fewest reasons."""
    a1 = Attempt(iteration=1, artifact="a1", outcome=ValidationOutcome(ok=False, reasons=["x", "y"]), feedback_used=None)
    a2 = Attempt(iteration=2, artifact="a2", outcome=ValidationOutcome(ok=False, reasons=["x"]), feedback_used="f")
    a3 = Attempt(iteration=3, artifact="a3", outcome=ValidationOutcome(ok=False, reasons=["x", "y", "z"]), feedback_used="g")
    best = _pick_best([a1, a2, a3])
    assert best.iteration == 2  # fewest reasons


def test_pick_best_ties_break_to_later():
    """When tied on reasons, later iteration wins (refinement assumption)."""
    a1 = Attempt(iteration=1, artifact="a1", outcome=ValidationOutcome(ok=False, reasons=["x"]), feedback_used=None)
    a2 = Attempt(iteration=2, artifact="a2", outcome=ValidationOutcome(ok=False, reasons=["x"]), feedback_used="f")
    best = _pick_best([a1, a2])
    assert best.iteration == 2


def test_max_iters_zero_raises():
    """max_iters < 1 is a programmer error."""
    try:
        refine(lambda f: "x", lambda a: ValidationOutcome(ok=False), max_iters=0)
        assert False, "should have raised"
    except ValueError as e:
        assert "max_iters" in str(e)


def test_validation_outcome_to_feedback():
    """Empty reasons produces a sensible default."""
    o = ValidationOutcome(ok=False)
    fb = o.to_feedback()
    assert "rejected" in fb.lower()

    o2 = ValidationOutcome(ok=False, reasons=["first reason", "second reason"])
    fb2 = o2.to_feedback()
    assert "first reason" in fb2
    assert "second reason" in fb2


# ── Driver ──────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import inspect, sys, traceback
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    print(f"Running {len(tests)} tests...")
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
            traceback.print_exc()
    if failed:
        print(f"\n{failed} failure(s)")
        sys.exit(1)
    print(f"\nAll {len(tests)} tests passed.")
