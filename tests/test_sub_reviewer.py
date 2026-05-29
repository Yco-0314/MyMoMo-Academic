"""Unit tests for abm_auto.review.sub_reviewer — SubReviewer adapters + run_panel."""
from __future__ import annotations

import pytest

from abm_auto.review.sub_reviewer import (
    REVIEWERS,
    SubReviewer,
    _fill_template,
    run_panel,
)


# ── _fill_template ──────────────────────────────────────────────────────


def test_fill_template_replaces_needed_placeholders() -> None:
    template = "Story: {{ story }}\nDesign: {{ design }}\nReport: {{ report }}"
    materials = {"story": "S1", "design": "D1", "report": "R1"}
    out = _fill_template(template, materials, ["story", "design", "report"])
    assert "S1" in out and "D1" in out and "R1" in out
    assert "{{ story }}" not in out


def test_fill_template_uses_placeholder_for_missing_material() -> None:
    template = "Story: {{ story }}\nMissing: {{ never_set }}"
    materials = {"story": "S1"}
    out = _fill_template(template, materials, ["story", "never_set"])
    assert "（未提供）" in out


def test_fill_template_ignores_keys_not_in_needed() -> None:
    """Even if `materials` has extra keys, only `needed` keys are filled."""
    template = "Story: {{ story }}\nOther: {{ other }}"
    materials = {"story": "S1", "other": "O1"}
    out = _fill_template(template, materials, ["story"])
    # `other` placeholder remains unfilled (not in `needed`)
    assert "{{ other }}" in out


# ── SubReviewer.run ─────────────────────────────────────────────────────


class _FakeLLM:
    """Capture last (system, user, max_tokens) tuple."""

    def __init__(self, response: str = "MOCK REVIEW"):
        self.response = response
        self.last_call: dict | None = None

    def __call__(self, system: str, user: str, max_tokens: int = 0) -> str:
        self.last_call = {"system": system, "user": user, "max_tokens": max_tokens}
        return self.response


def _fake_loader(_name: str) -> str:
    return "TEMPLATE: {{ story }} / {{ design }}"


def test_sub_reviewer_fills_template_and_calls_llm() -> None:
    sub = SubReviewer(
        id="R1",
        name="Theory",
        prompt_name="review_theory",
        system="SYS",
        materials_needed=["story", "design"],
    )
    llm = _FakeLLM(response="R1 review text")
    out = sub.run(
        materials={"story": "S", "design": "D"},
        mode_block="",
        llm_caller=llm,
        prompt_loader=_fake_loader,
    )
    assert out == "R1 review text"
    assert "S" in llm.last_call["user"]
    assert "D" in llm.last_call["user"]
    assert llm.last_call["system"] == "SYS"


def test_mode_aware_reviewer_prepends_mode_block() -> None:
    sub = SubReviewer(
        id="R1", name="X", prompt_name="t", system="S",
        materials_needed=["story"], mode_aware=True,
    )
    llm = _FakeLLM()
    sub.run(
        materials={"story": "S"},
        mode_block="## Mode preamble — reproduce",
        llm_caller=llm,
        prompt_loader=_fake_loader,
    )
    assert "Mode preamble" in llm.last_call["user"]
    # Preamble comes BEFORE the template body
    assert llm.last_call["user"].index("Mode preamble") < llm.last_call["user"].index("TEMPLATE:")


def test_mode_neutral_reviewer_ignores_mode_block() -> None:
    """R2-style reviewer (mode_aware=False) does NOT receive the preamble."""
    sub = SubReviewer(
        id="R2", name="Method", prompt_name="t", system="S",
        materials_needed=["story"], mode_aware=False,
    )
    llm = _FakeLLM()
    sub.run(
        materials={"story": "S"},
        mode_block="## Mode preamble — reproduce",
        llm_caller=llm,
        prompt_loader=_fake_loader,
    )
    assert "Mode preamble" not in llm.last_call["user"]


def test_empty_mode_block_does_not_add_separator() -> None:
    """No mode preamble → no leading separator."""
    sub = SubReviewer(
        id="R1", name="X", prompt_name="t", system="S",
        materials_needed=["story"], mode_aware=True,
    )
    llm = _FakeLLM()
    sub.run(
        materials={"story": "S"},
        mode_block="",
        llm_caller=llm,
        prompt_loader=_fake_loader,
    )
    assert llm.last_call["user"].startswith("TEMPLATE:")


def test_audit_history_appended_when_non_empty() -> None:
    sub = SubReviewer(
        id="R1", name="X", prompt_name="t", system="S",
        materials_needed=["story"],
    )
    llm = _FakeLLM()
    sub.run(
        materials={"story": "S"},
        mode_block="",
        llm_caller=llm,
        prompt_loader=_fake_loader,
        audit_history="ISSUE-001 HIGH open ...",
    )
    assert "审计历史" in llm.last_call["user"]
    assert "ISSUE-001" in llm.last_call["user"]


def test_audit_history_skipped_when_marker_present() -> None:
    """The '（审计记录为空' marker means there's nothing real to append."""
    sub = SubReviewer(
        id="R1", name="X", prompt_name="t", system="S",
        materials_needed=["story"],
    )
    llm = _FakeLLM()
    sub.run(
        materials={"story": "S"},
        mode_block="",
        llm_caller=llm,
        prompt_loader=_fake_loader,
        audit_history="（审计记录为空 — pipeline 未启用 AuditLedger）",
    )
    assert "审计历史" not in llm.last_call["user"]


# ── REVIEWERS catalog ───────────────────────────────────────────────────


def test_default_panel_has_four_reviewers() -> None:
    assert len(REVIEWERS) == 4
    ids = {sub.id for sub in REVIEWERS}
    assert ids == {"R1", "R2", "R3", "R4"}


def test_r2_is_mode_neutral() -> None:
    """R2 (methodology audit) is the only mode-neutral reviewer by convention."""
    by_id = {sub.id: sub for sub in REVIEWERS}
    assert by_id["R2"].mode_aware is False
    for rid in ("R1", "R3", "R4"):
        assert by_id[rid].mode_aware is True


def test_every_reviewer_has_a_prompt_name() -> None:
    for sub in REVIEWERS:
        assert sub.prompt_name
        assert sub.system
        assert sub.materials_needed


# ── run_panel orchestrator ──────────────────────────────────────────────


def test_run_panel_returns_dict_per_reviewer() -> None:
    llm = _FakeLLM(response="OK")
    materials = {k: "X" for k in ["story", "design", "odd", "report",
                                   "sensitivity", "memory", "params_history",
                                   "results", "trajectory"]}
    out = run_panel(
        materials=materials,
        mode_block="",
        llm_caller=llm,
        prompt_loader=_fake_loader,
    )
    assert set(out.keys()) == {"R1", "R2", "R3", "R4"}
    assert all(v == "OK" for v in out.values())


def test_run_panel_skips_when_should_run_false() -> None:
    """A subclass with should_run=False is omitted from the output."""

    class _AlwaysSkip(SubReviewer):
        def should_run(self, materials, mode_block=""):
            return False

    skip = _AlwaysSkip(id="R0", name="Skip", prompt_name="t", system="S", materials_needed=[])
    llm = _FakeLLM(response="OK")
    out = run_panel(
        materials={},
        mode_block="",
        llm_caller=llm,
        prompt_loader=_fake_loader,
        reviewers=[skip],
    )
    assert out == {}
