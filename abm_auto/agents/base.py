from __future__ import annotations
import re
import time
from pathlib import Path

import anthropic
from rich.console import Console

from abm_auto.config import DEFAULT_MODEL, PROMPTS_DIR, KNOWLEDGE_DIR
from abm_auto.runner.workspace import Workspace

console = Console()


LANG_DIRECTIVES = {
    "en": (
        "Write ALL output in English. Use standard academic English conventions. "
        "Follow IMRAD structure where applicable. Be precise and formal."
    ),
    "zh": "用中文撰写所有输出。",
}

# Section headers used in pipeline report assembly — keyed by lang
SECTION_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "sensitivity": "## Sensitivity Analysis ({method})",
        "trajectory": "## Trajectory Analysis",
        "trajectory_system": (
            "You are a computational social scientist specializing in ABM trajectory analysis. "
            "Focus on emergent phenomena and phase transitions."
        ),
    },
    "zh": {
        "sensitivity": "## 敏感性分析（{method}）",
        "trajectory": "## 轨迹分析",
        "trajectory_system": (
            "你是一名专注于ABM轨迹分析的计算社会科学家。"
            "重点分析涌现现象和相变过程。"
        ),
    },
}


class BaseAgent:
    """Base class for all pipeline agents."""

    def __init__(self, client: anthropic.Anthropic, workspace: Workspace,
                 model: str = DEFAULT_MODEL, lang: str = "zh"):
        self.client = client
        self.workspace = workspace
        self.model = model
        self.lang = lang

    def load_prompt(self, name: str) -> str:
        """Load a prompt template from the prompts directory."""
        path = PROMPTS_DIR / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        return path.read_text(encoding="utf-8")

    def load_knowledge(self, name: str) -> str:
        """Load a reference document from the knowledge directory."""
        path = KNOWLEDGE_DIR / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Knowledge file not found: {path}")
        return path.read_text(encoding="utf-8")

    def call_llm(self, system: str, user: str, max_tokens: int = 8192) -> str:
        """Call Claude and return the text response. Injects language directive. Retries on transient errors."""
        lang_dir = LANG_DIRECTIVES.get(self.lang, LANG_DIRECTIVES["en"])
        full_system = f"{system}\n\n{lang_dir}"
        console.print(f"  [dim]→ LLM ({self.model}, lang={self.lang}, max_tokens={max_tokens})[/dim]")

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=full_system,
                    messages=[{"role": "user", "content": user}],
                )
                return response.content[0].text
            except anthropic.RateLimitError as e:
                # HTTP 429 — back off and retry; always retryable
                wait = min(30 * (2 ** attempt), 300)  # 30s, 60s, 120s, 240s, 300s
                console.print(f"  [yellow]⚠ Rate limit ({attempt + 1}/{max_retries}), waiting {wait}s...[/yellow]")
                time.sleep(wait)
                if attempt == max_retries - 1:
                    raise
            except anthropic.BadRequestError as e:
                msg = str(e)
                if "413" in msg or "Payload Too Large" in msg:
                    # Truncate and retry once
                    if attempt == 0:
                        console.print("  [yellow]⚠ Request too large, truncating and retrying...[/yellow]")
                        user = user[: int(len(user) * 0.6)]
                        continue
                # Quota exhausted or other non-retryable 400 — propagate immediately
                if "workspace API usage limits" in msg or "quota" in msg.lower():
                    console.print(f"  [red]✗ API quota exhausted — {msg[:200]}[/red]")
                raise
            except (anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
                if attempt < max_retries - 1:
                    wait = min(10 * (2 ** attempt), 120)  # exponential: 10, 20, 40, 80
                    console.print(f"  [yellow]⚠ API error ({attempt + 1}/{max_retries}), retrying in {wait}s... ({e})[/yellow]")
                    time.sleep(wait)
                else:
                    raise

    def render_prompt(self, template: str, **kwargs) -> str:
        """Simple {{ var }} substitution."""
        for key, value in kwargs.items():
            template = template.replace("{{ " + key + " }}", str(value) if value else "")
            template = template.replace("{{" + key + "}}", str(value) if value else "")
        return template

    def call_llm_with_prompt(
        self,
        prompt_name: str,
        system: str,
        max_tokens: int = 8192,
        **context,
    ) -> str:
        """Load a prompt template, render it with *context*, and call the LLM.

        Replaces the repeated load_prompt() → .replace() chain → call_llm()
        pattern found across AnalyzerAgent, OptimizerAgent, ReporterAgent, etc.

        Args:
            prompt_name: filename stem under PROMPTS_DIR (e.g. "analyze").
            system: system-prompt string passed to the LLM.
            max_tokens: forwarded to call_llm().
            **context: template variables substituted into {{ key }} placeholders.
        """
        template = self.load_prompt(prompt_name)
        prompt = self.render_prompt(template, **context)
        return self.call_llm(system, prompt, max_tokens=max_tokens)
