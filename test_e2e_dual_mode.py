"""
End-to-end verification of the dual-mode pipeline plumbing.

Runs Phase -1 → 0 → 0.5 → 1 → 1c for two stories:
  1. A reproduce-mode story (El Farol 1994) — should skip HypothesisAgent
  2. An originate-mode story (custom phenomenon) — should run HypothesisAgent

For each, verifies:
  - research_spec.json written with correct mode
  - hypothesis.md present iff originate mode
  - DESIGN.md created
  - audit_ledger.jsonl + audit_ledger.md exist with sensible content
  - ViabilityChecker thresholds differ between modes

Skips: LitReviewer (network calls), Phase 2+ (code gen + sim — slow).
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from abm_auto import config
from abm_auto.llm import make_client
from abm_auto.runner.workspace import Workspace
from abm_auto.agents.mode_detector import ModeDetector
from abm_auto.agents.hypothesis_agent import HypothesisAgent
from abm_auto.agents.designer import DesignAgent
from abm_auto.agents.viability_checker import ViabilityChecker

console = Console()


ORIGINATE_STORY = """# Phenomenon: Cascading Trust Collapse in Online Marketplaces

## What I want to model

I've been observing that on platforms like eBay and Taobao, small fluctuations
in seller trust scores can sometimes cascade into widespread market-wide loss
of confidence — even when no specific scandal has occurred. I want to build
an ABM to investigate when and why these cascades happen.

## What the agents are

- Buyers who decide whether to purchase based on perceived trust
- Sellers who maintain reputation scores
- A platform that aggregates and displays trust signals

## What I don't yet know

- The exact mechanism by which buyer behavior aggregates into market-wide
  panic — is it through observation of other buyers, through trust score
  signals, or through both?
- Whether the cascade requires a triggering event or can emerge spontaneously
- The role of platform design (how trust scores are displayed, updated)

## Why ABM

This is exactly the kind of micro-to-macro emergence that requires
agent-based modelling. No closed-form model captures the heterogeneity of
trust signals or the feedback between individual decisions and market state.
"""


def run_one_story(name: str, story_text: str, mode_override: str | None = None) -> dict:
    """Run the relevant phases for one story, return key artifacts as a dict."""
    suffix = f" (--mode {mode_override})" if mode_override else " (auto-detect)"
    console.rule(f"[bold blue]Running: {name}{suffix}[/bold blue]")

    client = make_client(
        provider=config.LLM_PROVIDER,
        api_key=config.get_api_key(),
        base_url=config.get_base_url(),
        timeout=300,
    )
    console.print(f"[dim]Using provider: {config.LLM_PROVIDER}, "
                  f"default model: {config.DEFAULT_MODEL}[/dim]")

    workspace = Workspace.create(name=f"e2e_{name}")
    workspace.write_story(story_text)
    console.print(f"[dim]Workspace: {workspace.path}[/dim]")

    common = {"client": client, "workspace": workspace, "lang": "zh"}

    # Phase -1
    mode_detector = ModeDetector(model=config.DEFAULT_MODEL, **common)
    spec = mode_detector.run(mode_override=mode_override)
    console.print(f"  [cyan]→ spec.mode = {spec.mode}[/cyan]")
    console.print(
        f"  [cyan]→ viability thresholds: assumptions≤{spec.viability_max_assumptions}, "
        f"missing≤{spec.viability_max_missing_elements}[/cyan]"
    )

    # Phase 0.5 (originate only)
    hypothesis_md = ""
    if spec.mode == "originate":
        hyp_agent = HypothesisAgent(model=config.STRONG_MODEL, **common)
        hypothesis_md = hyp_agent.run()

    # Phase 1
    designer = DesignAgent(model=config.STRONG_MODEL, **common)
    design = designer.run()

    # Phase 1c
    viability_checker = ViabilityChecker(model=config.DEFAULT_MODEL, **common)
    viability = viability_checker.check(
        workspace.design_path,
        workspace.story_path,
        spec=spec,
    )

    # Collect artifacts
    audit_md = (workspace.path / "audit_ledger.md").read_text(encoding="utf-8") \
        if (workspace.path / "audit_ledger.md").exists() else ""
    audit_events = []
    audit_jsonl = workspace.path / "audit_ledger.jsonl"
    if audit_jsonl.exists():
        for line in audit_jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                audit_events.append(json.loads(line))

    return {
        "workspace_path": str(workspace.path),
        "mode": spec.mode,
        "spec_path_exists": (workspace.path / "research_spec.json").exists(),
        "hypothesis_md_exists": (workspace.path / "hypothesis.md").exists(),
        "hypothesis_length": len(hypothesis_md),
        "design_length": len(design),
        "viability_ok": viability.ok,
        "viability_assumption_count": viability.assumption_count,
        "viability_missing": viability.missing_elements,
        "spec_max_assumptions": spec.viability_max_assumptions,
        "audit_event_count": len(audit_events),
        "audit_event_actors": sorted({e["actor"] for e in audit_events}),
        "audit_event_phases": sorted({e["phase"] for e in audit_events}),
        "audit_event_types": sorted({e["event_type"] for e in audit_events}),
        "audit_md_excerpt": audit_md[:1000],
    }


def main():
    # Read the El Farol reproduce-mode story
    el_farol_path = Path("examples/classic_el_farol/story.md")
    reproduce_story = el_farol_path.read_text(encoding="utf-8")

    # Run three scenarios
    results = {}
    # 1. El Farol with auto-detection: tests improved prompt
    results["reproduce_el_farol"] = run_one_story("reproduce_el_farol", reproduce_story)
    # 2. Originate trust cascade auto-detection (should easily be originate)
    results["originate_trust_cascade"] = run_one_story("originate_trust_cascade", ORIGINATE_STORY)
    # 3. Same trust cascade but with --mode reproduce override: proves CLI flag works
    results["forced_reproduce_trust"] = run_one_story(
        "forced_reproduce_trust", ORIGINATE_STORY, mode_override="reproduce"
    )

    # ── Assertions ──
    console.rule("[bold green]Verification[/bold green]")

    repro = results["reproduce_el_farol"]
    orig = results["originate_trust_cascade"]
    forced = results["forced_reproduce_trust"]

    failures = []

    # Mode detection (auto)
    if repro["mode"] != "reproduce":
        failures.append(f"El Farol (auto) should be reproduce, got {repro['mode']}")
    if orig["mode"] != "originate":
        failures.append(f"Trust cascade (auto) should be originate, got {orig['mode']}")
    # Forced mode override must win regardless of LLM judgment
    if forced["mode"] != "reproduce":
        failures.append(
            f"Forced --mode=reproduce should override LLM, got {forced['mode']}"
        )
    # Forced reproduce must NOT create hypothesis.md (originate-only artifact)
    if forced["hypothesis_md_exists"]:
        failures.append("forced reproduce: hypothesis.md should not exist")
    if forced["spec_max_assumptions"] != 5:
        failures.append(
            f"forced reproduce: viability threshold should be 5, got {forced['spec_max_assumptions']}"
        )

    # research_spec.json written
    if not repro["spec_path_exists"]:
        failures.append("reproduce: research_spec.json missing")
    if not orig["spec_path_exists"]:
        failures.append("originate: research_spec.json missing")

    # Hypothesis: only originate
    if repro["hypothesis_md_exists"]:
        failures.append("reproduce mode should NOT create hypothesis.md")
    if not orig["hypothesis_md_exists"]:
        failures.append("originate mode should create hypothesis.md")
    if orig["hypothesis_length"] < 500:
        failures.append(f"originate hypothesis.md too short: {orig['hypothesis_length']}")

    # Viability thresholds differ
    if repro["spec_max_assumptions"] != 5:
        failures.append(f"reproduce should have max_assumptions=5, got {repro['spec_max_assumptions']}")
    if orig["spec_max_assumptions"] != 15:
        failures.append(f"originate should have max_assumptions=15, got {orig['spec_max_assumptions']}")

    # Audit ledger populated for both
    if repro["audit_event_count"] < 2:
        failures.append(f"reproduce audit has too few events: {repro['audit_event_count']}")
    if orig["audit_event_count"] < 2:
        failures.append(f"originate audit has too few events: {orig['audit_event_count']}")

    # Expected actors in both
    for label, r in [("reproduce", repro), ("originate", orig)]:
        for must_have in ["ModeDetector", "ViabilityChecker"]:
            if must_have not in r["audit_event_actors"]:
                failures.append(f"{label} audit missing actor: {must_have}")

    # ── Report ──
    console.print("\n[bold]Summary table:[/bold]")
    console.print(
        f"{'metric':<32} | {'el_farol(auto)':<18} | "
        f"{'trust(auto)':<18} | trust(--mode=repro)"
    )
    console.print("-" * 100)
    keys_to_show = [
        "mode", "spec_max_assumptions",
        "hypothesis_md_exists", "hypothesis_length",
        "viability_ok", "viability_assumption_count",
        "audit_event_count",
    ]
    for k in keys_to_show:
        console.print(
            f"{k:<32} | {str(repro[k]):<18} | "
            f"{str(orig[k]):<18} | {forced[k]}"
        )

    console.print(f"\n[dim]el_farol:   {repro['workspace_path']}[/dim]")
    console.print(f"[dim]trust(auto):  {orig['workspace_path']}[/dim]")
    console.print(f"[dim]forced:     {forced['workspace_path']}[/dim]")

    if failures:
        console.print("\n[bold red]FAILURES:[/bold red]")
        for f in failures:
            console.print(f"  ✗ {f}")
        return 1
    else:
        console.print("\n[bold green]✓ All checks passed[/bold green]")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
