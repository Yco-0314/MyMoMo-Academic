"""Synthesis Phase — the DETERMINISTIC plumbing (ADR-015).

Bounded self-extension: when the Coverage Gate (ADR-014) finds a gap, can the
system synthesize a new operator and INTERNALIZE it autonomously? Only if an
INDEPENDENT, human-audited oracle passes the candidate — never on the
generator's word (ADR-012).

This module is the self-testable plumbing (no LLM; the LLM would draft the
candidate operator — here candidates are supplied directly so the gate logic
is provable). The trust law is STRUCTURAL: `attempt()` takes an oracle
*paradigm name* looked up in the audited `ORACLE_LIBRARY` — there is no
parameter for a caller-supplied oracle, so a generator cannot certify itself.

Regimes (ADR-015):
  verifiable gap (paradigm in the library)   → synthesize, verify, internalize
  unverifiable gap (no paradigm)             → propose for human audit; halt stands
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .coverage_gate import Mechanism
from .synthesis_oracles import REAL_ORACLES


def verify_in_subprocess(code: str, oracle_paradigm: str, *, timeout: float = 10.0,
                         sandbox_cmd: Optional[list] = None) -> bool:
    """Verify synthesized candidate CODE in an ISOLATED, timeout-bounded process
    (ADR-015 option B). The subprocess execs the candidate and runs the AUDITED
    oracle on it (so a candidate cannot supply its own judge); the parent reads
    only a PASS/FAIL string and NEVER execs untrusted code. A hang/crash/escape
    is contained by the separate process + the timeout-kill.

    ``sandbox_cmd`` prefixes the command with an OS sandbox (e.g.
    ``["firejail", "--net=none", "--private"]``) for untrusted input — a plain
    subprocess is isolation, not a hard security boundary.
    """
    cmd = list(sandbox_cmd or []) + [
        sys.executable, "-m", "abm_auto.codegen._synthesis_sandbox_runner", oracle_paradigm,
    ]
    # The runner must import abm_auto (for the audited oracle) regardless of cwd
    # (kept at a temp dir for fs isolation), so put the project root on PYTHONPATH.
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.pathsep.join(p for p in (project_root, os.environ.get("PYTHONPATH", "")) if p),
    }
    try:
        proc = subprocess.run(cmd, input=code, capture_output=True, text=True,
                              timeout=timeout, env=env, cwd=tempfile.gettempdir())
    except (subprocess.TimeoutExpired, Exception):
        return False
    return proc.stdout.strip().splitlines()[-1:] == ["PASS"]


# ── the human-audited oracle library: paradigm name -> known-answer oracle ──
# An oracle takes a CANDIDATE operator (a callable implementing the mechanism)
# and returns True iff it reproduces a KNOWN answer. The answer is independent
# of the candidate's implementation — that independence is what makes the
# oracle a real judge and not self-certification.

def _oracle_affine_recovery(candidate: Callable) -> bool:
    """Known answer: the candidate must implement x -> 2x + 1 on 0..4. A small,
    real, runnable oracle — enough to prove the plumbing genuinely gates.
    Real library entries (Kalman track-known-signal, tabular-Q solve-known-MDP,
    LP match-known-optimum) have the same shape: a fixed known answer."""
    try:
        return all(abs(candidate(x) - (2 * x + 1)) < 1e-9 for x in range(5))
    except Exception:
        return False


# Membership here is the trust frontier (audited, finite). Adding a paradigm is
# a human act; the agent extends only WITHIN this set. The real paradigms live
# in synthesis_oracles.py — each a known-answer test, self-tested against a
# reference-correct AND a reference-buggy candidate, so passing one is genuinely
# a verification.
ORACLE_LIBRARY: dict[str, Callable[[Any], bool]] = {
    "affine_recovery": _oracle_affine_recovery,    # the plumbing toy
    **REAL_ORACLES,                                 # tabular_q_learning / kalman_filter / linear_program
}


@dataclass
class SynthesisResult:
    outcome: str        # "internalized" | "rejected" | "proposed"
    mechanism: str
    detail: str


@dataclass
class SynthesisPhase:
    """Internalizes a synthesized operator only if an INDEPENDENT library
    oracle passes it. Detection-then-halt (ADR-014) stays the safe floor; this
    is the oracle-bounded addition on top."""

    oracles: dict = field(default_factory=lambda: dict(ORACLE_LIBRARY))
    internalized: dict = field(default_factory=dict)   # capability -> operator name

    def attempt(self, mechanism: Mechanism, candidate: Callable, *,
                oracle_paradigm: str) -> SynthesisResult:
        """Try to internalize a synthesized `candidate` operator for `mechanism`.

        The oracle is fetched from the audited library BY NAME. There is no
        parameter for a caller-supplied oracle — so a generator that drafts both
        the operator and 'its own test' cannot self-certify: an unaudited
        paradigm name simply isn't in the library, and the attempt is proposed,
        never internalized.
        """
        if oracle_paradigm not in self.oracles:
            return SynthesisResult(
                "proposed", mechanism.name,
                f"no audited oracle for {oracle_paradigm!r}; halt stands; "
                f"proposal (candidate + candidate oracle) emitted for human audit",
            )
        oracle = self.oracles[oracle_paradigm]          # from the library, not the caller
        if not oracle(candidate):
            return SynthesisResult(
                "rejected", mechanism.name,
                f"candidate failed the library oracle {oracle_paradigm!r}; NOT internalized",
            )
        operator_name = f"Synthesized_{mechanism.capability}"
        self.internalized[mechanism.capability] = operator_name
        return SynthesisResult(
            "internalized", mechanism.name,
            f"passed independent oracle {oracle_paradigm!r}; registered as {operator_name}",
        )

    def synthesize(self, mechanism: Mechanism, *, oracle_paradigm: str,
                   draft: Callable, max_tries: int = 4) -> SynthesisResult:
        """Bounded SEARCH (cf. DataMaster) — but pruned by our INDEPENDENT library
        oracle, not a benchmark the searcher optimizes (that would be
        self-certification). Draft a candidate, verify with the library oracle,
        retry-with-feedback on failure, internalize the FIRST that passes.

        ``draft(feedback)`` produces a candidate conforming to the paradigm's
        protocol; it is the ONLY drafter seam (a hand-written one in tests, the
        LLM later). Everything else — the oracle, the internalize gate — is
        deterministic. Unbudgeted search would be self-deception; the oracle and
        the try budget bound it.
        """
        if oracle_paradigm not in self.oracles:
            return SynthesisResult(
                "proposed", mechanism.name,
                f"no audited oracle for {oracle_paradigm!r}; halt stands; proposal "
                f"(candidate + candidate oracle) emitted for human audit",
            )
        oracle = self.oracles[oracle_paradigm]
        feedback = None
        for i in range(max(1, max_tries)):
            candidate = draft(feedback)
            if oracle(candidate):
                operator_name = f"Synthesized_{mechanism.capability}"
                self.internalized[mechanism.capability] = operator_name
                return SynthesisResult(
                    "internalized", mechanism.name,
                    f"passed independent oracle {oracle_paradigm!r} on try {i + 1}/"
                    f"{max_tries}; registered as {operator_name}",
                )
            feedback = f"candidate failed the {oracle_paradigm!r} oracle (try {i + 1})"
        return SynthesisResult(
            "rejected", mechanism.name,
            f"no candidate passed the {oracle_paradigm!r} oracle in {max_tries} "
            f"tries; NOT internalized (halt stands)",
        )

    def synthesize_sandboxed(self, mechanism: Mechanism, *, oracle_paradigm: str,
                             draft_code: Callable, max_tries: int = 4,
                             timeout: float = 10.0, sandbox_cmd=None) -> SynthesisResult:
        """Bounded search where the candidate is CODE, verified in an ISOLATED
        subprocess (ADR-015 option B) — the path for the LLM drafter, whose
        output is executed. Same trust law as ``synthesize``: only an audited
        paradigm is verifiable, the subprocess runs the AUDITED oracle (never a
        caller's), pass → internalize. ``draft_code(feedback)`` returns the
        candidate's Python source (defining ``build``)."""
        if oracle_paradigm not in REAL_ORACLES:
            return SynthesisResult(
                "proposed", mechanism.name,
                f"no audited sandbox oracle for {oracle_paradigm!r}; halt stands; "
                f"proposal for human audit",
            )
        feedback = None
        for i in range(max(1, max_tries)):
            code = draft_code(feedback)
            if verify_in_subprocess(code, oracle_paradigm, timeout=timeout,
                                    sandbox_cmd=sandbox_cmd):
                operator_name = f"Synthesized_{mechanism.capability}"
                self.internalized[mechanism.capability] = operator_name
                return SynthesisResult(
                    "internalized", mechanism.name,
                    f"passed audited oracle {oracle_paradigm!r} in a sandbox on try "
                    f"{i + 1}/{max_tries}; registered as {operator_name}",
                )
            feedback = f"candidate failed the sandboxed {oracle_paradigm!r} oracle (try {i + 1})"
        return SynthesisResult(
            "rejected", mechanism.name,
            f"no sandboxed candidate passed {oracle_paradigm!r} in {max_tries} tries; "
            f"NOT internalized",
        )

    def covers(self, mechanism: Mechanism) -> bool:
        """Re-gate: a mechanism is now operator-covered iff its capability was
        internalized this run. (In the pipeline the Coverage Gate consults this
        registry; the round-trip is proven here without coupling the gate.)"""
        return mechanism.capability in self.internalized


# ── self-test: the ADR-015 load-bearing fixtures. No LLM. ────────────────────

def self_test() -> bool:
    """Proves the plumbing AND the trust law:
      1. correct candidate + library oracle  -> internalized; re-gate covers.
      2. buggy candidate                      -> rejected; NOT internalized
                                                 (the oracle actually gates).
      3. no audited oracle (a GAN)            -> proposed; halt stands.
      4. self-certification (own paradigm)    -> proposed; never internalized
                                                 (no caller-oracle slot exists).
    """
    def good(x):  # the synthesized operator the LLM would draft, here correct
        return 2 * x + 1

    def buggy(x):
        return x

    gap = Mechanism("belief", "bayesian_filter")     # uncovered by the Coverage Gate

    # 1. happy path — autonomous, safe self-extension
    s1 = SynthesisPhase()
    r1 = s1.attempt(gap, good, oracle_paradigm="affine_recovery")
    if r1.outcome != "internalized" or not s1.covers(gap):
        return False

    # 2. buggy synthesis is caught by the independent oracle (load-bearing)
    s2 = SynthesisPhase()
    r2 = s2.attempt(gap, buggy, oracle_paradigm="affine_recovery")
    if r2.outcome != "rejected" or s2.covers(gap):
        return False

    # 3. unverifiable gap — proposal, no autonomous internalization
    s3 = SynthesisPhase()
    gan = Mechanism("conditional_gan", "generative_model")
    r3 = s3.attempt(gan, good, oracle_paradigm="adversarial_fidelity")
    if r3.outcome != "proposed" or s3.covers(gan):
        return False

    # 4. self-certification is structurally impossible (load-bearing): a
    #    "correct" candidate naming its OWN unaudited paradigm is still proposed.
    s4 = SynthesisPhase()
    r4 = s4.attempt(gap, good, oracle_paradigm="my_own_oracle")
    if r4.outcome != "proposed" or s4.covers(gap):
        return False

    return True
