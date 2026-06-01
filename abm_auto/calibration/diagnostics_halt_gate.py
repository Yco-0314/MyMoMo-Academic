"""DiagnosticsHaltGate — the polarity-inverting Gate (ADR-013).

Wraps the *judgement* of `maybe_halt_on_diagnostics` behind the Gate
seam. This Gate exists to prove the seam absorbs a validator whose
native polarity is INVERTED relative to every other check:

  maybe_halt_on_diagnostics → True  means "HALT" means BAD.
  Gate convention             → passed=True means GOOD.

So the adapter inverts: `passed = not should_halt`. A passed Verdict
means "the diagnostics did not refute the simulator as broken" — not
"the simulator is verified correct".

Pure-judgement extraction
--------------------------
The original function mixes judgement with a side effect (it writes
kill_memo.md). A Gate's `judge` must be deterministic and side-effect
free, so this Gate judges the **signal dict** directly and writes
nothing. The kill_memo side effect stays the caller's responsibility
(the pipeline phase), exactly where flow-control belongs.

Tier = "refutation". The all-FLAT / all-MISMATCH policy refutes "the
simulator is functional" with high confidence (insensitive-to-every-
parameter loss landscape = structurally broken). It cannot verify a
simulator is functional — partial signals deliberately do not fire.
"""
from __future__ import annotations

from abm_auto.verification.gate import Verdict


class DiagnosticsHaltGate:
    """Gate over the 'diagnostics signal' family: refutes a simulator as
    non-functional when ALL parameters are flat or ALL ε-targets mismatch.
    Refutation tier. Polarity inverted vs the wrapped halt function.
    """

    name = "diagnostics_halt"
    family = "diagnostics_signal"
    tier = "refutation"

    def judge(self, signal: dict) -> Verdict:
        """Pure: given the diagnostics_signal dict, decide if the simulator
        is refuted as broken. `passed = not halt` (polarity inversion).

        Mirrors maybe_halt_on_diagnostics' policy exactly:
          all-FLAT β  (n_flat == n_params > 0)  OR
          all-MISMATCH ε (n_mismatch == n_claims > 0)
        Partial signals do NOT refute (they're genuine identifiability
        issues for the report, not proof of brokenness).
        """
        n_params = int(signal.get("n_params", 0))
        n_flat = int(signal.get("n_flat_params", 0))
        n_claims = int(signal.get("n_eps_claims", 0))
        n_mismatch = int(signal.get("n_eps_mismatches", 0))

        all_flat = n_params > 0 and n_flat == n_params
        all_mismatch = n_claims > 0 and n_mismatch == n_claims
        halt = all_flat or all_mismatch

        reasons: list[str] = []
        if all_flat:
            reasons.append(
                f"All {n_params} calibration parameter(s) show FLAT profile "
                f"likelihood (curvature < 0.1) → loss landscape insensitive "
                f"to every parameter; simulator likely does not transition state."
            )
        if all_mismatch:
            targets_str = ", ".join(signal.get("eps_mismatch_targets", []) or [])
            reasons.append(
                f"All {n_claims} ε execution-fidelity targets MISMATCH the "
                f"story's claimed directions ({targets_str}); simulator "
                f"contradicts the described mechanism."
            )

        return Verdict(
            passed=not halt,                 # polarity inversion
            tier="refutation",
            gate_name=self.name,
            reasons=reasons,                 # populated only when refuted (halt)
            salient_number=None,             # categorical, no continuous margin
            evidence={
                "n_params": n_params, "n_flat_params": n_flat,
                "n_eps_claims": n_claims, "n_eps_mismatches": n_mismatch,
                "all_flat": all_flat, "all_mismatch": all_mismatch,
            },
        )

    def self_test(self) -> bool:
        """Refutation-paradigm self-test on synthetic signal dicts.

          (a) clean signal (no flat, no mismatch) → not refuted (passed)
          (b) all-flat β → refuted (not passed)
          (c) all-mismatch ε → refuted (not passed)
          (d) partial (1 of 3 flat) → NOT refuted (passed) — the policy's
              deliberate conservatism

        Pure, no I/O. (b)/(c) are the rejection end; (a)/(d) guard against
        over-firing. Necessary-not-sufficient → refutation tier.
        """
        clean = {"n_params": 3, "n_flat_params": 0,
                 "n_eps_claims": 3, "n_eps_mismatches": 0}
        if not self.judge(clean).passed:
            return False

        all_flat = {"n_params": 3, "n_flat_params": 3,
                    "n_eps_claims": 0, "n_eps_mismatches": 0}
        if self.judge(all_flat).passed:
            return False

        all_mismatch = {"n_params": 3, "n_flat_params": 0, "n_eps_claims": 3,
                        "n_eps_mismatches": 3,
                        "eps_mismatch_targets": ["s", "i", "r"]}
        if self.judge(all_mismatch).passed:
            return False

        partial = {"n_params": 3, "n_flat_params": 1,
                   "n_eps_claims": 3, "n_eps_mismatches": 1}
        if not self.judge(partial).passed:
            return False  # partial must NOT over-fire

        return True
