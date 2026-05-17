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

    def run(self, mode: str = "panel") -> str:
        """
        Run peer review.

        Args:
            mode: "panel" for full 5-reviewer panel, "quick" for single consolidated review.

        Returns:
            Combined review as markdown text.
        """
        if mode == "quick":
            return self._run_quick()
        return self._run_panel()

    def _run_panel(self) -> str:
        """Run the full 5-reviewer panel: R1→R2→R3→R4→EiC."""
        console.print(Panel.fit(
            "[bold]同行评议委员会[/bold]\n"
            "R1 理论质询师 → R2 方法论审查员 → R3 文献专家 → R4 逻辑拆解师 → 主编终审",
            border_style="magenta",
        ))

        materials = self._gather_materials()
        reviews = {}

        # Run R1-R4 sequentially
        for reviewer in REVIEWERS:
            rid = reviewer["id"]
            console.print(f"\n[bold magenta]{rid}: {reviewer['name']}[/bold magenta]")

            prompt_template = self.load_prompt(reviewer["prompt"])
            prompt = self._fill_template(prompt_template, materials, reviewer["materials"])

            review = self.call_llm(reviewer["system"], prompt, max_tokens=3072)
            reviews[rid] = review

            # Save individual review
            path = self.workspace.path / f"review_{rid.lower()}.md"
            path.write_text(review, encoding="utf-8")
            console.print(f"  [green]✓ {rid} review saved[/green]")

            # Extract score if present
            self._show_score(review, rid)

        # Run Editor-in-Chief with all reviewer summaries
        console.print(f"\n[bold red]EiC: 主编终审[/bold red]")
        eic_review = self._run_editor(materials, reviews)
        reviews["EiC"] = eic_review

        # Combine all reviews into one document
        combined = self._combine_reviews(reviews)
        combined_path = self.workspace.path / "peer_review.md"
        combined_path.write_text(combined, encoding="utf-8")
        console.print(f"\n[bold green]✓ 完整评审报告: {combined_path}[/bold green]")

        self._display_final_verdict(eic_review)
        return combined

    def _run_quick(self) -> str:
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

    def _run_editor(self, materials: dict[str, str], reviews: dict[str, str]) -> str:
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

        system = (
            "你是极其忙碌且眼光毒辣的 ABM 顶刊主编。"
            "没有耐心，只要结论。诚实残忍。用中文撰写。"
        )

        review = self.call_llm(system, prompt, max_tokens=3072)

        path = self.workspace.path / "review_editor.md"
        path.write_text(review, encoding="utf-8")
        console.print(f"  [green]✓ Editor review saved[/green]")
        return review

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
        }

    def _combine_reviews(self, reviews: dict[str, str]) -> str:
        """Combine all reviews into a single document."""
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

        return "\n".join(parts)

    def _show_score(self, review: str, reviewer_id: str) -> None:
        """Extract and display score from a reviewer's output."""
        for line in review.split("\n"):
            stripped = line.strip()
            if "评分" in stripped and "/10" in stripped:
                console.print(f"  [dim]{reviewer_id}: {stripped}[/dim]")
                break

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
