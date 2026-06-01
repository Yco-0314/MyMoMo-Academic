"""AntiPatternGate — the first concrete Gate (ADR-013).

Wraps the existing `anti_patterns.scan()` behind the `Gate` seam without
changing `scan()` or its callers. `scan()` stays the catalogue's source
of truth; this Gate adapts its `list[str]` output into a uniform
`Verdict` and adds the `self_test` audit surface.

Tier = "verification". Justification (the self-test paradigm): the
anti-pattern catalogue is a finite set of known-bad regexes, so the
self-test proves a COMPLETE property —
  (a) clean code passes, and
  (b) every catalogued pattern (all 19) is caught and correctly
      attributed, using the canonical `anti_patterns.TRIGGERS` map.

The trigger map is the single source of truth shared with the fixture
test; the catalogue's coverage gate forces a trigger for every pattern,
so in-Gate coverage stays 19/19 as the catalogue grows. That
completeness is what earns the verification tier — derived here, not
asserted as a label.
"""
from __future__ import annotations

from abm_auto.codegen.anti_patterns import ANTI_PATTERNS, scan
from abm_auto.verification.gate import Verdict


class AntiPatternGate:
    """Gate over the 'source code' family: rejects code containing any
    catalogued LLM-hallucination anti-pattern."""

    name = "anti_pattern"
    family = "source_code"
    tier = "verification"

    def judge(self, code_files: dict[str, str]) -> Verdict:
        """Deterministic: scan code_files, fail iff any anti-pattern hits.

        `code_files` is the same {path: contents} dict `scan()` already
        consumes (from `Workspace.read_model_files()`), so this Gate drops
        into the existing GVR call site unchanged.
        """
        issues = scan(code_files)
        return Verdict(
            passed=not issues,
            tier="verification",
            gate_name=self.name,
            reasons=issues,
            salient_number=None,  # anti-pattern is boolean — no continuous score
            evidence={"issue_count": len(issues)},
        )

    def self_test(self) -> bool:
        """Verification-paradigm self-test on synthetic ground truth.

        Completeness check, 19/19, using the canonical TRIGGERS map:
          (a) a known-clean snippet passes, AND
          (b) EVERY catalogued AntiPattern is caught + correctly
              attributed by its trigger snippet.

        Returns True iff the Gate still discriminates correctly. If a
        future catalogue edit breaks a trigger (or omits one), this
        returns False — the audit surface a reviewer trusts once.
        """
        from abm_auto.codegen.anti_patterns import TRIGGERS

        # (b-guard) every pattern must have a trigger (no silent gap)
        catalogue_names = {ap.name for ap in ANTI_PATTERNS}
        if set(TRIGGERS) != catalogue_names:
            return False

        # (a) clean code must pass
        clean = {"core/model.py": "class M:\n    def setup(self):\n        pass\n"}
        if self.judge(clean).passed is not True:
            return False

        # (b) each trigger placed in a file its pattern's `where` accepts
        where_by_name = {ap.name: ap.where for ap in ANTI_PATTERNS}
        for name, trigger in TRIGGERS.items():
            fname = _filename_for(where_by_name[name])
            v = self.judge({fname: trigger})
            if v.passed:
                return False  # a catalogued bad pattern slipped through
            if not any(name in r for r in v.reasons):
                return False  # caught, but not attributed to this pattern
        return True


def _filename_for(where) -> str:
    """A filename the anti-pattern's `where` filter accepts (or a default
    .py path when it has no filter)."""
    candidates = ["core/model.py", "core/agent.py", "core/environment.py", "main.py"]
    if where is None:
        return candidates[0]
    for c in candidates:
        if where(c):
            return c
    return candidates[0]
