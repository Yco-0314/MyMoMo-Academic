"""CoordNullGate — refutation-tier gate (mirrors analysis/null_gate.py). The
optimized network must beat BOTH the original AND the random-edge null on makespan
(lower is better) by `margin`. Passing means "not refuted" — the optimization's
edge SELECTION (not just adding edges) survived; it never means "verified"."""
from __future__ import annotations

from abm_auto.verification.gate import Verdict


class CoordNullGate:
    name = "coord_null"
    family = "coord_makespan"
    tier = "refutation"

    def __init__(self, *, margin: float = 1.0):
        self.margin = margin

    def judge(self, *, original: float, optimized: float, null: float) -> Verdict:
        beats_original = optimized <= original - self.margin
        beats_null = optimized <= null - self.margin
        passed = beats_original and beats_null
        reasons = []
        if not beats_original:
            reasons.append(f"optimized makespan {optimized:.1f} did not beat original {original:.1f} by {self.margin}")
        if not beats_null:
            reasons.append(f"optimized {optimized:.1f} ≈ random-edge null {null:.1f} — edge SELECTION not shown")
        return Verdict(passed=passed, tier="refutation",
                       gate_name="coord optimization beats original AND random-edge null (makespan)",
                       salient_number=(round(null - optimized, 2), self.margin), reasons=reasons)

    def self_test(self) -> bool:
        good = self.judge(original=50.0, optimized=40.0, null=49.0).passed       # selection helps
        tie = self.judge(original=50.0, optimized=44.0, null=44.2).passed        # just adding edges
        return good is True and tie is False
