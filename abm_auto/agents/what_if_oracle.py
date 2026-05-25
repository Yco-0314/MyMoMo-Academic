"""
Phase 6.5: What-If Scenario Oracle (originate mode only).

Runs after the main run/analyze/optimize loop in originate mode.
Reproduce mode skips this entirely — when reproducing a paper, exploring
counterfactual scenarios is the wrong activity; we want fidelity, not
boundary exploration.

Purpose:
  Original-research ABM users want to know the *envelope* of their model:
  what happens at the extremes, what assumptions invert the conclusion,
  what second-order dynamics emerge. AnalyzerAgent answers "what happened",
  but the researcher's next question is always "what could happen?"

  This agent generates 6 structured what-if scenarios using a forecasting
  framework adapted from K-Dense-AI/what-if-oracle:

    Ω Best Case    — parameters producing the most theoretically interesting outcome
    α Most Likely  — empirical / default-like configuration
    Δ Worst Case   — parameter regimes where the mechanism breaks down
    Ψ Wild Card    — extreme but plausible outliers
    Φ Contrarian   — assumptions that invert the intuitive prediction
    ∞ Second Order — what happens after the main dynamics stabilize?

Output:
  what_if_analysis.md — structured scenarios + summary
  Appended to all_insights so it shows up in the final report.
"""
from __future__ import annotations

from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()

_SYSTEM = (
    "You are a research foresight analyst for an agent-based modelling study. "
    "Your job is to map the behavioural envelope of a model — not its current results, "
    "but the space of plausible adjacent outcomes. "
    "Be specific: cite parameters, propose concrete modifications, "
    "describe predicted dynamics in measurable terms. "
    "Write in the same language as the source materials (Chinese if Chinese, English if English)."
)

_SCENARIO_TEMPLATE = """## What-If 场景分析 (What-If Envelope)

为本研究构建 6 类反事实场景，覆盖模型的行为边界。每类场景须包含：
- **参数 / 假设修改**：相对当前 baseline 改了什么（具体数值）
- **预测动态**：仿真会出现什么（具体到指标方向、强度、时序）
- **研究意义**：这个场景为什么对原创贡献有价值

### Ω Best Case (理论最有趣)
能让本研究的核心机制最清晰地展现，哪怕脱离经验现实。

### α Most Likely (经验最贴近)
参数贴近真实世界观测值（如果文献中有），呈现「实际系统会怎样运行」。

### Δ Worst Case (机制崩溃)
机制在哪些参数区域不再产生有趣的涌现，模型退化为平凡解。

### Ψ Wild Card (极端但可信)
小概率但理论上可能的参数组合，可能导致剧烈相变或全新模式。

### Φ Contrarian (反直觉)
违背通常预期的假设修改——例如「如果同质偏好实际上**促进**多样性呢？」。
重点是揭示模型中可能存在的隐藏假设。

### ∞ Second Order (二阶涌现)
主动态稳定后，下一步会发生什么？谁会被影响？是否存在系统层面的反馈？

---

最后给出 **场景比较表**：

| 场景 | 一句话发现 | 对原创贡献的价值 |
|---|---|---|
| Ω | ... | ... |
| α | ... | ... |
| Δ | ... | ... |
| Ψ | ... | ... |
| Φ | ... | ... |
| ∞ | ... | ... |
"""


class WhatIfOracle(BaseAgent):
    """
    Phase 6.5: Counterfactual scenario analysis (originate mode only).

    Called once per pipeline run, after the optimize/analyze loop completes.
    """

    def run(self, all_insights: list[str], spec=None) -> str:
        """Generate what_if_analysis.md. Returns the text (empty if skipped)."""

        # Reproduce mode: skip silently
        if spec is None or spec.mode != "originate":
            return ""

        # Skip if already generated (re-run safety)
        existing_path = self.workspace.path / "what_if_analysis.md"
        if existing_path.exists() and existing_path.stat().st_size > 200:
            console.print(
                "  [dim]Phase 6.5: what_if_analysis.md already present — skipping.[/dim]"
            )
            return existing_path.read_text(encoding="utf-8")

        console.print("[bold cyan]Phase 6.5: Generating what-if scenarios...[/bold cyan]")

        story = self.workspace.read_story()
        design = self.workspace.read_design()
        hypothesis = self.workspace.read_hypothesis()

        if not (story and design and all_insights):
            console.print("  [yellow]⚠ Insufficient context for what-if analysis — skipping[/yellow]")
            return ""

        # Build the user prompt
        insights_text = "\n\n".join(all_insights[-5:])  # last 5 runs of insights
        hypothesis_block = (
            f"\n\n## Theoretical Anchor (from hypothesis.md)\n\n{hypothesis[:1500]}"
            if hypothesis
            else ""
        )

        user_prompt = (
            "## Research Context\n\n"
            f"{story[:1200]}\n\n"
            f"## Model Design\n\n{design[:1500]}\n\n"
            f"## Simulation Insights so far\n\n{insights_text[:3000]}"
            f"{hypothesis_block}\n\n"
            "---\n\n"
            f"{_SCENARIO_TEMPLATE}"
        )

        analysis = self.call_llm(_SYSTEM, user_prompt, max_tokens=3500)

        existing_path.write_text(analysis, encoding="utf-8")
        console.print(
            f"  [green]✓ what_if_analysis.md written ({len(analysis)} chars)[/green]"
        )

        try:
            scenario_markers = sum(
                analysis.count(s) for s in ("## Ω", "## α", "## Δ", "## Ψ", "## Φ", "## ∞")
            )
            self.workspace.audit.info(
                phase="Phase 6.5",
                text=(
                    f"What-if envelope written ({len(analysis)} chars, "
                    f"{scenario_markers}/6 scenarios)"
                ),
                actor="WhatIfOracle",
                structured={
                    "length": len(analysis),
                    "scenario_count": scenario_markers,
                    "insights_synthesised": len(all_insights),
                },
            )
        except Exception:
            pass

        return analysis
