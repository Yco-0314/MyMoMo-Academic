"""
Mock-LLM end-to-end verification of dual-mode pipeline contracts.

Replaces every agent's `call_llm` with a deterministic stub that:
  1. records the (system, prompt) it was called with
  2. returns a hand-canned response appropriate for that agent

Verifies the *plumbing*, not LLM judgment quality:
  - ModeDetector → research_spec.json populated correctly
  - HypothesisAgent runs in originate, skipped in reproduce
  - DesignAgent's prompt CONTAINS hypothesis content when present
  - ViabilityChecker uses mode-aware thresholds
  - ReviewerAgent injects mode preamble into R1/R3/R4/EiC prompts (not R2)
  - audit_ledger.jsonl accumulates events from multiple actors

Zero API calls.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from abm_auto.runner.workspace import Workspace
from abm_auto.agents.mode_detector import ModeDetector, ResearchSpec
from abm_auto.agents.hypothesis_agent import HypothesisAgent
from abm_auto.agents.designer import DesignAgent
from abm_auto.agents.viability_checker import ViabilityChecker
from abm_auto.agents.reviewer import ReviewerAgent
from abm_auto.agents.what_if_oracle import WhatIfOracle

console = Console()


# ── Canned responses ────────────────────────────────────────────────────────

MOCK_HYPOTHESIS_MD = """## H1: 信任级联通过观察其他买家行为传播

**Core mechanism**: 买家观察其他买家的退出行为，将退出解读为隐藏风险信号。

**Key assumptions**:
- 买家有限理性，依赖社会信号
- 退出行为可见

**Predicted dynamics**: 当退出率超过 15% 时，二阶传播效应出现，市场进入崩溃模式。

**Key parameters to sweep**: observation_radius (1-50), trust_decay (0.01-0.2), social_weight (0-1)

**Testability score**: 8/10 — 可通过模拟扰动验证。

**Novelty vs. literature**: 强调买家间的观察传播，区别于纯信号机制。

## H2: 平台信号设计放大微小波动

**Core mechanism**: 平台的可视化设计（红点、星级阈值）使小波动跨阈值。

**Key assumptions**:
- 信号阈值是离散的
- 买家对信号变化敏感

**Predicted dynamics**: 信号设计的离散性导致非线性反应。

**Key parameters to sweep**: signal_granularity (3-10), threshold_count (1-5)

**Testability score**: 7/10

**Novelty vs. literature**: 关注 UI 设计在涌现中的作用。

## H3: 卖家应激反应触发买家退出

**Core mechanism**: 卖家对负面信号反应过度，进一步恶化信号。

**Key assumptions**:
- 卖家也是有限理性
- 卖家行为可见

**Predicted dynamics**: 双向反馈循环。

**Key parameters to sweep**: seller_reaction_strength (0-1)

**Testability score**: 6/10

**Novelty vs. literature**: 卖家与买家联合行为，非单向。

## Recommendation

**Build H1** because 它最贴近经验观察（市场panic往往源于群体观察），最易在 ABM 中实现（agent间观察是标准机制），并能为后续扩展到 H2/H3 提供基础。

## Rejected alternatives (brief)

- **H2**: 需要建模 UI 设计，超出 ABM 核心范围。
- **H3**: 引入卖家异质性会显著增加模型复杂度。
"""

MOCK_DESIGN_MD_HEADER = """# DESIGN.md — Trust Cascade Model

## 1. Agents

- Buyer agents (100): observe market, decide to participate
- Seller agents (20): maintain reputation, react to demand

## 2. Interaction mechanism

Buyers observe a random sample of other buyers each step.
Time step: 1 day of market activity.

## 3. Initialization

Buyers initialized with trust_threshold ~ N(0.5, 0.1).
Sellers start with reputation = 1.0.

## 4. Decision rules

Buyer decides to participate if perceived_trust > trust_threshold.

## 5. Scenarios

num_agents=100, observation_radius=10, trust_decay=0.05, social_weight=0.5

## 6. Output metrics

participation_rate, mean_trust, cascade_events
"""

MOCK_VIABILITY_LLM_PASS = '{"verdict":"pass","reason":"design has clear agents and outputs"}'
MOCK_REVIEW_R1 = "## Reviewer 1 评审\n\n理论贡献分析…\n\n### 评分: 7/10"
MOCK_REVIEW_R2 = "## Reviewer 2 评审\n\nODD 透明度…\n\n### 评分: 6/10"
MOCK_REVIEW_R3 = "## Reviewer 3 评审\n\n文献对话…\n\n### 评分: 7/10"
MOCK_REVIEW_R4 = "## Reviewer 4 评审\n\n逻辑结构…\n\n### 评分: 8/10"
MOCK_REVIEW_EIC = "## 主编终审\n\n综合判定…\n\n### 总分: 7/10\n\nMinor Revision"
MOCK_RESOLUTION_LEDGER = (
    "| Issue | Severity | Action | Notes |\n"
    "|-------|----------|--------|-------|\n"
    "| 参数依据不明 | High | DOWNGRADE | 在报告中弱化claim |\n"
    "| 缺乏稳健性检验 | Medium | NEW_ANALYSIS | 加跑参数扰动 |\n"
)


def build_mock_call_llm(recorder: list, agent_name: str):
    """Return a fake call_llm bound to record calls and dispatch by content."""

    def fake(self, system: str, prompt: str, max_tokens: int = 2048, **kwargs):
        recorder.append({"agent": agent_name, "system": system, "prompt": prompt})

        # ModeDetector — returns JSON spec
        if agent_name == "ModeDetector":
            if "El Farol" in prompt or "Arthur" in prompt or "Bar Problem" in prompt:
                return json.dumps({
                    "mode": "reproduce",
                    "confidence": 0.95,
                    "paper_ref": "Arthur 1994 El Farol Bar Problem",
                    "paper_doi": "",
                    "phenomenon": "",
                    "research_question": "",
                    "has_calibration_data": False,
                    "calibration_data_path": "",
                    "calibration_targets": [],
                })
            else:
                return json.dumps({
                    "mode": "originate",
                    "confidence": 0.88,
                    "paper_ref": "",
                    "paper_doi": "",
                    "phenomenon": "Trust cascade in online marketplaces",
                    "research_question": "When and why do trust cascades happen?",
                    "has_calibration_data": False,
                    "calibration_data_path": "",
                    "calibration_targets": [],
                })

        if agent_name == "HypothesisAgent":
            return MOCK_HYPOTHESIS_MD

        if agent_name == "DesignAgent":
            return MOCK_DESIGN_MD_HEADER

        if agent_name == "ViabilityChecker":
            return MOCK_VIABILITY_LLM_PASS

        if agent_name == "ReviewerAgent":
            # Dispatch by content of prompt: which reviewer is this?
            if "Reviewer 1" in prompt or "理论贡献" in prompt:
                return MOCK_REVIEW_R1
            if "Reviewer 2" in prompt or "ABM 方法论" in prompt:
                return MOCK_REVIEW_R2
            if "Reviewer 3" in prompt or "文献对话" in prompt:
                return MOCK_REVIEW_R3
            if "Reviewer 4" in prompt or "逻辑链条" in prompt:
                return MOCK_REVIEW_R4
            if "editorial assistant" in system.lower() or "Resolution Ledger" in prompt:
                return MOCK_RESOLUTION_LEDGER
            # EiC
            return MOCK_REVIEW_EIC

        if agent_name == "WhatIfOracle":
            return "## Ω Best Case\n...\n## α Most Likely\n...\n"

        return "MOCK_RESPONSE"

    return fake


def run_one(story_name: str, story_text: str, expect_mode: str) -> dict:
    """Run mock pipeline through Phase -1 → 0.5 → 1 → 1c → Reviewer."""
    console.rule(f"[bold blue]{story_name}[/bold blue]")

    workspace = Workspace.create(name=f"mock_{story_name}")
    workspace.write_story(story_text)
    # Pre-create files needed by ReviewerAgent's material gatherer
    (workspace.path / "ODD.md").write_text("# ODD (mock)\nPurpose...\n", encoding="utf-8")
    workspace.report_path.write_text("# Report (mock)\nResults...\n", encoding="utf-8")

    recorder: list = []

    common = {"client": None, "workspace": workspace, "lang": "zh", "model": "mock"}

    # Phase -1
    with patch.object(ModeDetector, "call_llm",
                      build_mock_call_llm(recorder, "ModeDetector")):
        md = ModeDetector(**common)
        spec = md.run()

    # Phase 0.5
    if spec.mode == "originate":
        with patch.object(HypothesisAgent, "call_llm",
                          build_mock_call_llm(recorder, "HypothesisAgent")):
            ha = HypothesisAgent(**common)
            ha.run()

    # Phase 1
    with patch.object(DesignAgent, "call_llm",
                      build_mock_call_llm(recorder, "DesignAgent")):
        da = DesignAgent(**common)
        da.run()

    # Phase 1c
    with patch.object(ViabilityChecker, "call_llm",
                      build_mock_call_llm(recorder, "ViabilityChecker")):
        vc = ViabilityChecker(**common)
        viability = vc.check(workspace.design_path, workspace.story_path, spec=spec)

    # Phase 8 (Review) — mock
    with patch.object(ReviewerAgent, "call_llm",
                      build_mock_call_llm(recorder, "ReviewerAgent")):
        rv = ReviewerAgent(**common)
        rv.run(spec=spec)

    # ── collect artifacts ──
    audit_events = []
    if (workspace.path / "audit_ledger.jsonl").exists():
        for line in (workspace.path / "audit_ledger.jsonl").read_text(
            encoding="utf-8"
        ).splitlines():
            if line.strip():
                audit_events.append(json.loads(line))

    designer_prompt = next(
        (c["prompt"] for c in recorder if c["agent"] == "DesignAgent"), ""
    )

    # Reviewer prompts by R-id (heuristic: which reviewer template in prompt)
    reviewer_prompts: dict[str, str] = {}
    for c in recorder:
        if c["agent"] != "ReviewerAgent":
            continue
        p = c["prompt"]
        for rid, marker in [("R1", "理论贡献"), ("R2", "ABM 方法论"),
                            ("R3", "文献对话"), ("R4", "逻辑链条")]:
            if marker in p and rid not in reviewer_prompts:
                reviewer_prompts[rid] = p

    return {
        "workspace": workspace.path,
        "spec": spec,
        "viability_ok": viability.ok,
        "viability_assumption_count": viability.assumption_count,
        "viability_missing": viability.missing_elements,
        "hypothesis_exists": (workspace.path / "hypothesis.md").exists(),
        "design_exists": workspace.design_path.exists(),
        "peer_review_exists": (workspace.path / "peer_review.md").exists(),
        "audit_event_count": len(audit_events),
        "audit_actors": sorted({e["actor"] for e in audit_events}),
        "audit_phases": sorted({e["phase"] for e in audit_events}),
        "audit_severities": sorted({e["severity"] for e in audit_events}),
        "designer_prompt": designer_prompt,
        "reviewer_prompts": reviewer_prompts,
        "recorder": recorder,
        "expect_mode": expect_mode,
    }


def assert_all(results: dict[str, dict]) -> list[str]:
    """Run all contract assertions, return list of failure strings."""
    failures: list[str] = []

    repro = results["reproduce"]
    orig = results["originate"]

    # ── Mode detection accuracy (mocked, should be exact) ──
    if repro["spec"].mode != "reproduce":
        failures.append(f"reproduce: got {repro['spec'].mode}, expected reproduce")
    if orig["spec"].mode != "originate":
        failures.append(f"originate: got {orig['spec'].mode}, expected originate")

    # ── Hypothesis gate ──
    if repro["hypothesis_exists"]:
        failures.append("reproduce should NOT create hypothesis.md")
    if not orig["hypothesis_exists"]:
        failures.append("originate MUST create hypothesis.md")

    # ── Hypothesis injection into DesignAgent prompt ──
    if "Theoretical Framework" in repro["designer_prompt"]:
        failures.append("reproduce DesignAgent prompt should NOT contain Theoretical Framework block")
    if "Theoretical Framework" not in orig["designer_prompt"]:
        failures.append("originate DesignAgent prompt MUST contain Theoretical Framework block")
    if "H1: 信任级联" not in orig["designer_prompt"]:
        failures.append("originate DesignAgent prompt MUST quote the recommended hypothesis H1")

    # ── Viability thresholds ──
    if repro["spec"].viability_max_assumptions != 5:
        failures.append(f"reproduce viability_max_assumptions={repro['spec'].viability_max_assumptions}, want 5")
    if orig["spec"].viability_max_assumptions != 15:
        failures.append(f"originate viability_max_assumptions={orig['spec'].viability_max_assumptions}, want 15")

    # ── Reviewer mode preamble injection ──
    for r, mode_marker in [(repro, "Reproduction Mode"), (orig, "Originate Mode")]:
        # R1/R3/R4 should have the preamble; R2 should NOT
        for rid in ("R1", "R3", "R4"):
            p = r["reviewer_prompts"].get(rid, "")
            if not p:
                failures.append(f"{r['expect_mode']}: reviewer prompt for {rid} not captured")
                continue
            if mode_marker not in p:
                failures.append(f"{r['expect_mode']}: {rid} prompt missing '{mode_marker}'")
        r2_prompt = r["reviewer_prompts"].get("R2", "")
        if r2_prompt and mode_marker in r2_prompt:
            failures.append(f"{r['expect_mode']}: R2 prompt should NOT contain mode preamble (R2 is mode-neutral)")

    # ── Audit ledger has multiple writers ──
    for r in (repro, orig):
        required_actors = {"ModeDetector", "ViabilityChecker"}
        if not required_actors.issubset(set(r["audit_actors"])):
            failures.append(
                f"{r['expect_mode']}: audit missing actors. "
                f"Got {r['audit_actors']}, need ⊇ {required_actors}"
            )
        if r["audit_event_count"] < 2:
            failures.append(
                f"{r['expect_mode']}: audit has {r['audit_event_count']} events, expected ≥2"
            )

    return failures


def main():
    el_farol = Path("examples/classic_el_farol/story.md").read_text(encoding="utf-8")
    originate_story = """# Phenomenon: Trust cascade in online marketplaces

I want to model how small fluctuations in seller trust scores cascade into
market-wide loss of confidence on e-commerce platforms. The agents are buyers,
sellers, and a platform. The phenomenon is the sudden tipping behaviour.
"""

    results = {
        "reproduce": run_one("reproduce_el_farol", el_farol, "reproduce"),
        "originate": run_one("originate_trust", originate_story, "originate"),
    }

    console.rule("[bold]Verification[/bold]")
    failures = assert_all(results)

    # Summary table
    keys = [
        "expect_mode", "spec.mode", "spec.viability_max_assumptions",
        "hypothesis_exists", "design_exists", "peer_review_exists",
        "viability_ok", "audit_event_count", "audit_actors",
    ]

    def cell(r, k):
        if k == "spec.mode":
            return r["spec"].mode
        if k == "spec.viability_max_assumptions":
            return r["spec"].viability_max_assumptions
        return r[k]

    console.print(f"\n[bold]{'metric':<38} | reproduce  | originate[/bold]")
    console.print("-" * 80)
    for k in keys:
        console.print(f"{k:<38} | {str(cell(results['reproduce'], k))[:25]:<25} | "
                      f"{cell(results['originate'], k)}")

    # Reviewer preamble injection (per reviewer)
    console.print(f"\n[bold]{'reviewer prompt has mode preamble':<38} | reproduce | originate[/bold]")
    for rid, want in [("R1", True), ("R2", False), ("R3", True), ("R4", True)]:
        r_repro = "Reproduction Mode" in results["reproduce"]["reviewer_prompts"].get(rid, "")
        r_orig = "Originate Mode" in results["originate"]["reviewer_prompts"].get(rid, "")
        want_label = "yes" if want else "NO (neutral)"
        console.print(f"{rid} (want={want_label:<11}) {'':<14} | {str(r_repro):<9} | {r_orig}")

    if failures:
        console.print(f"\n[bold red]{len(failures)} failure(s):[/bold red]")
        for f in failures:
            console.print(f"  ✗ {f}")
        return 1
    console.print(f"\n[bold green]✓ All {len(keys) + 8}+ contract assertions passed[/bold green]")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
