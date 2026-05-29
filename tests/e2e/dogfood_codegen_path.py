"""Dogfood the full pipeline through the CODEGEN path (no --external-model).

Why this exists
---------------
Most of today's benchmarks bypass codegen by passing --external-model. That
proves the CALIBRATION side of the pipeline works but says nothing about
whether the full "story → working model → calibrated → report" promise
actually delivers for users who *don't* have a handcrafted simulator.

This script runs the full pipeline on the BEHAVE 2025 virus story without
--external-model, captures stdout + workspace artifacts, computes 14
metrics across codegen health / pipeline health / calibration health /
UX, and writes a diagnostic markdown report.

Usage:
    python tests/e2e/dogfood_codegen_path.py [--story path] [--iterations N]

The script is intentionally permissive — it does NOT fix bugs encountered
during the run. The point is to OBSERVE what fails, where the experience
degrades, what surprises us. Fixes live in separate work guided by the
diagnostic report.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

REPO = Path(__file__).parent.parent.parent
DEFAULT_STORY = REPO / "examples" / "calibration_challenge_virus" / "story.md"
DEFAULT_OBSERVED = REPO / "examples" / "calibration_challenge_virus" / "observed.csv"
DEFAULT_GROUND_TRUTH = {
    "virus_spread_chance": 4.4,
    "recovery_chance": 2.5,
    "gain_resistance_chance": 25.0,
}


def run_pipeline(
    story: Path,
    iterations: int,
    workspace_name: str,
    observed: Optional[Path] = None,
) -> tuple[int, str, str, float]:
    """Invoke `python -m abm_auto.cli run` as a subprocess. Return (exit_code, stdout, stderr, wall_seconds)."""
    cmd = [
        sys.executable, "-u", "-m", "abm_auto.cli", "run",
        str(story),
        "--iterations", str(iterations),
        "--mode", "reproduce",
        "--no-lit-review",
        "--workspace", workspace_name,
    ]
    if observed:
        cmd += ["--observed", str(observed)]
    print(f"$ {' '.join(cmd)}", flush=True)
    t0 = time.time()
    result = subprocess.run(
        cmd, cwd=REPO,
        capture_output=True, text=True,
        env={**__import__("os").environ},
    )
    wall = time.time() - t0
    return result.returncode, result.stdout, result.stderr, wall


def count_llm_calls(stdout: str) -> dict[str, int]:
    """Count LLM API invocations by model from log lines '→ LLM (model=..., ...)'."""
    matches = re.findall(r"→ LLM \(([a-zA-Z0-9._-]+)", stdout)
    return dict(Counter(matches))


def count_gvr_attempts(stdout: str) -> dict[str, int]:
    """Count GVR refine() retries by actor."""
    # GVR audit emits lines like "GVR <actor>: initial attempt" / "GVR <actor>: retry 1 of N"
    attempts = re.findall(r"GVR ([A-Za-z]+)(?:Viability)?: (initial attempt|retry)", stdout)
    counter: Counter = Counter()
    for actor, _kind in attempts:
        counter[actor] += 1
    return dict(counter)


def count_phase_completions(stdout: str) -> list[str]:
    """Extract the sequence of phases that ran (by their log headers)."""
    return re.findall(r"Phase [\-0-9.a-z]+[a-z]?\b", stdout)


def detect_anti_pattern_hits(stdout: str, audit_path: Optional[Path]) -> list[str]:
    """Find anti_pattern validator firings in stdout + audit ledger."""
    hits = []
    for line in stdout.splitlines():
        if "anti_pattern" in line.lower() or "hallucinated" in line.lower() or "Removed API" in line:
            hits.append(line.strip()[:200])
    if audit_path and audit_path.exists():
        try:
            for line in audit_path.read_text(encoding="utf-8").splitlines():
                if "anti_pattern" in line.lower() or "hallucinat" in line.lower():
                    hits.append(line.strip()[:200])
        except Exception:
            pass
    return hits


def detect_pipeline_halted(stdout: str) -> Optional[str]:
    """Was the pipeline halted? Return the halt reason or None."""
    m = re.search(r"Pipeline halted: (.+?)(?:\n|$)", stdout)
    return m.group(1) if m else None


def find_workspace(stdout: str, workspace_name: str) -> Optional[Path]:
    """Locate the workspace dir from stdout or by name lookup."""
    m = re.search(r"Workspace: (\S+)", stdout)
    if m:
        p = Path(m.group(1))
        if p.exists():
            return p
    # Fallback: look up by name
    candidate = REPO / "workspace" / workspace_name
    if candidate.exists():
        return candidate
    return None


def score_mse(observed: Path, simulated: Path) -> Optional[float]:
    """Score final-sim trajectory against observed via score_calibration_mse."""
    try:
        sys.path.insert(0, str(REPO))
        from benchmark_calibration_challenge import score_calibration_mse
        res = score_calibration_mse(observed, simulated)
        return res.get("aggregate_mse")
    except Exception as e:
        print(f"  MSE scoring failed: {e}", flush=True)
        return None


def estimate_api_cost_usd(llm_calls: dict[str, int]) -> float:
    """Rough USD cost estimate. DeepSeek pricing: ~$0.27/M input, ~$1.10/M output (2026)."""
    # Per-call rough averages (input tokens dominate; outputs typically 500-2000)
    avg_input_tokens = 4000
    avg_output_tokens = 1000
    cost_per_call = (avg_input_tokens * 0.27 + avg_output_tokens * 1.10) / 1_000_000
    return sum(llm_calls.values()) * cost_per_call


def collect_metrics(
    workspace: Path,
    stdout: str,
    stderr: str,
    wall: float,
    exit_code: int,
    observed_path: Path = DEFAULT_OBSERVED,
) -> dict[str, Any]:
    """Compute the 14 metrics for the report.

    `observed_path` is the file to score the final-sim trajectory against.
    Must match the observed.csv that was passed to the pipeline (cross-domain
    dogfoods would silently score against the wrong domain otherwise).
    """
    audit_path = workspace / "audit_ledger.jsonl" if workspace else None
    best_params_path = workspace / "best_params.json" if workspace else None
    final_sim_path = workspace / "calibration_final_sim.csv" if workspace else None
    report_path = workspace / "report.md" if workspace else None
    ars_dir = workspace / "research-output" if workspace else None

    llm_calls = count_llm_calls(stdout)
    gvr = count_gvr_attempts(stdout)
    anti_pattern_hits = detect_anti_pattern_hits(stdout, audit_path)
    halt_reason = detect_pipeline_halted(stdout)
    phases_seen = count_phase_completions(stdout)

    best_params = None
    if best_params_path and best_params_path.exists():
        try:
            best_params = json.loads(best_params_path.read_text())
        except Exception:
            pass

    mse = None
    if final_sim_path and final_sim_path.exists():
        # Score against the story-resolved observed.csv (cross-domain safety)
        mse = score_mse(observed_path, final_sim_path)

    rel_errs = None
    if best_params:
        rel_errs = {
            k: abs(best_params.get(k, 0) - v) / v * 100
            for k, v in DEFAULT_GROUND_TRUTH.items() if v != 0
        }

    return {
        # Codegen health
        "anti_pattern_hits": anti_pattern_hits,
        "gvr_retries": gvr,
        "halt_reason": halt_reason,
        "phases_completed": phases_seen,
        # Calibration health
        "best_params": best_params,
        "ground_truth": DEFAULT_GROUND_TRUTH,
        "rel_errs_pct": rel_errs,
        "mse": mse,
        # UX
        "wall_seconds": wall,
        "llm_calls_by_model": llm_calls,
        "llm_calls_total": sum(llm_calls.values()),
        "est_cost_usd": estimate_api_cost_usd(llm_calls),
        "exit_code": exit_code,
        "report_exists": bool(report_path and report_path.exists()),
        "report_chars": (report_path.read_text(encoding="utf-8").__len__() if report_path and report_path.exists() else 0),
        "ars_package_exists": bool(ars_dir and ars_dir.exists()),
        "stderr_preview": stderr[:1000],
        "workspace": str(workspace) if workspace else None,
    }


def render_report(metrics: dict[str, Any]) -> str:
    """Render the diagnostic markdown report."""
    bp = metrics.get("best_params") or {}
    gt = metrics["ground_truth"]
    rel = metrics.get("rel_errs_pct") or {}
    mse = metrics.get("mse")
    mse_str = f"{mse:.1f}" if mse is not None else "—"
    halt = metrics.get("halt_reason") or "(none)"
    anti_pattern_count = len(metrics.get("anti_pattern_hits") or [])
    llm_total = metrics.get("llm_calls_total", 0)
    cost = metrics.get("est_cost_usd", 0)

    lines = [
        "# Dogfood report: codegen path on BEHAVE 2025 virus story",
        "",
        f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}  ",
        f"**Story**: `examples/calibration_challenge_virus/story.md`  ",
        f"**Mode**: reproduce (no --external-model — full codegen path)  ",
        f"**Iterations**: 2  ",
        f"**Workspace**: `{metrics.get('workspace', 'unknown')}`",
        "",
        "## TL;DR",
        "",
        f"- Exit code: **{metrics['exit_code']}**",
        f"- Wall time: **{metrics['wall_seconds']:.0f}s** ({metrics['wall_seconds']/60:.1f} min)",
        f"- LLM calls: **{llm_total}** (est. **${cost:.2f}** at DeepSeek pricing)",
        f"- Calibration MSE: **{mse_str}** (external-model baseline ≈ 100 ± 60)",
        f"- Halt: {halt}",
        "",
        "## Metrics",
        "",
        "### Codegen health",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Anti-pattern validator hits | **{anti_pattern_count}** |",
        f"| Pipeline halted? | {halt} |",
        f"| Phases logged | {len(metrics.get('phases_completed') or [])} occurrences |",
        f"| GVR retries by actor | `{metrics.get('gvr_retries') or '(none)'}` |",
        "",
        "### Calibration health",
        "",
        f"| Parameter | Truth | Got | Rel. err |",
        f"|---|---|---|---|",
    ]
    for k, v in gt.items():
        got = bp.get(k)
        got_str = f"{got:.3f}" if isinstance(got, (int, float)) else "—"
        err = rel.get(k)
        err_str = f"{err:.1f}%" if err is not None else "—"
        lines.append(f"| `{k}` | {v} | {got_str} | {err_str} |")
    lines += [
        "",
        f"**Aggregate MSE**: {mse_str}  ",
        f"**Floor estimate** (from ADR-006): 100-200  ",
        f"**External-model baseline** (commit 3c3c15c): 99 ± 59",
        "",
        "### UX",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Wall time | {metrics['wall_seconds']:.0f}s ({metrics['wall_seconds']/60:.1f} min) |",
        f"| LLM calls total | {llm_total} |",
        f"| LLM calls by model | `{metrics.get('llm_calls_by_model') or '(none)'}` |",
        f"| Estimated USD cost | ${cost:.2f} |",
        f"| Report generated? | {metrics['report_exists']} ({metrics['report_chars']:,} chars) |",
        f"| ARS package? | {metrics['ars_package_exists']} |",
        "",
    ]

    if anti_pattern_count:
        lines += ["### Anti-pattern hits (first 10)", ""]
        for h in (metrics.get("anti_pattern_hits") or [])[:10]:
            lines.append(f"- `{h}`")
        lines.append("")

    if metrics.get("stderr_preview"):
        lines += [
            "### stderr preview",
            "",
            "```",
            metrics["stderr_preview"],
            "```",
            "",
        ]

    lines += [
        "## Friction inventory",
        "",
        "_Subjective observations from running this end-to-end. Each item is a candidate for architectural deepening or a bug to file._",
        "",
        "TODO: fill in after observing run.",
        "",
    ]
    return "\n".join(lines)


def _resolve_observed(story: Path, explicit: Optional[Path]) -> Path:
    """Auto-resolve observed.csv from story dir if not explicitly passed.

    Without this, cross-domain dogfoods (Opinion / Schelling) silently
    scored against virus observed.csv → garbage MSE. The CLI's --observed
    flag works; this just makes the default sensible per-story.
    """
    if explicit is not None and explicit != DEFAULT_OBSERVED:
        return explicit
    story_observed = story.parent / "observed.csv"
    if story_observed.exists():
        return story_observed
    return DEFAULT_OBSERVED


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", type=Path, default=DEFAULT_STORY)
    ap.add_argument("--iterations", type=int, default=2)
    ap.add_argument("--observed", type=Path, default=None,
                    help="Passed through to --observed CLI flag. Auto-resolved "
                         "from <story.parent>/observed.csv when omitted.")
    ap.add_argument("--report", type=Path, default=REPO / "docs" / "dogfood" / f"{time.strftime('%Y-%m-%d')}-codegen-path-virus.md")
    args = ap.parse_args()
    args.observed = _resolve_observed(args.story, args.observed)

    workspace_name = f"dogfood_codegen_{int(time.time())}"
    print(f"=== Dogfood codegen path ===")
    print(f"Story:     {args.story}")
    print(f"Workspace: {workspace_name}")
    print(f"Report:    {args.report}")
    print()

    exit_code, stdout, stderr, wall = run_pipeline(
        args.story, args.iterations, workspace_name, observed=args.observed,
    )
    print(f"\n[wall {wall:.0f}s, exit {exit_code}]")

    workspace = find_workspace(stdout, workspace_name)
    if not workspace:
        print("ERROR: could not locate workspace dir")
        # Still emit a report with what we have
        metrics = collect_metrics(None, stdout, stderr, wall, exit_code, observed_path=args.observed)
    else:
        metrics = collect_metrics(workspace, stdout, stderr, wall, exit_code, observed_path=args.observed)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(metrics), encoding="utf-8")
    # Save raw stdout for later forensics
    raw_path = args.report.with_suffix(".stdout.txt")
    raw_path.write_text(stdout, encoding="utf-8")
    print(f"\n→ Report:        {args.report}")
    print(f"→ Raw stdout:    {raw_path}")
    print(f"→ Workspace:     {workspace}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
