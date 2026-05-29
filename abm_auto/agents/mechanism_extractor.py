"""
Phase 1d — Mechanism Spec Extraction.

Reads DESIGN.md (+ hypothesis.md if originate mode) and produces TWO
artefacts:

  - `mechanism_spec.md`   — free-form markdown pseudocode (audit trail,
                            human review). Always written.
  - `mechanism_spec.json` — structured MechanismSpec for the
                            TemplateGenerator. Written only when the LLM
                            output includes a parseable ```json``` block
                            matching the schema.

When the JSON block is missing or invalid, the pipeline falls back to
legacy codegen (CoderAgent writes all 7 files including the boilerplate).
When it's present and valid, TemplateGenerator emits the 5 boilerplate
files deterministically and CoderAgent's job narrows to agent.py +
environment.py only — the topology API, scenario class, data collector,
and main.py boilerplate become uncopyable-by-LLM.

Pipeline placement:
    DesignAgent → ViabilityChecker (Phase 1+1c)
      ↓
    MechanismExtractor (Phase 1d)  ← this agent
      ↓
    OddWriter (Phase 1b)
      ↓
    CoderAgent (Phase 2) — reads mechanism_spec.md + .json
"""
from __future__ import annotations

import json
import re
from typing import Optional

from rich.console import Console

from abm_auto.agents.base import BaseAgent
from abm_auto.codegen.mechanism_spec import MechanismSpec

console = Console()

_SYSTEM = (
    "You are a simulation algorithm specifier. Your job is to read an ABM "
    "design document and produce unambiguous pseudocode that pins down "
    "every behavioural decision left ambiguous. The pseudocode you write "
    "will be translated LITERALLY into Python by the downstream coder; "
    "any ambiguity becomes mechanism drift. Write in the same language as "
    "the design document (Chinese if Chinese, English if English)."
)

# Soft minimum for a meaningful spec; below this we treat output as failed.
_MIN_OUTPUT_CHARS = 400


class MechanismExtractor(BaseAgent):
    """Phase 1d: produce mechanism_spec.md.

    Idempotent: if mechanism_spec.md already exists with substantive content,
    skip (lets re-runs of partial pipelines preserve work).
    """

    def run(self) -> str:
        existing = self.workspace.read_mechanism_spec()
        if existing and len(existing.strip()) > _MIN_OUTPUT_CHARS:
            console.print(
                "  [dim]Phase 1d: mechanism_spec.md already present — skipping.[/dim]"
            )
            return existing

        console.print("[bold cyan]Phase 1d: Extracting mechanism spec...[/bold cyan]")

        design = self.workspace.read_design()
        if not design:
            console.print(
                "  [yellow]⚠ No DESIGN.md — skipping mechanism spec[/yellow]"
            )
            return ""

        hypothesis = self.workspace.read_hypothesis()

        # Build the conditional hypothesis section ourselves — keep the prompt
        # template Jinja-free (the base render_prompt only handles {{ var }},
        # and stray {% if %} tags confuse the reasoner model into returning
        # empty output).
        hypothesis_block = (
            f"### hypothesis.md (originate mode)\n{hypothesis}\n"
            if hypothesis
            else ""
        )
        template = self.load_prompt("mechanism_spec")
        prompt = self.render_prompt(
            template,
            design=design,
            hypothesis_block=hypothesis_block,
        )

        # 4096 not 2048: deepseek-reasoner consumes the budget on its chain-of-
        # thought before emitting visible output. With 2048, an empty string
        # comes back; with 4096, full ~6000-char spec. Same total cost since
        # we billable-token-count both (reasoning + completion).
        spec = self.call_llm(_SYSTEM, prompt, max_tokens=4096)
        if not spec or len(spec.strip()) < _MIN_OUTPUT_CHARS:
            console.print(
                f"  [yellow]⚠ Mechanism spec is too short ({len(spec or '')} chars) — "
                f"keeping it but quality may be low[/yellow]"
            )

        self.workspace.write_mechanism_spec(spec)
        console.print(
            f"  [green]✓ mechanism_spec.md written ({len(spec)} chars)[/green]"
        )

        # NEW (Layer 3): try to extract the JSON block for TemplateGenerator
        mech_spec_obj = _extract_mechanism_json(spec)
        json_path = self.workspace.path / "mechanism_spec.json"
        json_status = "absent"
        if mech_spec_obj is not None:
            errors = mech_spec_obj.validate()
            if errors:
                console.print(
                    f"  [yellow]⚠ mechanism_spec.json parsed but invalid "
                    f"({len(errors)} errors); template path will be skipped:[/yellow]"
                )
                for e in errors[:5]:
                    console.print(f"      [yellow]· {e}[/yellow]")
                json_status = f"invalid ({len(errors)} errors)"
            else:
                json_path.write_text(mech_spec_obj.to_json(), encoding="utf-8")
                console.print(
                    f"  [green]✓ mechanism_spec.json written — "
                    f"TemplateGenerator will own 5 boilerplate files[/green]"
                )
                json_status = "ok"
        else:
            console.print(
                "  [yellow]⚠ no ```json``` block found in LLM output — "
                "TemplateGenerator skipped, falling back to legacy codegen[/yellow]"
            )

        # Audit
        try:
            section_count = spec.count("\n## ")
            self.workspace.audit.info(
                phase="Phase 1d",
                text=f"Mechanism spec generated ({len(spec)} chars, {section_count} sections); json={json_status}",
                actor="MechanismExtractor",
                structured={
                    "length": len(spec),
                    "sections": section_count,
                    "had_hypothesis": bool(hypothesis),
                    "json_status": json_status,
                },
            )
        except Exception:
            pass

        return spec


_JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def _extract_mechanism_json(llm_output: str) -> Optional[MechanismSpec]:
    """Find and parse the ```json``` block from LLM output.

    Returns None when:
      - no fenced json block present
      - block present but not parseable as JSON
      - JSON parsed but not loadable into MechanismSpec
    The caller decides what to do with None (fall back to legacy codegen).
    """
    match = _JSON_BLOCK_RE.search(llm_output)
    if not match:
        return None
    block = match.group(1).strip()
    try:
        data = json.loads(block)
    except json.JSONDecodeError as e:
        console.print(f"  [dim]json block parse error: {e}[/dim]")
        return None
    try:
        return MechanismSpec.from_dict(data)
    except (TypeError, KeyError) as e:
        console.print(f"  [dim]json → MechanismSpec mapping error: {e}[/dim]")
        return None
