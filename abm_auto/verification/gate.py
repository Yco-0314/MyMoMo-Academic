"""The `Gate` seam — the atom of abm-auto's research harness (ADR-013).

A Gate is a DETERMINISTIC check over one intermediate-state family. It
returns a uniform `Verdict` carrying a `tier`. The harness reads only
`passed + tier` for flow control; the continuous `salient_number` (if
any) sinks into provenance + human-readable rendering.

Why this exists
---------------
abm-auto had five scattered validators with five return types and
inconsistent pass-polarity (see ADR-013). `Gate` concentrates that
smeared complexity into one deep seam so the GVR loop, the
diagnostics-HALT, and the method-transfer harness all consume one shape;
a new method×domain adds a Gate, not new glue.

The load-bearing rule (ADR-013)
-----------------------------------------
`judge` MUST be deterministic — no LLM inside. That is what lets a Gate
be `self_test`ed on synthetic ground truth, and it is what stops a
generator from self-certifying. `tier` is DERIVED from the self-test
paradigm, never a hand-written label:

  - "verification" — the self-test proves a COMPLETE property (e.g.
    known-bad input is always caught AND clean input always passes).
    A Verdict from such a Gate may legitimately say "verified."
  - "refutation"  — the self-test only proves the Gate can REJECT
    obvious failure (e.g. tells signal from white noise) but cannot
    prove the finding has domain meaning. Its Verdict may say only
    "not refuted." Conflating the two is the laundering ADR-013 forbids.

This module defines only the seam (Protocol + Verdict + Tier). Concrete
Gates live next to the validator they wrap (e.g. AntiPatternGate in
codegen/, NullGate in analysis/).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

Tier = Literal["verification", "refutation"]


@dataclass
class Verdict:
    """A Gate's uniform output.

    The harness reads only `passed` + `tier` for flow decisions. Everything
    else is for provenance + human rendering and must never drive a
    pass/fail branch (keeps the harness thin, per ADR-013 D2).
    """

    passed: bool
    tier: Tier
    gate_name: str
    #: Human-readable reasons the check failed (empty when passed). For a
    #: refutation Gate that "passed", this stays empty — passing a
    #: refutation Gate means "not refuted", NOT "verified true".
    reasons: list[str] = field(default_factory=list)
    #: Optional (score, threshold). Present only for Gates with a
    #: continuous quantity (null p-value, calibration MSE, curvature).
    #: Sinks into provenance + rendering; never a flow-control input.
    salient_number: tuple[float, float] | None = None
    #: Gate-specific evidence the harness does NOT interpret. Renderer +
    #: provenance may unpack it by gate_name.
    evidence: object | None = None

    def render(self) -> str:
        """One-line human summary. Honest about tier: a passed refutation
        Gate renders as 'not refuted', not 'verified'."""
        if self.passed:
            word = "verified" if self.tier == "verification" else "not refuted"
            head = f"[{self.gate_name}] PASS ({word})"
        else:
            head = f"[{self.gate_name}] FAIL ({self.tier})"
        if self.salient_number is not None:
            score, thresh = self.salient_number
            head += f" — score={score:.4g} threshold={thresh:.4g}"
        if self.reasons:
            head += "\n  " + "\n  ".join(self.reasons[:10])
        return head


@runtime_checkable
class Gate(Protocol):
    """A deterministic check over one intermediate-state family.

    Implementations declare:
      - `name`: stable identifier (appears in Verdict + provenance).
      - `family`: which intermediate-state family it consumes (source
        code / scalar trajectory / interaction graph / ...). The harness
        routes artifacts to Gates by family.
      - `tier`: derived from the self-test paradigm, not hand-written.

    and provide:
      - `judge(x)`: deterministic verdict over an input of its family.
      - `self_test()`: run the Gate's self-test paradigm on synthetic
        ground truth; True iff the Gate still discriminates correctly.
        This is the audit surface — the thing a reviewer checks once so
        the Gate can be trusted thereafter.
    """

    name: str
    family: str
    tier: Tier

    def judge(self, x) -> Verdict: ...

    def self_test(self) -> bool: ...


def outcome_from_verdict(verdict: Verdict, *, fatal_tiers: frozenset[Tier] = frozenset({"verification"})):
    """Adapt a Gate `Verdict` into the GVR loop's `ValidationOutcome`.

    The single, canonical translation between the two verdict vocabularies
    (ADR-013): Gate's (passed + tier) → GVR's (ok + severity). Replaces the
    hand-rolled translation that each GVR validator previously inlined —
    which dropped tier and salient_number every time.

    severity policy is the CONSUMER's decision, not the Gate's: a tier is a
    fixed property of a Gate, but "does failing it halt this loop" depends
    on the loop. The default (`verification → fatal`, everything else soft)
    matches GVR's current need — only verification-tier Gates run in GVR
    today, and a structural defect must block the retry. The parameter
    leaves the door open for a consumer (e.g. a future refutation Gate in
    GVR, or provenance) to choose differently, without baking one policy in.

    salient_number is preserved into `structured` (lossless) so a consumer
    that wants the margin still has it — ValidationOutcome has no dedicated
    field, but its `structured` dict is exactly for this.
    """
    from abm_auto.refinement import ValidationOutcome

    if verdict.passed:
        return ValidationOutcome(ok=True)

    structured: dict = dict(verdict.evidence) if isinstance(verdict.evidence, dict) else {}
    if verdict.salient_number is not None:
        structured["salient_score"] = verdict.salient_number[0]
        structured["salient_threshold"] = verdict.salient_number[1]
    structured["tier"] = verdict.tier

    return ValidationOutcome(
        ok=False,
        reasons=list(verdict.reasons),
        severity="fatal" if verdict.tier in fatal_tiers else "soft",
        structured=structured,
    )
