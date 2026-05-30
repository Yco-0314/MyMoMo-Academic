"""Execution-based mechanism verifier — does sim BEHAVE as the story claims?

Today's verifier chain (dry_run / anti_pattern / contract / fidelity /
structural_fidelity / targets_alignment) looks at CODE. None look at
the trajectory the code actually produces.

This module bridges the gap. Two steps:

1. Extract qualitative direction-of-change claims from the story
   (LLM call — "S decreases? I peaks-then-decays? R rises monotonically?").

2. Classify the actual sim trajectory direction per target.

3. Diff. Any mismatch → fatal validator failure with clear feedback:
   "Story says S should decrease but your sim shows S monotonically
    increasing — check the spread direction in environment.step()."

Catches the class of bugs no current validator catches: code imports OK,
sim runs OK, MSE is plausible, but the mechanism semantics are wrong.
The Schelling dogfood today (slow GVR loop, eventual exit 0 with empty
calibration) is exactly the kind of failure this would have surfaced
clearly on iter 1 instead of cascading through 4+ retry cycles.

Design notes
------------
- The qualitative-claim extraction is ONE LLM call per pipeline run,
  cached on the workspace. Cheap.
- Direction classification is pure (no LLM): looks at first/last/peak.
- Mismatch reporting is structured so GVR can feed it back to
  CoderAgent specifically about which target's direction is wrong.
- Module is standalone — wire via a new Phase later, or call from
  PreRunSanityPhase, or as a CodegenPhase validator. The verifier
  itself doesn't care about Pipeline integration.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd


# Direction labels — small closed set the LLM picks from
DIRECTION_LABELS = (
    "monotonic_decrease",
    "monotonic_increase",
    "peak_then_decay",
    "valley_then_recover",
    "stable",
    "unclear",
)


@dataclass
class QualitativeClaim:
    """One direction-of-change claim about a target column."""
    target: str
    direction: str         # one of DIRECTION_LABELS
    rationale: str = ""    # LLM's brief explanation


@dataclass
class TrajectoryClassification:
    """Classification of an actual sim trajectory."""
    target: str
    direction: str         # one of DIRECTION_LABELS
    peak_ratio: float      # peak / final, useful for diagnostic
    monotonicity: float    # fraction of increasing pairs


@dataclass
class VerificationResult:
    """Output of verify_execution — full diff between claims and reality."""
    claims: list[QualitativeClaim]
    actuals: list[TrajectoryClassification]
    mismatches: list[tuple[str, str, str]] = field(default_factory=list)
    # (target, expected_direction, actual_direction)

    @property
    def is_valid(self) -> bool:
        return len(self.mismatches) == 0

    def feedback(self) -> list[str]:
        """Structured reasons for GVR feedback to CoderAgent."""
        out: list[str] = []
        for target, expected, actual in self.mismatches:
            out.append(
                f"`{target}` direction mismatch: story says "
                f"`{expected}` but sim produces `{actual}`. Check the "
                f"calculation in environment.step() — likely an inverted "
                f"sign, missing update, or wrong target attribute."
            )
        return out


# ─────────────────────────────────────────────────────────────────────────
# Trajectory classification (pure — no LLM, no I/O beyond reading the CSV)
# ─────────────────────────────────────────────────────────────────────────


def classify_trajectory(
    series: np.ndarray,
    stable_rel_tol: float = 0.05,
    peak_dominance_ratio: float = 1.5,
) -> TrajectoryClassification:
    """Pure direction classifier for one numeric series.

    Strategy (in order, first match wins):
    1. If max-min < stable_rel_tol × max → `stable`
    2. If peak/final > peak_dominance_ratio AND argmax in middle 80% → `peak_then_decay`
    3. If trough/final < 1/peak_dominance_ratio AND argmin in middle 80% → `valley_then_recover`
    4. Else compute monotonicity:
       - > 0.85 increasing → `monotonic_increase`
       - < 0.15 increasing → `monotonic_decrease`
       - else → `unclear`
    """
    arr = np.asarray(series, dtype=float)
    n = len(arr)
    if n < 2:
        return TrajectoryClassification(
            target="?", direction="unclear", peak_ratio=1.0, monotonicity=0.0,
        )

    rng = arr.max() - arr.min()
    if rng < stable_rel_tol * max(abs(arr.max()), 1e-9):
        return TrajectoryClassification(
            target="?", direction="stable",
            peak_ratio=1.0,
            monotonicity=0.5,
        )

    peak_idx = int(np.argmax(arr))
    trough_idx = int(np.argmin(arr))
    final_val = arr[-1] if arr[-1] != 0 else 1e-9

    peak_ratio = float(arr[peak_idx] / final_val) if final_val > 0 else 1.0

    # peak_then_decay: peak in middle 80%, peak/final large, AND the
    # post-peak section shows actual decay (not just random noise).
    # The post-peak monotonicity check is what distinguishes a real
    # epidemic curve from a random walk that happens to peak in the
    # interior — noisy random data passed every other check and was
    # mislabeled as peak_then_decay before this guard.
    in_middle = lambda idx: 0.1 * n < idx < 0.9 * n
    post_peak_decay_share = 0.0
    pre_peak_rise_share = 0.0
    if peak_idx >= 2:
        pre_diffs = np.diff(arr[: peak_idx + 1])
        pre_peak_rise_share = float(np.sum(pre_diffs > 0)) / max(len(pre_diffs), 1)
    if peak_idx < n - 2:
        post_diffs = np.diff(arr[peak_idx:])
        post_peak_decay_share = float(np.sum(post_diffs < 0)) / max(len(post_diffs), 1)
    if (arr[peak_idx] > 0 and final_val > 0 and
            arr[peak_idx] / max(final_val, 1e-9) > peak_dominance_ratio and
            in_middle(peak_idx) and
            pre_peak_rise_share >= 0.6 and
            post_peak_decay_share >= 0.6):
        return TrajectoryClassification(
            target="?", direction="peak_then_decay",
            peak_ratio=peak_ratio,
            monotonicity=_fraction_increasing(arr),
        )

    post_trough_recovery_share = 0.0
    pre_trough_fall_share = 0.0
    if trough_idx >= 2:
        pre_diffs = np.diff(arr[: trough_idx + 1])
        pre_trough_fall_share = float(np.sum(pre_diffs < 0)) / max(len(pre_diffs), 1)
    if trough_idx < n - 2:
        post_diffs = np.diff(arr[trough_idx:])
        post_trough_recovery_share = float(np.sum(post_diffs > 0)) / max(len(post_diffs), 1)
    if (arr[trough_idx] >= 0 and final_val > 0 and
            final_val / max(arr[trough_idx], 1e-9) > peak_dominance_ratio and
            in_middle(trough_idx) and
            pre_trough_fall_share >= 0.6 and
            post_trough_recovery_share >= 0.6):
        return TrajectoryClassification(
            target="?", direction="valley_then_recover",
            peak_ratio=peak_ratio,
            monotonicity=_fraction_increasing(arr),
        )

    frac_inc = _fraction_increasing(arr)
    if frac_inc > 0.85:
        return TrajectoryClassification(
            target="?", direction="monotonic_increase",
            peak_ratio=peak_ratio, monotonicity=frac_inc,
        )
    if frac_inc < 0.15:
        return TrajectoryClassification(
            target="?", direction="monotonic_decrease",
            peak_ratio=peak_ratio, monotonicity=frac_inc,
        )
    return TrajectoryClassification(
        target="?", direction="unclear",
        peak_ratio=peak_ratio, monotonicity=frac_inc,
    )


def _fraction_increasing(arr: np.ndarray) -> float:
    """Fraction of adjacent pairs where arr[i+1] > arr[i]."""
    if len(arr) < 2:
        return 0.5
    diffs = np.diff(arr)
    n_inc = int(np.sum(diffs > 0))
    n_total = len(diffs)
    return n_inc / n_total if n_total else 0.5


def classify_trajectory_csv(csv_path: Path, targets: list[str]) -> list[TrajectoryClassification]:
    """Read sim output CSV + classify each target column."""
    df = pd.read_csv(csv_path)
    out: list[TrajectoryClassification] = []
    for target in targets:
        if target not in df.columns:
            out.append(TrajectoryClassification(
                target=target, direction="unclear",
                peak_ratio=1.0, monotonicity=0.5,
            ))
            continue
        series = pd.to_numeric(df[target], errors="coerce").fillna(0.0).values
        cls = classify_trajectory(series)
        cls.target = target
        out.append(cls)
    return out


# ─────────────────────────────────────────────────────────────────────────
# Qualitative claim extraction (LLM call — orchestrator-injected)
# ─────────────────────────────────────────────────────────────────────────


_CLAIM_SYSTEM = (
    "You are an ABM domain expert. Read a research story and identify the "
    "qualitative direction each output target column should follow over time. "
    "Output ONLY valid JSON matching the schema, no other text."
)

_CLAIM_USER_TEMPLATE = """\
## Research story

{story}

## Output targets

{targets_list}

## Task

For each target column, what direction does it move over the simulation?
Pick EXACTLY ONE from:

  - monotonic_decrease   (always going down, e.g. susceptible in SIR)
  - monotonic_increase   (always going up, e.g. resistant in SIR)
  - peak_then_decay      (rises then falls, e.g. infected in SIR)
  - valley_then_recover  (falls then rises, less common)
  - stable               (no significant change, e.g. mean_opinion in symmetric Deffuant)
  - unclear              (story doesn't say or it's not deterministic)

Output JSON:

```json
{{
  "claims": [
    {{"target": "<exact column name>", "direction": "<one of labels above>", "rationale": "<1 line>"}},
    ...
  ]
}}
```

Use the EXACT column names from the targets list. Be conservative — pick
"unclear" rather than guessing.
"""


def extract_qualitative_claims(
    story_text: str,
    targets: list[str],
    llm_caller: Callable[..., str],
) -> list[QualitativeClaim]:
    """One LLM call: read story.md, identify direction per target.

    `llm_caller` matches BaseAgent.call_llm(system, user, max_tokens, model=None)
    — typically passed as `agent.call_llm`. The caller controls which model
    is used (recommend deepseek-chat / fast model — this is a structured-
    extraction call, doesn't need reasoning).

    Returns empty list on parse failure (verifier downstream then no-ops —
    skipping verification is preferable to halting on a parse error).
    """
    if not targets:
        return []
    targets_list = "\n".join(f"- `{t}`" for t in targets)
    user = _CLAIM_USER_TEMPLATE.format(story=story_text[:6000], targets_list=targets_list)
    try:
        raw = llm_caller(_CLAIM_SYSTEM, user, max_tokens=800)
    except Exception:
        return []

    # Extract JSON block (forgiving of markdown code fence)
    match = re.search(r"```json\s*\n(.*?)\n```", raw, re.DOTALL)
    if match:
        block = match.group(1).strip()
    else:
        block = raw.strip()
    try:
        data = json.loads(block)
    except json.JSONDecodeError:
        return []

    claims = []
    for entry in data.get("claims", []):
        target = entry.get("target", "")
        direction = entry.get("direction", "")
        if not target or direction not in DIRECTION_LABELS:
            continue
        claims.append(QualitativeClaim(
            target=target,
            direction=direction,
            rationale=entry.get("rationale", ""),
        ))
    return claims


# ─────────────────────────────────────────────────────────────────────────
# Top-level: verify_execution (composes the two above)
# ─────────────────────────────────────────────────────────────────────────


def verify_execution(
    story_text: str,
    sim_csv: Path,
    targets: list[str],
    llm_caller: Callable[..., str],
) -> VerificationResult:
    """Full verification: extract claims, classify sim, diff.

    `llm_caller` only invoked once (for claim extraction). Classification
    is pure. Returns VerificationResult with .is_valid + .feedback().
    """
    claims = extract_qualitative_claims(story_text, targets, llm_caller)
    actuals = classify_trajectory_csv(sim_csv, targets)
    return diff_claims_vs_actuals(claims, actuals)


def diff_claims_vs_actuals(
    claims: list[QualitativeClaim],
    actuals: list[TrajectoryClassification],
) -> VerificationResult:
    """Compute mismatches. Pure — no LLM, no I/O."""
    claim_map = {c.target: c.direction for c in claims}
    actual_map = {a.target: a.direction for a in actuals}
    mismatches: list[tuple[str, str, str]] = []
    for target, expected in claim_map.items():
        if expected == "unclear":
            continue   # LLM had no claim → can't verify
        actual = actual_map.get(target, "unclear")
        if actual == "unclear":
            continue   # sim trajectory couldn't be classified → skip
        if expected != actual:
            mismatches.append((target, expected, actual))
    return VerificationResult(
        claims=claims,
        actuals=actuals,
        mismatches=mismatches,
    )


__all__ = [
    "DIRECTION_LABELS",
    "QualitativeClaim",
    "TrajectoryClassification",
    "VerificationResult",
    "classify_trajectory",
    "classify_trajectory_csv",
    "extract_qualitative_claims",
    "verify_execution",
    "diff_claims_vs_actuals",
]
