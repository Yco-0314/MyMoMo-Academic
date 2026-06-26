"""Tests for abm_auto.agents._hypothesis — the hypothesis-design consistency seam.

Before this module the bilingual hypothesis parsing was duplicated across two
agents and the drift check was inlined in DesignAgent.run(), observable only via
the audit ledger and with zero direct coverage. These tests pin the parser and
the drift logic against example documents — no agents or workspaces mocked.
"""
from __future__ import annotations

from abm_auto.agents import _hypothesis as H


_EN = (
    "## Recommendation\nBuild H2: the density mechanism is primary.\n\n"
    "## H1: contact\nH1 body\n\n## H2: density\nH2 body about density\n\n"
    "## H3: mobility\nH3 body\n\n## Rejected\nH1 weak; H3 untestable\n"
)
_ZH = (
    "## 推荐\n构建 H3:迁移机制为主。\n\n"
    "## H1：接触\nH1正文\n\n## H2：密度\nH2正文\n\n## H3：迁移\nH3正文关于迁移\n\n"
    "## 被否决\nH1弱;H2不可测\n"
)
_REJECT_FALLBACK = (
    "## Recommendation\nThe evidence points one way.\n\n"
    "## H1: a\nbody\n## H2: b\nbody\n## H3: c\nbody\n\n"
    "## Rejected\nH1 because foo; H2 because bar\n"
)


def test_recommended_english_build():
    rec = H.recommended_hypothesis(_EN)
    assert rec.number == "2"
    assert "RECOMMENDED HYPOTHESIS: H2" in rec.text
    assert "H2 body about density" in rec.text


def test_recommended_chinese_build():
    rec = H.recommended_hypothesis(_ZH)
    assert rec.number == "3"
    assert "RECOMMENDED HYPOTHESIS: H3" in rec.text


def test_recommended_reject_fallback_infers_missing():
    # Recommendation names no H explicitly; two of three rejected -> the missing
    # one (H3) is the recommendation. This is the richer logic the drift check
    # now shares (the simple extractor returned None here).
    rec = H.recommended_hypothesis(_REJECT_FALLBACK)
    assert rec.number == "3"


def test_recommended_no_section_returns_truncated_md():
    md = "Just narrative mentioning H1 and H2, no recommendation heading.\n"
    rec = H.recommended_hypothesis(md)
    assert rec.number is None
    assert rec.text == md[:1500]


def test_used_hypothesis_bilingual_and_absent():
    assert H.used_hypothesis("## Anchor\nSelected hypothesis H3 — density.\n") == "3"
    assert H.used_hypothesis("## 锚点\n选定假设 H2。\n") == "2"
    assert H.used_hypothesis("## Anchor\n**H1：** contact\n") == "1"
    assert H.used_hypothesis("## Anchor\nReproduce mode, no hypothesis.\n") is None


def test_drift_reason():
    # Drift: design built a different H than recommended.
    reason = H.drift_reason("2", "3")
    assert reason and "recommended H2" in reason and "around H3" in reason
    # No drift: same number.
    assert H.drift_reason("3", "3") is None
    # Not drift: a missing recommendation or missing design marker is not drift.
    assert H.drift_reason(None, "3") is None
    assert H.drift_reason("3", None) is None
