"""
Multi-reviewer ABM peer review panel.

5 specialized reviewers + 1 Editor-in-Chief, modeled after
top journal review processes (JASSS, CMOT, AJS, ASR).

Reviewers:
  R1 — Theory contribution & concept construction
  R2 — Methodology & verification transparency
  R3 — Literature dialogue & gap validation
  R4 — Logic chain & structure audit
  EiC — Editor-in-Chief desk reject filter + final verdict
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from abm_auto.agents.base import BaseAgent

console = Console()


# Reviewer definitions: (id, name, prompt_file, system_msg, materials_needed)
REVIEWERS = [
    {
        "id": "R1",
        "name": "理论贡献质询师",
        "prompt": "review_theory",
        "system": (
            "你是社会科学顶刊的资深理论审稿人。尖锐直接，禁止讨好型学术套话。"
            "如果理论贡献为零，直说。用中文撰写。"
        ),
        "materials": ["story", "design", "odd", "report"],
    },
    {
        "id": "R2",
        "name": "方法论审查员",
        "prompt": "review_methodology",
        "system": (
            "你是学术界出名的'挑刺王' Reviewer 2，ABM 方法论专家。"
            "对 ODD 透明度和 V&V 有像素级洁癖。用中文撰写。"
        ),
        "materials": ["odd", "design", "sensitivity", "memory", "params_history"],
    },
    {
        "id": "R3",
        "name": "文献对话专家",
        "prompt": "review_literature",
        "system": (
            "你精通 ABM 与计算社会科学思想史，擅长识别伪创新和稻草人缺口。"
            "用中文撰写。"
        ),
        "materials": ["story", "design", "odd", "report"],
    },
    {
        "id": "R4",
        "name": "逻辑结构拆解师",
        "prompt": "review_logic",
        "system": (
            "你是学术逻辑审计师，只关注论证结构是否自洽严密。"
            "不需要领域知识，纯粹的形式逻辑检验。用中文撰写。"
        ),
        "materials": ["story", "design", "results", "trajectory", "report"],
    },
]


class ReviewerAgent(BaseAgent):
    """Multi-reviewer peer review panel for ABM research."""

    # Reviewers whose evaluation criteria are mode-dependent.
    # R2 (methodology transparency) is mode-neutral and skips the mode preamble.
    _MODE_AWARE_REVIEWERS = {"R1", "R3", "R4"}

    def run(self, mode: str = "panel", spec=None) -> str:
        """
        Run peer review.

        Args:
            mode: "panel" for full 5-reviewer panel, "quick" for single consolidated review.
            spec: ResearchSpec from ModeDetector (optional). When provided, R1/R3/R4
                  and EiC receive a mode-context preamble that re-calibrates their
                  criteria — reproduce mode evaluates fidelity, originate mode
                  evaluates contribution.

        Returns:
            Combined review as markdown text.
        """
        if mode == "quick":
            return self._run_quick(spec=spec)
        return self._run_panel(spec=spec)

    def _run_panel(self, spec=None) -> str:
        """Run the full 5-reviewer panel: R1→R2→R3→R4→EiC."""
        console.print(Panel.fit(
            "[bold]同行评议委员会[/bold]\n"
            "R1 理论质询师 → R2 方法论审查员 → R3 文献专家 → R4 逻辑拆解师 → 主编终审",
            border_style="magenta",
        ))

        materials = self._gather_materials()
        reviews = {}

        # Pre-compute mode context block (empty string if no spec or unknown mode)
        mode_block = self._mode_context_block(spec)
        if mode_block:
            mode_label = spec.mode if spec else "unknown"
            console.print(f"  [dim]Review mode: {mode_label}[/dim]")

        # Run R1-R4 sequentially
        for reviewer in REVIEWERS:
            rid = reviewer["id"]
            console.print(f"\n[bold magenta]{rid}: {reviewer['name']}[/bold magenta]")

            prompt_template = self.load_prompt(reviewer["prompt"])
            prompt = self._fill_template(prompt_template, materials, reviewer["materials"])

            # Inject mode context preamble for R1/R3/R4 only (R2 is mode-neutral)
            if mode_block and rid in self._MODE_AWARE_REVIEWERS:
                prompt = mode_block + "\n\n---\n\n" + prompt

            # Append audit history — cross-phase issue context that the templates
            # don't reference by placeholder. Reviewers see what was raised
            # in earlier phases and whether it was resolved.
            audit_history = materials.get("audit_history", "")
            if audit_history and "（审计记录为空" not in audit_history:
                prompt += (
                    "\n\n---\n\n"
                    "## 流水线审计历史（cross-phase audit ledger）\n\n"
                    "以下是 pipeline 各阶段已记录的 issue 及其状态。请在评审中明确引用 open issues，"
                    "对已 resolved 的 issue 可作为方法论透明度的正面证据。\n\n"
                    + audit_history
                )

            review = self.call_llm(reviewer["system"], prompt, max_tokens=3072)
            reviews[rid] = review

            # Save individual review
            path = self.workspace.path / f"review_{rid.lower()}.md"
            path.write_text(review, encoding="utf-8")
            console.print(f"  [green]✓ {rid} review saved[/green]")

            # Extract score if present
            score = self._show_score(review, rid)

            # Audit: log this reviewer's score + name
            try:
                self.workspace.audit.info(
                    phase="Phase 8",
                    text=f"{rid} ({reviewer['name']}) review complete, score: {score or 'n/a'}",
                    actor=f"Reviewer:{rid}",
                    structured={
                        "reviewer_id": rid,
                        "reviewer_name": reviewer["name"],
                        "score": score,
                        "review_length": len(review),
                    },
                )
            except Exception:
                pass

        # Run Editor-in-Chief with all reviewer summaries
        console.print(f"\n[bold red]EiC: 主编终审[/bold red]")
        eic_review = self._run_editor(materials, reviews, mode_block=mode_block)
        reviews["EiC"] = eic_review

        # Combine all reviews into one document
        combined = self._combine_reviews(reviews)
        combined_path = self.workspace.path / "peer_review.md"
        combined_path.write_text(combined, encoding="utf-8")
        console.print(f"\n[bold green]✓ 完整评审报告: {combined_path}[/bold green]")

        self._display_final_verdict(eic_review)
        return combined

    def _run_quick(self, spec=None) -> str:
        """Run the original single-pass consolidated review."""
        console.print("[bold cyan]Peer Review (Quick Mode)...[/bold cyan]")

        materials = self._gather_materials()
        prompt_template = self.load_prompt("peer_review")
        prompt = (
            prompt_template
            .replace("{{ story }}", materials["story"])
            .replace("{{ design }}", materials["design"])
            .replace("{{ odd }}", materials["odd"])
            .replace("{{ results_summary }}", materials["results"])
            .replace("{{ sensitivity }}", materials["sensitivity"])
            .replace("{{ trajectory }}", materials["trajectory"])
            .replace("{{ memory }}", materials["memory"])
        )

        # Inject mode context preamble
        mode_block = self._mode_context_block(spec)
        if mode_block:
            prompt = mode_block + "\n\n---\n\n" + prompt

        system = (
            "You are a senior ABM reviewer for JASSS and CMOT journals. "
            "Be rigorous, specific, and constructive. Write in Chinese. "
            "Score each dimension honestly — do not inflate scores."
        )

        review = self.call_llm(system, prompt, max_tokens=4096)
        review_path = self.workspace.path / "peer_review.md"
        review_path.write_text(review, encoding="utf-8")
        console.print(f"  [green]✓ Peer review saved: {review_path}[/green]")
        self._display_final_verdict(review)
        return review

    def _run_editor(
        self,
        materials: dict[str, str],
        reviews: dict[str, str],
        mode_block: str = "",
    ) -> str:
        """Run the Editor-in-Chief final verdict."""
        prompt_template = self.load_prompt("review_editor")

        # Summarize each reviewer's output (truncate for context)
        r1_summary = reviews.get("R1", "（未执行）")[:800]
        r2_summary = reviews.get("R2", "（未执行）")[:800]
        r3_summary = reviews.get("R3", "（未执行）")[:800]
        r4_summary = reviews.get("R4", "（未执行）")[:800]

        prompt = (
            prompt_template
            .replace("{{ story }}", materials["story"])
            .replace("{{ design }}", materials["design"])
            .replace("{{ report }}", materials["report"])
            .replace("{{ r1_summary }}", r1_summary)
            .replace("{{ r2_summary }}", r2_summary)
            .replace("{{ r3_summary }}", r3_summary)
            .replace("{{ r4_summary }}", r4_summary)
        )

        # EiC also receives mode preamble so the final verdict uses correct criteria
        if mode_block:
            prompt = mode_block + "\n\n---\n\n" + prompt

        system = (
            "你是极其忙碌且眼光毒辣的 ABM 顶刊主编。"
            "没有耐心，只要结论。诚实残忍。用中文撰写。"
        )

        review = self.call_llm(system, prompt, max_tokens=3072)

        path = self.workspace.path / "review_editor.md"
        path.write_text(review, encoding="utf-8")
        console.print(f"  [green]✓ Editor review saved[/green]")

        # Audit: log the editor's final verdict
        try:
            verdict = self._extract_verdict(review)
            self.workspace.audit.info(
                phase="Phase 8",
                text=f"Editor-in-Chief verdict: {verdict or 'unknown'}",
                actor="Reviewer:EiC",
                structured={"verdict": verdict, "review_length": len(review)},
            )
        except Exception:
            pass
        return review

    @staticmethod
    def _extract_verdict(review: str) -> str | None:
        """Find the EiC verdict keyword (Accept / Minor Revision / Major Revision / Reject)."""
        for line in review.split("\n"):
            stripped = line.strip()
            for kw in ("Accept", "Minor Revision", "Major Revision", "Reject"):
                if kw in stripped and "终审" not in stripped and "##" not in stripped:
                    return kw
        return None

    def _mode_context_block(self, spec) -> str:
        """Build the mode-context preamble injected into R1/R3/R4/EiC prompts.

        Returns an empty string when spec is None — in that case reviewers use
        their original (originate-flavoured) prompts unchanged.

        The block re-calibrates evaluation criteria:
          reproduce — judge fidelity to the source paper, not originality
          originate — judge contribution, anchored on hypothesis.md (if present)
        """
        if spec is None:
            return ""

        if spec.mode == "reproduce":
            paper_ref = spec.paper_ref or "（源论文信息未提取）"
            return (
                "## 评审模式：复现研究 (Reproduction Mode)\n\n"
                f"**待评审任务是对一篇已有论文的复现：** {paper_ref}\n\n"
                "**评审重点是「忠实度」而非「原创性」。** 重要的范式调整：\n\n"
                "- **不要问** 「这有什么理论贡献？」——理论贡献属于原论文。\n"
                "- **应该问**：模型是否忠实实现了原论文描述的机制？仿真动态是否复现了原论文报告的关键现象？\n"
                "- **R1（理论）**：评判原论文的理论框架是否被准确还原；关键概念是否被简化、混淆或误解；\n"
                "  agent 行为规则是否对应原论文的机制描述。\n"
                "- **R3（文献）**：评判与原论文的对话是否准确；原论文与领域的关系是否被正确呈现；\n"
                "  不要再问「研究缺口是否真实」——缺口由原论文定义。\n"
                "- **R4（逻辑）**：评判复现的因果链是否与原论文一致；任何偏离原文之处是 bug 还是合理的实现差异。\n\n"
                "**评分基准重置**：高分给「成功复现关键动态且实现透明」，"
                "低分给「机制偏离、关键参数无依据、未能复现关键发现」。\n"
                "禁止以「无新理论贡献」为由扣分——这是设计目标，不是缺陷。\n"
            )

        if spec.mode == "originate":
            phenomenon = spec.phenomenon or "（现象描述未提取）"
            rq = spec.research_question or ""
            has_hypothesis = bool(self.workspace.read_hypothesis())
            hypothesis_note = (
                "假设框架已经过竞争性筛选（见 hypothesis.md），"
                "推荐假设作为本模型的理论锚点。"
                if has_hypothesis
                else "未运行 HypothesisAgent，模型理论框架由 DesignAgent 直接构建。"
            )
            rq_block = f"\n**核心研究问题：** {rq}\n" if rq else ""
            return (
                "## 评审模式：原创研究 (Originate Mode)\n\n"
                f"**待评审任务是从现象出发的原创建模：** {phenomenon}\n"
                f"{rq_block}\n"
                f"{hypothesis_note}\n\n"
                "**评审标准与传统顶刊论文一致：** 理论贡献、机制清晰度、实证可证伪性、文献对话。\n"
                "原创模式的合理特征（不应被扣分）：\n"
                "- 部分参数为合理设定（非论文复现，无原始参数表可对照）\n"
                "- 假设的边界条件需要由作者自己论证，而非引用原论文\n"
                "- 仿真结果与「预期」不完全一致——这本身就是研究发现\n\n"
                "**应严格扣分的情形**：理论锚点不明（hypothesis.md 之外另立机制而不说明）、"
                "机制循环论证（假设直接塞进规则然后「验证」假设）、过度推论。\n"
            )

        return ""

    def _fill_template(self, template: str, materials: dict[str, str],
                       needed: list[str]) -> str:
        """Fill template placeholders with available materials."""
        for key in needed:
            placeholder = "{{ " + key + " }}"
            value = materials.get(key, "（未提供）")
            template = template.replace(placeholder, value)
        return template

    def _gather_materials(self) -> dict[str, str]:
        """Collect all reviewable artifacts from workspace."""
        ws = self.workspace

        story = ws.read_story() or "（未提供）"
        design = ws.read_design() or "（未提供）"

        odd_path = ws.path / "ODD.md"
        odd = odd_path.read_text(encoding="utf-8") if odd_path.exists() else "（未生成）"

        # Results summary
        results_lines = []
        params_history = ws.read_params_history()
        for h in params_history:
            results_lines.append(f"Run {h['run']}: {h.get('hypothesis', '')} | Params: {h['params']}")
        for run_dir in sorted(ws.results_dir.glob("run_*")):
            insights_file = run_dir / "insights.md"
            if insights_file.exists():
                text = insights_file.read_text(encoding="utf-8")
                results_lines.append(f"\n### {run_dir.name} Insights\n{text[:500]}")
        results = "\n".join(results_lines) if results_lines else "（无实验结果）"

        # Params history as text
        params_text = json.dumps(params_history, indent=2, ensure_ascii=False) if params_history else "（无参数历史）"

        # Sensitivity
        sensitivity = "（未执行）"
        for method in ("morris", "sobol"):
            interp_path = ws.path / f"sensitivity_{method}_interpretation.md"
            if interp_path.exists():
                sensitivity = interp_path.read_text(encoding="utf-8")
                break
            json_path = ws.path / f"sensitivity_{method}.json"
            if json_path.exists():
                sensitivity = json_path.read_text(encoding="utf-8")
                break

        # Trajectory
        trajectory = "（未执行）"
        for p in [ws.path / "trajectory_interpretation.md", ws.path / "trajectory_analysis.md"]:
            if p.exists():
                trajectory = p.read_text(encoding="utf-8")
                break

        # Memory
        memory = "（未启用）"
        mem_dir = ws.path / "memory"
        if mem_dir.exists():
            from abm_auto.memory.store import ExperimentMemory
            mem = ExperimentMemory(mem_dir)
            memory = mem.retrieve_context() or "（空）"

        # Report
        report = "（未生成）"
        if ws.report_path.exists():
            report = ws.report_path.read_text(encoding="utf-8")

        # Audit ledger — cross-phase issue history (newest)
        try:
            audit_view = ws.audit.for_reviewer()
        except Exception:
            audit_view = "（审计记录不可用）"

        return {
            "story": story[:2000],
            "design": design[:2500],
            "odd": odd[:2500],
            "results": results[:2000],
            "params_history": params_text[:1500],
            "sensitivity": sensitivity[:1500],
            "trajectory": trajectory[:1500],
            "memory": memory[:1000],
            "report": report[:2000],
            "audit_history": audit_view[:2500],
        }

    def _build_resolution_ledger(self, reviews: dict[str, str]) -> str:
        """Generate a structured Resolution Ledger from all reviewer content.

        Each issue is classified into one of four actions:
          FIX           — fix the code or model mechanism
          NEW_ANALYSIS  — re-run simulation with different params / setup
          DOWNGRADE     — weaken a claim in the report
          DROP          — issue is out of scope, no action needed
        """
        all_reviews = "\n\n".join(
            f"## {rid}\n{text}" for rid, text in reviews.items()
        )

        system = (
            "You are an editorial assistant. Extract every distinct issue raised by the reviewers "
            "and classify each one. Respond ONLY with a Markdown table, no preamble.\n"
            "Table columns: Issue | Severity (High/Medium/Low) | Action | Notes\n"
            "Action must be exactly one of: FIX | NEW_ANALYSIS | DOWNGRADE | DROP\n"
            "- FIX: code or model mechanism needs to be corrected\n"
            "- NEW_ANALYSIS: re-run simulation with adjusted parameters or setup\n"
            "- DOWNGRADE: soften a claim in the report text\n"
            "- DROP: acknowledged but out of scope for this paper"
        )

        prompt = (
            "## Reviewer Comments\n\n"
            f"{all_reviews[:5000]}\n\n"
            "Generate the Resolution Ledger table now."
        )

        try:
            ledger_body = self.call_llm(system, prompt, max_tokens=1500)
            # Ensure it starts with a header row
            if "| Issue" not in ledger_body:
                ledger_body = (
                    "| Issue | Severity | Action | Notes |\n"
                    "|-------|----------|--------|-------|\n"
                ) + ledger_body
        except Exception:
            ledger_body = (
                "| Issue | Severity | Action | Notes |\n"
                "|-------|----------|--------|-------|\n"
                "| (Resolution Ledger generation failed) | — | — | — |\n"
            )

        return (
            "\n\n---\n\n"
            "# Resolution Ledger\n\n"
            "> Structured action table generated from all reviewer comments.\n"
            "> Pipeline reads this table: NEW_ANALYSIS → re-run, FIX → code revision.\n\n"
            + ledger_body
        )

    def _combine_reviews(self, reviews: dict[str, str]) -> str:
        """Combine all reviews into a single document with Resolution Ledger."""
        parts = ["# ABM 同行评议报告\n"]

        reviewer_names = {
            "R1": "Reviewer 1: 理论贡献质询师",
            "R2": "Reviewer 2: 方法论审查员",
            "R3": "Reviewer 3: 文献对话专家",
            "R4": "Reviewer 4: 逻辑结构拆解师",
            "EiC": "主编终审",
        }

        for rid in ["R1", "R2", "R3", "R4", "EiC"]:
            if rid in reviews:
                parts.append(f"\n---\n\n# {reviewer_names[rid]}\n\n{reviews[rid]}")

        # Append Resolution Ledger at the end
        parts.append(self._build_resolution_ledger(reviews))

        return "\n".join(parts)

    def parse_ledger(self, peer_review_text: str) -> dict[str, list[str]]:
        """Parse the Resolution Ledger from peer_review.md into action buckets.

        Returns:
            {
              "FIX": ["issue text", ...],
              "NEW_ANALYSIS": [...],
              "DOWNGRADE": [...],
              "DROP": [...],
            }
        """
        actions: dict[str, list[str]] = {
            "FIX": [], "NEW_ANALYSIS": [], "DOWNGRADE": [], "DROP": [],
        }
        in_ledger = False
        for line in peer_review_text.splitlines():
            if "Resolution Ledger" in line:
                in_ledger = True
                continue
            if not in_ledger:
                continue
            if line.startswith("|") and "|" in line[1:]:
                cols = [c.strip() for c in line.strip("|").split("|")]
                if len(cols) >= 3:
                    issue, _, action = cols[0], cols[1], cols[2]
                    action_key = action.strip().upper().replace(" ", "_")
                    if action_key in actions and issue and "Issue" not in issue:
                        actions[action_key].append(issue)
        return actions

    def _show_score(self, review: str, reviewer_id: str) -> str | None:
        """Extract and display score from a reviewer's output. Returns score string or None."""
        for line in review.split("\n"):
            stripped = line.strip()
            if "评分" in stripped and "/10" in stripped:
                console.print(f"  [dim]{reviewer_id}: {stripped}[/dim]")
                return stripped
        return None

    def _display_final_verdict(self, review: str) -> None:
        """Display the final verdict from the review."""
        for line in review.split("\n"):
            stripped = line.strip()
            if "总分" in stripped and "/" in stripped:
                console.print(f"\n  [bold]{stripped}[/bold]")
            for kw in ("Accept", "Minor Revision", "Major Revision", "Reject"):
                if kw in stripped and "终审" not in stripped and "##" not in stripped:
                    console.print(f"  [bold yellow]终审决议: {stripped}[/bold yellow]")
                    return
