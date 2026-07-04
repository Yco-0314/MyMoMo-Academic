"""Hypothesis-design consistency — one deep module for the bilingual hypothesis
parsing and the hypothesis→design drift check.

Three pieces used to be smeared across two agents and an inline audit block:
- HypothesisAgent re-derived the recommended H number with one bilingual scan,
- DesignAgent re-derived it again (a richer scan + a rejected-alternatives
  fallback) to build the design prompt, and
- DesignAgent.run() inlined the drift comparison, observable only via the audit
  ledger and with no direct test coverage (the "H1/H3 silent-bug class").

This module concentrates all of it behind a small, pure interface so it is
testable against example documents without mocking agents or workspaces:
- ``recommended_hypothesis(hypothesis_md)`` -> the recommended H number AND the
  formatted block the design prompt embeds,
- ``used_hypothesis(design_md)``           -> the H number DESIGN.md built around,
- ``drift_reason(recommended_n, used_n)``  -> a human-readable reason if the
  design tested a different theory than the one selected, else ``None``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Recommendation section + rejected-alternatives section headings (bilingual).
# \b does not work on CJK, so a non-word-char lookahead stands in.
_REC_HEADING = re.compile(
    r"^##\s*(Recommendation|推荐|推荐方案|建议)(?![A-Za-z])", re.IGNORECASE
)
_REJECT_HEADING = re.compile(
    r"^##\s*(Rejected|Reject|被否决|被驳回|已驳回)(?![A-Za-z])", re.IGNORECASE
)

# Where DESIGN.md declares which hypothesis it implements (scanned in the first
# 3000 chars — the Theoretical Anchor section — to avoid matching incidental
# later mentions like "future work could test H2").
_USED_PATTERNS = [
    r"Selected\s+hypothesis[^\n]*?H\s*(\d+)",
    r"选[定择]\s*假设[^\n]*?H\s*(\d+)",
    r"\*\*\s*H\s*(\d+)\s*[:：]",
    r"build(?:ing)?\s+(?:around\s+)?H\s*(\d+)",
    r"构建\s*H\s*(\d+)",
]


@dataclass(frozen=True)
class Recommendation:
    """The recommended hypothesis: its H number (or ``None`` if none could be
    isolated) and the formatted text block the design prompt embeds."""

    number: str | None
    text: str


def recommended_hypothesis(hypothesis_md: str) -> Recommendation:
    """Parse hypothesis.md for the recommended H number + its block.

    Bilingual: recognises English ("## Recommendation", "Build H<N>") and Chinese
    ("## 推荐", "构建 H<N>") headings and verbs. If the Recommendation section names
    no number explicitly, falls back to the rejected-alternatives block — with
    exactly two of three rejected, the missing one is the recommendation. Critical
    for the dual-mode workflow: silent extraction failure makes DesignAgent build
    the wrong hypothesis by default.
    """
    lines = hypothesis_md.splitlines()
    rec_lines: list[str] = []
    h_number: str | None = None

    # 1. Scan for the Recommendation section.
    in_rec = False
    for line in lines:
        if _REC_HEADING.match(line):
            in_rec = True
            continue
        if in_rec:
            if line.startswith("## "):
                break
            rec_lines.append(line)
    recommendation = "\n".join(rec_lines).strip()

    # 2. Find the recommended H number — multiple patterns, in priority order.
    if recommendation:
        patterns = [
            r"(?:Build|构建|推荐|选择|采用)\s*H\s*[:：]?\s*(\d+)",
            r"\*\*\s*(?:Build|构建)\s*H\s*[:：]?\s*(\d+)",
            r"H\s*(\d+)\b",  # last resort: first H<N> in recommendation block
        ]
        for p in patterns:
            m = re.search(p, recommendation, re.IGNORECASE)
            if m:
                h_number = m.group(1)
                break

    # 3. Fallback: exactly two of three rejected → the missing one is recommended.
    if h_number is None:
        rejected_nums: set[str] = set()
        in_reject = False
        for line in lines:
            if _REJECT_HEADING.match(line):
                in_reject = True
                continue
            if in_reject and line.startswith("## "):
                break
            if in_reject:
                for m in re.finditer(r"H\s*(\d+)", line):
                    rejected_nums.add(m.group(1))
        if len(rejected_nums) == 2:
            all_nums = {"1", "2", "3"}
            candidate = all_nums - rejected_nums
            if len(candidate) == 1:
                h_number = candidate.pop()

    # 4. Extract the chosen H block.
    recommended_h = ""
    if h_number:
        in_block = False
        block_lines: list[str] = []
        block_heading_re = re.compile(rf"^##\s*H\s*{h_number}\s*[:：]")
        other_h_re = re.compile(r"^##\s*H\s*\d+\s*[:：]")
        for line in lines:
            if block_heading_re.match(line):
                in_block = True
                block_lines.append(line)
                continue
            if in_block:
                if other_h_re.match(line):
                    break
                if _REC_HEADING.match(line) or _REJECT_HEADING.match(line):
                    break
                block_lines.append(line)
        recommended_h = "\n".join(block_lines).strip()

    # 5. Compose the prompt block — with a clear marker for the LLM.
    if recommended_h and recommendation:
        text = (
            f"**RECOMMENDED HYPOTHESIS: H{h_number}** "
            f"(extracted from hypothesis.md — build the design around this one)\n\n"
            f"{recommended_h}\n\n"
            f"### Why this hypothesis was recommended\n\n{recommendation}"
        )
    elif recommendation:
        text = (
            f"**Recommendation block from hypothesis.md "
            f"(could not isolate single H block — read carefully):**\n\n"
            f"{recommendation}\n\n"
            f"---\n\n## Full hypothesis.md\n\n{hypothesis_md[:1500]}"
        )
    else:
        text = hypothesis_md[:1500]

    return Recommendation(number=h_number, text=text)


def used_hypothesis(design_md: str) -> str | None:
    """Inspect DESIGN.md for which H<N> it claims to implement (the "Selected
    hypothesis" / "选定假设" marker in the Theoretical Anchor). ``None`` if absent
    (e.g. reproduce mode)."""
    for p in _USED_PATTERNS:
        m = re.search(p, design_md[:3000], re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def drift_reason(recommended_n: str | None, used_n: str | None) -> str | None:
    """Return a human-readable reason iff DESIGN.md built around a different
    hypothesis than hypothesis.md recommended, else ``None``. Both numbers must be
    known — a missing recommendation or missing design marker is not drift."""
    if recommended_n and used_n and recommended_n != used_n:
        return (
            f"hypothesis.md recommended H{recommended_n}, but DESIGN.md built around "
            f"H{used_n}. The implementation tests a different theory than the one selected."
        )
    return None
