"""Tests for the hardened AI-ASSUMPTION counter (ADR-013 W4 dogfood).

The Yaman design dogfood showed the raw `findall("AI-ASSUMPTION")` count was
inflated by three artifacts: the rule-explanation heading, the same
assumption restated inline AND in §Assumptions (double count), and
template-owned boilerplate tagged in error. These pin the fix — including the
bold-form `**AI-ASSUMPTION**:` tag the first cut missed.
"""
from __future__ import annotations

import re

from abm_auto.agents.viability_checker import count_assumptions


def test_inline_bracket_tag_counted() -> None:
    assert count_assumptions("- `tolerance`: float [AI-ASSUMPTION: standard default]") == 1


def test_bold_section_tag_counted() -> None:
    # the §Assumptions section uses markdown bold — must still count
    assert count_assumptions("4. **AI-ASSUMPTION**: death = age/(age+10)") == 1


def test_rule_heading_not_a_tag() -> None:
    # the gate must not count the prompt's own rule-explanation heading
    assert count_assumptions("### 6. Assumptions (AI-ASSUMPTION only — last resort)") == 0


def test_chinese_rule_heading_not_a_tag() -> None:
    assert count_assumptions("## 6. 假设（仅AI-ASSUMPTION — 最后手段）") == 0


def test_no_colon_no_bracket_prose_is_not_a_tag() -> None:
    assert count_assumptions("We avoided any AI-ASSUMPTION here entirely.") == 0


def test_bare_bracket_marker_counted() -> None:
    # a bare [AI-ASSUMPTION] with no colon is still a real tag (must not be
    # silently dropped — that under-counts real assumptions)
    assert count_assumptions("- `max_generations`: 100 [AI-ASSUMPTION]") == 1


def test_parenthesized_emdash_heading_not_a_tag() -> None:
    # the §Assumptions heading uses parens + em-dash, no bracket, no colon
    assert count_assumptions("## 6. 假设（AI-ASSUMPTION——最后手段）") == 0


def test_inline_and_section_restatement_dedup() -> None:
    design = (
        "| `generations` | int | 200 | [AI-ASSUMPTION: common in the paper] |\n"
        "6. **AI-ASSUMPTION**: `generations` = 200\n"
    )
    assert count_assumptions(design) == 1   # one subject, counted once


def test_template_boilerplate_excluded() -> None:
    design = (
        "- `id`: int [AI-ASSUMPTION: standard]\n"
        "- `scenario_id`: int [AI-ASSUMPTION: standard]\n"
        "- `run_num`: int [AI-ASSUMPTION: standard]\n"
    )
    assert count_assumptions(design) == 0


def test_anonymous_assumption_still_counted() -> None:
    # a real assumption with no code identifier must NOT be silently dropped
    assert count_assumptions("- recipe tree item IDs start at 1 [AI-ASSUMPTION: not stated]") == 1


def test_distinct_subjects_counted_separately() -> None:
    design = (
        "- `generations` [AI-ASSUMPTION: a]\n"
        "- `attempts_per_generation` [AI-ASSUMPTION: b]\n"
        "- `repetitions` [AI-ASSUMPTION: c]\n"
    )
    assert count_assumptions(design) == 3


def test_hardened_below_raw_on_realistic_mix() -> None:
    """A design with boilerplate + duplication + a heading: hardened count is
    well below the naive findall, and equals the distinct real assumptions."""
    design = (
        "## 6. Assumptions (AI-ASSUMPTION only — last resort)\n"   # heading (0)
        "- `id`: int [AI-ASSUMPTION: standard]\n"                  # boilerplate (0)
        "- `scenario_id` [AI-ASSUMPTION: standard]\n"             # boilerplate (0)
        "| `generations` | 200 | [AI-ASSUMPTION: paper] |\n"      # real (1)
        "**AI-ASSUMPTION**: `generations` = 200\n"               # dup of above (0)
        "| `attempts` | 50 | [AI-ASSUMPTION: unstated] |\n"       # real (1)
        "- recipe tree encoding [AI-ASSUMPTION: not stated]\n"    # real anon (1)
    )
    raw = len(re.findall(r"AI[-_]ASSUMPTION", design, re.IGNORECASE))
    hardened = count_assumptions(design)
    assert raw == 7
    assert hardened == 3        # generations, attempts, recipe-tree
    assert hardened < raw
