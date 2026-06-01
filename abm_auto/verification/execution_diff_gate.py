"""ExecutionDiffGate — the deterministic half of ε, as a Gate (ADR-013 D-LLM).

This Gate proves the most load-bearing ADR-013 decision in code: a judge
that contained an LLM cannot be self-tested, so ε (`verify_execution`)
must SPLIT into

  - generation side: `extract_qualitative_claims` (one LLM call, reads
    story.md → direction claims). NOT a Gate — it is a generator.
  - judgement side: classify the sim trajectory + diff against the claims.
    Deterministic (no LLM). THIS is the Gate.

The LLM generates claims; deterministic code judges whether the sim
honours them. That is the harness's generate/judge separation reproduced
at the smallest scale.

Tier = "refutation". A mismatch (story says S decreases, sim shows S
increasing) genuinely REFUTES the generated mechanism. But a clean match
does NOT verify the mechanism is correct — only that its coarse
direction is consistent with the story. Same ceiling as NullGate; a
passed Verdict renders "not refuted", never "verified".
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from abm_auto.verification.execution_verifier import (
    QualitativeClaim,
    classify_trajectory_csv,
    diff_claims_vs_actuals,
)
from abm_auto.verification.gate import Verdict


@dataclass
class ExecutionDiffInput:
    """Input to ExecutionDiffGate: the LLM-generated claims + where the
    sim trajectory lives + which target columns to check.

    `claims` come from the generation side (extract_qualitative_claims);
    the Gate treats them as given input and judges the sim against them.
    """

    claims: list[QualitativeClaim]
    sim_csv: Path
    targets: list[str]


class ExecutionDiffGate:
    """Gate over the 'sim trajectory + claims' family: refutes a generated
    mechanism whose simulated direction-of-change contradicts the story's
    claimed direction. Deterministic — no LLM. Refutation tier.
    """

    name = "execution_diff"
    family = "trajectory_vs_claims"
    tier = "refutation"

    def judge(self, x: ExecutionDiffInput) -> Verdict:
        """Deterministic: classify the sim trajectory, diff against claims.

        passed iff no direction mismatch. Targets the LLM left 'unclear',
        or that the sim couldn't classify, are skipped (can't refute what
        you can't compare) — matching the existing diff semantics exactly.
        """
        actuals = classify_trajectory_csv(x.sim_csv, x.targets)
        result = diff_claims_vs_actuals(x.claims, actuals)
        passed = result.is_valid
        reasons = [] if passed else result.feedback()
        # salient_number: (#mismatches, 0) — 0 mismatches is the pass line.
        # Kept as a margin so provenance shows "2 of 3 targets contradicted"
        # rather than a bare bool.
        n_compared = sum(
            1 for c in x.claims
            if c.direction != "unclear"
            and any(a.target == c.target and a.direction != "unclear" for a in actuals)
        )
        return Verdict(
            passed=passed,
            tier="refutation",
            gate_name=self.name,
            reasons=reasons,
            salient_number=(float(len(result.mismatches)), 0.0),
            evidence={
                "mismatches": result.mismatches,
                "n_claims": len(x.claims),
                "n_compared": n_compared,
            },
        )

    def self_test(self) -> bool:
        """Refutation-paradigm self-test on synthetic ground truth.

        Writes a tiny CSV with a KNOWN monotonic-decreasing column, then:
          (a) a claim that matches reality (monotonic_decrease) → passed
          (b) a claim that contradicts reality (monotonic_increase) →
              refuted (not passed), and the mismatch is reported.

        Deterministic, no LLM, no network. Necessary-not-sufficient (a
        match doesn't prove correctness) — hence refutation tier.
        """
        import tempfile

        # Known ground truth: a column that strictly decreases.
        rows = ["tick,susceptible"]
        for t in range(20):
            rows.append(f"{t},{100 - 4 * t}")
        with tempfile.TemporaryDirectory() as d:
            csv = Path(d) / "sim.csv"
            csv.write_text("\n".join(rows) + "\n", encoding="utf-8")

            # (a) matching claim → not refuted
            match = ExecutionDiffInput(
                claims=[QualitativeClaim(target="susceptible",
                                         direction="monotonic_decrease")],
                sim_csv=csv,
                targets=["susceptible"],
            )
            if not self.judge(match).passed:
                return False

            # (b) contradicting claim → refuted
            contra = ExecutionDiffInput(
                claims=[QualitativeClaim(target="susceptible",
                                         direction="monotonic_increase")],
                sim_csv=csv,
                targets=["susceptible"],
            )
            v = self.judge(contra)
            if v.passed:
                return False  # a real contradiction slipped through
            if not any("susceptible" in r for r in v.reasons):
                return False  # caught but not attributed
        return True
