"""NullGate — surrogate-null Gate, the refutation-tier exemplar (ADR-013).

Wraps `method_transfer_guard.test_against_null` behind the Gate seam. It
is the counterpart to AntiPatternGate: where that Gate is
*verification* tier (proves a complete property), this one is
*refutation* tier — it can only reject the null hypothesis "this signal
is indistinguishable from noise", never prove the signal has domain
meaning. That ceiling is exactly the W3 / ADR-013 honesty boundary, made
structural.

What "passed" means here (the subtle part)
------------------------------------------
The Gate refutes the noise hypothesis. So:
  - signal BEATS its surrogate null (p < α)  → noise hypothesis REFUTED
    → passed=True. Honest reading: "not refuted as a real signal" /
    "survived the null", NOT "verified meaningful".
  - signal fails to beat null (p ≥ α)        → consistent with noise
    → passed=False.

A passed NullGate Verdict therefore renders as "not refuted", never
"verified" — the tier carries that distinction so a surrogate-survivor
can never be laundered into a validated finding.

salient_number = (p_value, alpha): the margin sinks into provenance +
rendering (e.g. "p=0.144, missed 0.05 by 0.094") instead of collapsing
to a bare bool — the Demo-1 lesson that margin is the informative part
of a negative.
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from abm_auto.analysis.method_transfer_guard import test_against_null
from abm_auto.verification.gate import Verdict


class NullGate:
    """Gate over the 'scalar trajectory' family: refutes the hypothesis
    that a statistic on the series is indistinguishable from a surrogate
    null. Refutation tier.
    """

    name = "surrogate_null"
    family = "scalar_trajectory"
    tier = "refutation"

    def __init__(
        self,
        statistic: Callable[[np.ndarray], float],
        *,
        null_kind: str = "phase",
        n_surrogates: int = 200,
        alpha: float = 0.05,
        seed: int = 0,
    ) -> None:
        """
        Args:
            statistic: series -> scalar (e.g. CSD ews_strength). The thing
                whose significance against a null we test.
            null_kind: "phase" (strict — keeps spectrum, destroys trend)
                or "shuffle" (destroys all temporal order). Default phase,
                the stricter test (the Demo-1 headline null).
            alpha: significance threshold (default 0.05).
        """
        self.statistic = statistic
        self.null_kind = null_kind
        self.n_surrogates = n_surrogates
        self.alpha = alpha
        self.seed = seed

    def judge(self, series: np.ndarray) -> Verdict:
        """Deterministic given seed: run the surrogate-null test, pass iff
        the statistic beats the null at alpha."""
        g = test_against_null(
            series,
            self.statistic,
            n_surrogates=self.n_surrogates,
            null_kind=self.null_kind,
            seed=self.seed,
        )
        passed = g.p_value < self.alpha
        if passed:
            reasons: list[str] = []
        else:
            reasons = [
                f"signal not distinguishable from {self.null_kind} null: "
                f"p={g.p_value:.4g} ≥ α={self.alpha} "
                f"(observed={g.observed:.4g}, null_mean={g.null_mean:.4g}, "
                f"z={g.z_score:.2f})"
            ]
        return Verdict(
            passed=passed,
            tier="refutation",
            gate_name=self.name,
            reasons=reasons,
            salient_number=(g.p_value, self.alpha),
            evidence={
                "observed": g.observed,
                "null_mean": g.null_mean,
                "null_std": g.null_std,
                "z_score": g.z_score,
                "null_kind": g.null_kind,
                "n_surrogates": g.n_surrogates,
            },
        )

    def self_test(self) -> bool:
        """Refutation-paradigm self-test on synthetic ground truth.

        The paradigm proves only rejection-of-obvious-failure, so the
        self-test checks the two ends that DEFINE a sound surrogate-null:
          (a) a clearly-trending series (rising-AR1 red noise) BEATS the
              null (passed=True), and
          (b) white noise does NOT beat its own null (passed=False).

        These are the same synthetic anchors used in
        tests/test_method_transfer.py, here turned into the Gate's audit
        surface. Passing both is necessary (not sufficient) — which is
        precisely why the tier is 'refutation', not 'verification'.
        """
        rng = np.random.default_rng(0)
        n = 200

        # (a) rising lag-1 autocorrelation → must beat the null
        rising = np.zeros(n)
        a = np.linspace(0.1, 0.95, n)
        for t in range(1, n):
            rising[t] = a[t] * rising[t - 1] + rng.normal(0, 0.1)

        # (b) white noise → must NOT beat the null
        white = rng.normal(0, 1, n)

        # statistic: CSD early-warning strength (the canonical use)
        from abm_auto.analysis.critical_slowing_down import critical_slowing_down

        stat = lambda s: critical_slowing_down(s).ews_strength
        gate = NullGate(stat, null_kind=self.null_kind,
                        n_surrogates=self.n_surrogates, alpha=self.alpha, seed=1)

        if not gate.judge(rising).passed:
            return False  # a real trend failed to beat the null → unsound
        if gate.judge(white).passed:
            return False  # white noise beat the null → unsound (false positive)
        return True
