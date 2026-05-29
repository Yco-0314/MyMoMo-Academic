"""SubReviewer — one adapter per panel reviewer (R1, R2, R3, R4).

Pattern mirror of `abm_auto.pipeline.phase.Phase` and
`abm_auto.codegen.fixups.CodegenFixup`: each reviewer is an independent
unit with a `name`, an optional `should_run` predicate, and a `run`
method that takes the gathered materials + mode context + llm caller
and returns the review text.

Replaces the inline `REVIEWERS = [{...}, ...]` dict-driven loop in the
historic ReviewerAgent (544-LoC god class). The new shape:

    for sub in REVIEWERS:
        if sub.should_run(ctx):
            reviews[sub.id] = sub.run(materials, mode_block, llm_caller)

Adding a reviewer = adding one SubReviewer instance to the REVIEWERS
list + the matching prompt file. No edits to ReviewerAgent.run().

What stays in ReviewerAgent (NOT extracted to sub-reviewers):
  - Materials gathering (_gather_materials) — reads workspace files
  - EiC executor (_run_editor) — synthesizes reviewer outputs, different
    input shape than R1-R4
  - Resolution Ledger (_build_resolution_ledger / parse_ledger) — meta-
    review concern, runs on COMBINED reviewer output
  - Output formatting (_combine_reviews, _display_final_verdict)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional


# Materials block names that R1-R4 templates use as {{ ... }} placeholders.
# A subreviewer's `materials_needed` is the subset its prompt actually
# references — everything else is dropped before prompt fill, keeping the
# context lean.
Materials = dict   # {placeholder_name: rendered_string}
LLMCaller = Callable[..., str]   # (system, user, max_tokens) -> str


# Per-reviewer mode-awareness: R2 is mode-neutral (methodology audit is
# the same for reproduce + originate), the others get mode preamble.
_MODE_AWARE = {"R1", "R3", "R4"}


@dataclass
class SubReviewer:
    """One reviewer in the panel — adapter for one prompt + system + materials."""

    id: str                          # "R1" | "R2" | "R3" | "R4"
    name: str                        # human-readable, used in stdout + audit
    prompt_name: str                 # template filename (without .md)
    system: str                      # system message for the LLM call
    materials_needed: list[str]      # which materials placeholders the prompt uses
    mode_aware: bool = True          # inject mode-context preamble when set
    max_tokens: int = 3072

    def should_run(self, materials: Materials, mode_block: str = "") -> bool:
        """Always-run for the standard panel. Hook for future conditional reviewers."""
        return True

    def run(
        self,
        materials: Materials,
        mode_block: str,
        llm_caller: LLMCaller,
        audit_history: str = "",
        prompt_loader: Callable[[str], str] = None,
    ) -> str:
        """Render prompt + call LLM + return review text.

        Args:
            materials: rendered material strings ({name: content}).
            mode_block: pre-rendered mode preamble (empty when no spec or R2).
            llm_caller: typically agent.call_llm bound method.
            audit_history: cross-phase audit ledger snippet (often empty).
            prompt_loader: callable taking prompt_name → template str.
                Defaults to abm_auto.agents.base.BaseAgent.load_prompt
                indirection in tests; production path injects the agent's
                bound method.

        Returns:
            The full LLM response — caller owns persisting to file.
        """
        if prompt_loader is None:
            # Lazy fallback: try to load from default prompts dir directly.
            # Production code always passes a loader explicitly.
            from abm_auto.config import PROMPTS_DIR
            prompt_loader = lambda n: (PROMPTS_DIR / f"{n}.md").read_text(encoding="utf-8")

        template = prompt_loader(self.prompt_name)
        prompt = _fill_template(template, materials, self.materials_needed)

        if self.mode_aware and mode_block:
            prompt = mode_block + "\n\n---\n\n" + prompt

        if audit_history and "（审计记录为空" not in audit_history:
            prompt += (
                "\n\n---\n\n"
                "## 流水线审计历史（cross-phase audit ledger）\n\n"
                "以下是 pipeline 各阶段已记录的 issue 及其状态。请在评审中明确引用 open issues，"
                "对已 resolved 的 issue 可作为方法论透明度的正面证据。\n\n"
                + audit_history
            )

        return llm_caller(self.system, prompt, max_tokens=self.max_tokens)


def _fill_template(template: str, materials: Materials, needed: list[str]) -> str:
    """Fill `{{ key }}` placeholders for every key in `needed`."""
    for key in needed:
        placeholder = "{{ " + key + " }}"
        value = materials.get(key, "（未提供）")
        template = template.replace(placeholder, value)
    return template


# ── Default panel: R1, R2, R3, R4 ────────────────────────────────────────


REVIEWERS: list[SubReviewer] = [
    SubReviewer(
        id="R1",
        name="理论贡献质询师",
        prompt_name="review_theory",
        system=(
            "你是社会科学顶刊的资深理论审稿人。尖锐直接，禁止讨好型学术套话。"
            "如果理论贡献为零，直说。用中文撰写。"
        ),
        materials_needed=["story", "design", "odd", "report"],
        mode_aware=True,
    ),
    SubReviewer(
        id="R2",
        name="方法论审查员",
        prompt_name="review_methodology",
        system=(
            "你是学术界出名的'挑刺王' Reviewer 2，ABM 方法论专家。"
            "对 ODD 透明度和 V&V 有像素级洁癖。用中文撰写。"
        ),
        materials_needed=["odd", "design", "sensitivity", "memory", "params_history"],
        mode_aware=False,   # R2's methodology audit is mode-neutral
    ),
    SubReviewer(
        id="R3",
        name="文献对话专家",
        prompt_name="review_literature",
        system=(
            "你精通 ABM 与计算社会科学思想史，擅长识别伪创新和稻草人缺口。"
            "用中文撰写。"
        ),
        materials_needed=["story", "design", "odd", "report"],
        mode_aware=True,
    ),
    SubReviewer(
        id="R4",
        name="逻辑结构拆解师",
        prompt_name="review_logic",
        system=(
            "你是学术逻辑审计师，只关注论证结构是否自洽严密。"
            "不需要领域知识，纯粹的形式逻辑检验。用中文撰写。"
        ),
        materials_needed=["story", "design", "results", "trajectory", "report"],
        mode_aware=True,
    ),
]


def run_panel(
    materials: Materials,
    mode_block: str,
    llm_caller: LLMCaller,
    prompt_loader: Callable[[str], str],
    audit_history: str = "",
    reviewers: list[SubReviewer] = None,
) -> dict[str, str]:
    """Run every SubReviewer that should_run; return {id: review_text}.

    Pure orchestrator — no file writes, no console output, no audit logging.
    The calling ReviewerAgent.run() handles persistence + UX.
    """
    if reviewers is None:
        reviewers = REVIEWERS
    reviews: dict[str, str] = {}
    for sub in reviewers:
        if not sub.should_run(materials, mode_block):
            continue
        reviews[sub.id] = sub.run(
            materials=materials,
            mode_block=mode_block,
            llm_caller=llm_caller,
            audit_history=audit_history,
            prompt_loader=prompt_loader,
        )
    return reviews
