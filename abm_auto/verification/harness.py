"""Harness — tier-aware orchestration of Gates (ADR-013).

The molecule built from the Gate atom. A bare `for g in gates: g.judge(x)`
would not earn its place (delete it and callers just loop themselves).
The Harness earns depth by solving three things a single Gate cannot:

  1. Family routing — each Gate consumes a different intermediate-state
     family (source_code / scalar_trajectory / trajectory_vs_claims /
     diagnostics_signal / spec_and_code). The Harness feeds each Gate the
     payload for its family, and SKIPS gates whose family is absent
     (absent ≠ failed).
  2. Tier-aware aggregation (the load-bearing part) — it does NOT collapse
     to a flat AND. A failed verification Gate ("structure is definitely
     wrong") and a failed refutation Gate ("no signal beat the null") mean
     different things and must never be merged. The report keeps two
     columns:
        - verification: a HARD DOOR. Any ran-and-failed verification Gate
          ⇒ `verification_clear = False` (a definite structural defect).
        - refutation: an EVIDENCE RECORD. Failures are tallied, not
          gated — a refutation failure is an honest negative result
          ("this method showed no signal here"), not a pipeline fault.
  3. A structured, tier-honest report the caller consumes — the Harness
     does NOT decide "halt vs proceed". It produces facts; the caller
     (GVR / diagnostics / a research report) applies its own policy.

This module is READ-ONLY new code: it composes existing Gates, touches no
existing flow (GVR still calls the legacy validators). Artifact-hash
provenance / replay is deliberately deferred to the provenance ledger
(ADR-013 candidate 3); this step proves tier-aware unified consumption +
the report shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from abm_auto.verification.gate import Gate, Verdict


@dataclass
class HarnessReport:
    """Tier-separated outcome of running a set of Gates over some artifacts.

    Deliberately NOT a single boolean. The two tiers answer different
    questions and stay separate so "structurally wrong" is never confused
    with "no evidence found" (the ADR-012 laundering guard, at the
    aggregate level).
    """

    verdicts: list[Verdict] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)  # gate names with no artifact

    # ── verification tier: the hard door ──
    @property
    def verification_verdicts(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.tier == "verification"]

    @property
    def verification_clear(self) -> bool:
        """True iff every verification Gate that RAN passed. A definite
        structural defect (a failed verification Gate) makes this False.
        Vacuously True if no verification Gate ran."""
        return all(v.passed for v in self.verification_verdicts)

    @property
    def verification_failures(self) -> list[Verdict]:
        return [v for v in self.verification_verdicts if not v.passed]

    # ── refutation tier: the evidence record (never a gate) ──
    @property
    def refutation_verdicts(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.tier == "refutation"]

    @property
    def refutation_survived(self) -> list[str]:
        """Refutation Gates whose finding beat its null (passed = not
        refuted). These are evidence the finding survived a challenge —
        NOT proof it is true."""
        return [v.gate_name for v in self.refutation_verdicts if v.passed]

    @property
    def refutation_failed(self) -> list[str]:
        """Refutation Gates that did not beat their null. Honest negatives,
        not pipeline faults."""
        return [v.gate_name for v in self.refutation_verdicts if not v.passed]

    def render(self) -> str:
        lines = ["Harness report"]
        door = "CLEAR" if self.verification_clear else "DEFECT"
        lines.append(f"  verification (hard door): {door}")
        for v in self.verification_verdicts:
            mark = "ok" if v.passed else "FAIL"
            lines.append(f"    [{mark}] {v.gate_name}")
        if self.refutation_verdicts:
            lines.append(
                f"  refutation (evidence): "
                f"{len(self.refutation_survived)} survived, "
                f"{len(self.refutation_failed)} no-signal"
            )
            for v in self.refutation_verdicts:
                word = "not refuted" if v.passed else "no signal"
                extra = ""
                if v.salient_number is not None:
                    extra = f" (score={v.salient_number[0]:.4g} thr={v.salient_number[1]:.4g})"
                lines.append(f"    [{word}] {v.gate_name}{extra}")
        if self.skipped:
            lines.append(f"  skipped (no artifact): {', '.join(self.skipped)}")
        return "\n".join(lines)


class Harness:
    """Routes artifacts to Gates by family and aggregates tier-aware.

    Stateless: `run` is a pure function of (gates, artifacts). Holds no
    flow-control policy — it reports, the caller decides.
    """

    def run(self, gates: list[Gate], artifacts: dict[str, object]) -> HarnessReport:
        """Run each Gate against the payload for its family.

        Args:
            gates: the Gates to apply.
            artifacts: {family_name: payload}. A Gate whose `family` is not
                a key here is SKIPPED (recorded, not failed) — not every
                run produces every intermediate-state family.

        Returns a HarnessReport with tier-separated results. Deterministic
        given deterministic Gates (which is enforced by the Gate contract:
        no LLM in judge).
        """
        report = HarnessReport()
        for g in gates:
            if g.family not in artifacts:
                report.skipped.append(g.name)
                continue
            report.verdicts.append(g.judge(artifacts[g.family]))
        return report
