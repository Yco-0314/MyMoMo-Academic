"""
Generate-Validate-Refine (GVR) loop.

A small, pure-function module that turns any (generator, validator) pair
into a self-healing retry loop with structured feedback.

Why this exists:
  Before GVR, VerifierAgent was the *only* place in the pipeline that did
  "produce output → check it → on failure, give feedback and try again".
  Every other phase was "one-shot, halt on first failure" — which made
  pipeline runs 50%+ flaky against a non-deterministic LLM. Benchmark runs
  on the SIR-on-network calibration challenge confirmed the pattern: same story.md,
  consecutive runs failed at different phases purely because of LLM noise.

  GVR makes that pattern a first-class module. Two adapters at launch:
    1. DesignAgent + ViabilityChecker  (new — closes a frequently-failing gate)
    2. CoderAgent + VerifierAgent      (refactor — proves the abstraction works
                                         on a fundamentally different case:
                                         deterministic execution-error feedback
                                         vs. LLM-judge semantic feedback)

Design decisions (from grilling, 2026-05-25):
  - Decision A: Validator can mix deterministic rules + optional LLM judge (A3)
  - Decision B: Feedback is free-text strings, not typed schemas (B1, simplest)
  - Decision C: Caller decides exhaustion policy; default = continue with best
                attempt + write BLOCKING audit event (C3 default C2)
  - Decision D: refine() is a free-standing function, not bolted onto agents (D3)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional

from rich.console import Console

console = Console()


# ── Types ───────────────────────────────────────────────────────────────────


@dataclass
class ValidationOutcome:
    """Result of validating a single generated artifact.

    A validator (deterministic check, LLM judge, or hybrid) returns this.
    """
    ok: bool                                  # True if the artifact is accepted
    reasons: list[str] = field(default_factory=list)  # human-readable failures
    severity: Literal["fatal", "soft"] = "soft"        # fatal = must halt; soft = best-effort OK
    structured: dict[str, Any] = field(default_factory=dict)  # for B2 upgrade later

    def to_feedback(self) -> str:
        """Render this single outcome as feedback text.

        Note: refine() no longer calls this directly (uses build_cumulative_feedback
        instead, which folds in the full history). Kept for external callers and
        backwards-compat tests.
        """
        if not self.reasons:
            return "Previous attempt was rejected (no specific reason given)."
        bullets = "\n".join(f"  - {r}" for r in self.reasons)
        return f"Previous attempt was rejected for these reasons:\n{bullets}"


@dataclass
class Attempt:
    """A single iteration in a refinement loop."""
    iteration: int                 # 1-indexed
    artifact: Any                  # what the generator produced
    outcome: ValidationOutcome
    feedback_used: Optional[str]   # the feedback that was fed INTO this attempt (None for iter 1)


@dataclass
class RefinementResult:
    """Outcome of an entire refine() call."""
    accepted: bool                 # validator returned ok=True at some iteration
    artifact: Any                  # the final artifact (best-so-far if not accepted)
    attempts: list[Attempt]        # full history
    exhausted: bool                # True if max_iters reached without acceptance

    @property
    def n_attempts(self) -> int:
        return len(self.attempts)


# Type aliases for the (generator, validator) callable shapes.
# Generator: takes optional feedback (None on first attempt), returns an artifact.
Generator = Callable[[Optional[str]], Any]
# Validator: takes an artifact, returns a ValidationOutcome.
Validator = Callable[[Any], ValidationOutcome]


# ── Cumulative feedback (anti-oscillation) ───────────────────────────────────


def build_cumulative_feedback(
    failed_attempts: list["Attempt"],
    max_reason_chars: int = 600,
) -> str:
    """Render the full failure history as feedback for the next attempt.

    Why this exists:
        The original `ValidationOutcome.to_feedback()` only described the LAST
        failure. The generator (typically an LLM) had no way to know that iter 3
        was about to repeat the same fix that iter 1 or 2 already tried.
        Result: oscillation between equivalent wrong answers (e.g. the verifier
        flipping between two hallucinated column names across 5 retries).

        This function pushes the full history into the next-attempt feedback,
        plus an explicit "do not repeat" directive. The Generator interface
        stays unchanged — only the contents of the string it receives gets
        richer.

    Args:
        failed_attempts: every Attempt that has failed so far (most recent last).
        max_reason_chars: per-attempt truncation cap to keep context manageable.

    Returns:
        Multi-line string. Empty when there are no failed attempts.
    """
    if not failed_attempts:
        return ""

    # Single failure: fall back to the simple message (no "do not repeat" yet)
    if len(failed_attempts) == 1:
        return failed_attempts[0].outcome.to_feedback()

    lines: list[str] = [
        f"This is attempt {len(failed_attempts) + 1}. "
        f"ALL {len(failed_attempts)} previous attempts failed:",
        "",
    ]
    for a in failed_attempts:
        reasons_text = "; ".join(a.outcome.reasons) if a.outcome.reasons else "(no reason)"
        if len(reasons_text) > max_reason_chars:
            reasons_text = reasons_text[:max_reason_chars] + "... (truncated)"
        lines.append(f"  Attempt {a.iteration} — failed:")
        lines.append(f"    {reasons_text}")
        lines.append("")

    lines.append(
        "⚠ DO NOT repeat any approach that produced the failures above. "
        "If the same root cause keeps recurring, the previous fixes were not "
        "addressing it — try a fundamentally different angle. "
        "If you cannot find a different fix, state explicitly what makes this "
        "unsolvable rather than re-trying a failed approach."
    )
    return "\n".join(lines)


# ── Main function ────────────────────────────────────────────────────────────


def refine(
    generator: Generator,
    validator: Validator,
    max_iters: int = 3,
    on_exhaust: Literal["halt", "continue_best"] = "continue_best",
    audit: Optional[Any] = None,    # AuditLedger or None
    actor: str = "refine",
    phase: str = "",
    verbose: bool = True,
) -> RefinementResult:
    """Generate → validate → feedback → retry until pass or exhausted.

    Args:
        generator: produces an artifact; takes feedback from previous failure
                   (None on first iteration).
        validator: checks the artifact; returns ValidationOutcome.
        max_iters: hard upper bound on (generate, validate) iterations.
        on_exhaust: what RefinementResult to return if no iteration accepts.
                    "halt"          — caller must check `.accepted` and stop
                    "continue_best" — same return shape but pipeline normally
                                      proceeds with `.artifact` (which is the
                                      best-so-far attempt). Caller writes
                                      audit event on exhaustion.
        audit: optional AuditLedger; refine writes one INFO per attempt + one
               BLOCKING on exhaustion.
        actor: name attached to audit events.
        phase: phase label for audit events.
        verbose: print iteration progress to console.

    Returns:
        RefinementResult — caller inspects `.accepted` and `.artifact`.
    """
    if max_iters < 1:
        raise ValueError(f"max_iters must be ≥ 1, got {max_iters}")

    attempts: list[Attempt] = []
    feedback: Optional[str] = None

    for i in range(1, max_iters + 1):
        if verbose:
            label = "initial attempt" if i == 1 else f"refine attempt {i}/{max_iters}"
            console.print(f"  [dim]GVR {actor}: {label}[/dim]")

        # Generate
        artifact = generator(feedback)

        # Validate
        outcome = validator(artifact)

        attempt = Attempt(
            iteration=i, artifact=artifact, outcome=outcome,
            feedback_used=feedback,
        )
        attempts.append(attempt)

        # Audit per-attempt info
        if audit is not None:
            try:
                audit.info(
                    phase=phase,
                    text=(
                        f"GVR iter {i}/{max_iters}: "
                        f"{'PASS' if outcome.ok else 'FAIL'}"
                        + (f" ({len(outcome.reasons)} reason(s))" if not outcome.ok else "")
                    ),
                    actor=actor,
                    structured={
                        "iteration": i,
                        "ok": outcome.ok,
                        "severity": outcome.severity,
                        "n_reasons": len(outcome.reasons),
                    },
                )
            except Exception:
                pass

        if outcome.ok:
            # Accepted — stop early
            if verbose:
                console.print(
                    f"  [green]GVR {actor}: accepted at iter {i}/{max_iters}[/green]"
                )
            return RefinementResult(
                accepted=True, artifact=artifact, attempts=attempts, exhausted=False,
            )

        # Build CUMULATIVE feedback for next iter — includes full failure history,
        # not just this attempt's outcome. Fixes the "LLM oscillation" failure
        # mode where the generator (amnesic across iterations) repeatedly tries
        # the same wrong fix because it doesn't know it was already attempted.
        feedback = build_cumulative_feedback(attempts)
        if verbose and i < max_iters:
            short_reason = outcome.reasons[0][:80] if outcome.reasons else "(no reason)"
            console.print(f"  [yellow]GVR {actor}: iter {i} failed → {short_reason}[/yellow]")

    # Exhausted
    best = _pick_best(attempts)
    if audit is not None:
        try:
            audit.raise_issue(
                phase=phase,
                severity="HIGH",
                text=(
                    f"GVR exhausted after {max_iters} attempts; "
                    f"falling back to best-so-far (iter {best.iteration})"
                    if on_exhaust == "continue_best"
                    else f"GVR exhausted after {max_iters} attempts; HALT requested"
                ),
                actor=actor,
                structured={
                    "max_iters": max_iters,
                    "on_exhaust": on_exhaust,
                    "best_iteration": best.iteration,
                    "best_reasons_count": len(best.outcome.reasons),
                },
            )
        except Exception:
            pass

    if verbose:
        console.print(
            f"  [red]GVR {actor}: exhausted ({max_iters} attempts); "
            f"falling back to iter {best.iteration} (best-so-far)[/red]"
        )

    return RefinementResult(
        accepted=False, artifact=best.artifact, attempts=attempts, exhausted=True,
    )


def _pick_best(attempts: list[Attempt]) -> Attempt:
    """Choose the "best" attempt from a refinement history.

    Heuristic: fewest validation reasons wins. Ties broken by latest iteration
    (assumption: refinement makes things better on average, so later attempts
    are slightly preferred).
    """
    return min(
        attempts,
        key=lambda a: (len(a.outcome.reasons), -a.iteration),
    )
