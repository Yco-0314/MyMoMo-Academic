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

        # ── Layer 3 (two-stage extraction) ──
        # Stage 1 above: free-form markdown spec (rich pseudocode, audit-friendly)
        # Stage 2 here:  focused JSON extractor → mechanism_spec.json
        #
        # Why two stages: a single LLM call asked for both markdown AND JSON
        # consistently dropped the JSON (3 dogfoods confirmed). Reasoner-class
        # models spend their budget on the markdown pseudocode and treat the
        # appended JSON requirement as optional. Splitting into two calls gives
        # each prompt narrow focus — Call 2 emits ONLY JSON.
        mech_spec_obj, json_status = self._extract_json_spec(spec, design)
        json_path = self.workspace.path / "mechanism_spec.json"
        if mech_spec_obj is not None:
            json_path.write_text(mech_spec_obj.to_json(), encoding="utf-8")
            console.print(
                f"  [green]✓ mechanism_spec.json written — "
                f"TemplateGenerator will own 5 boilerplate files[/green]"
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

    # ── Stage-2 JSON extraction ──

    _JSON_SYSTEM = (
        "You are a JSON-only extractor. Your output is parsed mechanically. "
        "Emit ONE fenced ```json``` block containing one JSON object that "
        "matches the schema in the user prompt. Nothing else — no prose, "
        "no commentary, no other code fences. Strict JSON: double quotes, "
        "no trailing commas, no Python literals (true/false/null only)."
    )

    def _extract_json_spec(
        self, markdown_spec: str, design: str,
    ) -> tuple[Optional[MechanismSpec], str]:
        """Stage 2: focused LLM call that emits ONLY mechanism_spec JSON.

        Returns (MechanismSpec | None, status_string). The status is one
        of: "ok", "no_json_block", "parse_error", "invalid (N errors)",
        "exception:Class". On any non-"ok" status, returns None for the
        spec; pipeline falls back to legacy codegen.

        One retry is permitted — if the first call returns malformed JSON,
        we prepend the parse error to a second call's prompt as feedback.
        """
        attempts: list[str] = []
        feedback: str = ""
        for attempt_idx in range(2):
            prompt_template = self.load_prompt("mechanism_spec_json")
            prompt = self.render_prompt(
                prompt_template,
                mechanism_md=markdown_spec,
                design=design,
            )
            if feedback:
                prompt = (
                    f"## ⚠ Previous attempt failed parsing\n\n"
                    f"{feedback}\n\n"
                    f"Fix the error and re-emit. Same schema applies.\n\n"
                    + prompt
                )
            try:
                # 4096 not 2048: deepseek-reasoner spends its budget on
                # chain-of-thought reasoning before emitting visible output.
                # First dogfood with 2048 returned empty string both attempts
                # — bumping to 4096 (same as Stage-1) gives the model headroom
                # to think then emit the JSON.
                raw = self.call_llm(self._JSON_SYSTEM, prompt, max_tokens=4096)
            except Exception as e:
                console.print(
                    f"  [yellow]⚠ Stage-2 LLM call raised "
                    f"({type(e).__name__}): {e}[/yellow]"
                )
                return None, f"exception:{type(e).__name__}"
            attempts.append(raw or "")
            parsed, status, parse_error = _parse_mechanism_json(raw)
            if status == "ok":
                # Final structural validation against MechanismSpec invariants
                errors = parsed.validate()
                if not errors:
                    return parsed, "ok"
                console.print(
                    f"  [yellow]⚠ Stage-2 JSON parsed but invalid "
                    f"({len(errors)} errors):[/yellow]"
                )
                for e in errors[:5]:
                    console.print(f"      [yellow]· {e}[/yellow]")
                if attempt_idx == 0:
                    feedback = (
                        "The JSON parsed, but MechanismSpec validation failed:\n"
                        + "\n".join(f"- {e}" for e in errors)
                    )
                    continue
                return None, f"invalid ({len(errors)} errors)"
            # parse failed — feed the error back on retry
            console.print(
                f"  [yellow]⚠ Stage-2 JSON parse failed: {parse_error}[/yellow]"
            )
            if attempt_idx == 0:
                feedback = parse_error
                continue
            return None, status
        return None, "no_json_block"


_JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
_BARE_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_mechanism_json(
    llm_output: str,
) -> tuple[Optional[MechanismSpec], str, str]:
    """Find + parse the JSON spec from a Stage-2 LLM response.

    Returns (spec, status, parse_error). status ∈ {"ok", "no_json_block",
    "parse_error", "mapping_error"}. spec is None on any non-ok status.

    Tries fenced ```json``` block first, then a bare top-level {…} as
    fallback (some models forget the fence even when asked).
    """
    if not llm_output:
        return None, "no_json_block", "LLM returned empty output"
    match = _JSON_BLOCK_RE.search(llm_output)
    block: Optional[str] = None
    if match:
        block = match.group(1).strip()
    else:
        # Fallback: look for a top-level {...} the model may have emitted bare
        bare = _BARE_JSON_RE.search(llm_output)
        if bare:
            block = bare.group(0).strip()
    if block is None:
        return None, "no_json_block", "no ```json``` block or bare {…} found"
    try:
        data = json.loads(block)
    except json.JSONDecodeError as e:
        return None, "parse_error", f"JSONDecodeError: {e.msg} at line {e.lineno} col {e.colno}"
    try:
        return MechanismSpec.from_dict(data), "ok", ""
    except (TypeError, KeyError, ValueError) as e:
        return None, "mapping_error", f"{type(e).__name__}: {e}"
