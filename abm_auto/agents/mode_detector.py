"""
Phase -1: Research Mode Detection.

Runs before everything else — before LitReviewer, before DesignAgent.
Reads story.md and infers whether this is a reproduction task or an
original research task, then produces a ResearchSpec that all downstream
agents use to calibrate their behaviour and thresholds.

Two modes:
  reproduce  — story.md describes an existing paper to replicate
  originate  — researcher describes a phenomenon / question to model from scratch

The mode is NEVER declared by the user. It is inferred from story.md signals:
  Reproduce signals: paper title, author, year, DOI, "reproduce", "replicate",
                     "based on X et al.", specific empirical findings cited.
  Originate signals: phenomenon description language, "I want to model",
                     "explore how", "investigate", no specific paper reference.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Literal

from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()

# Per-mode ViabilityChecker thresholds (passed through ResearchSpec so the
# gate doesn't need to know about mode itself).
_THRESHOLDS = {
    "reproduce": {
        "max_assumptions": 5,
        "max_missing_elements": 3,
        "llm_question": (
            "Is this design SEMANTICALLY consistent with faithful reproduction "
            "of the source paper?\n\n"
            "IMPORTANT — what NOT to check (covered by separate rule checks):\n"
            "  • Completeness of 8 required sections — checked by structural rule\n"
            "  • AI-ASSUMPTION tag count — checked by counting rule\n"
            "  • Document length / truncation — if rule checks pass, design is "
            "structurally complete\n\n"
            "FAIL only on these semantic problems:\n"
            "  (a) Agent behaviour is completely unspecified (no rules at all)\n"
            "  (b) The design contradicts what the source paper actually does\n"
            "  (c) All parameters are placeholders with no justification "
            "(none traced to story / lit / paper-canonical)\n\n"
            "If none of (a)/(b)/(c) apply, return PASS."
        ),
    },
    "originate": {
        "max_assumptions": 15,   # More assumptions are expected and acceptable
        "max_missing_elements": 6,
        "llm_question": (
            "Is this design a SEMANTICALLY valid implementation of an original-research ABM?\n\n"
            "IMPORTANT — what NOT to check (covered by separate rule checks):\n"
            "  • Completeness of the 8 required sections — checked by structural rule\n"
            "  • Number of AI-ASSUMPTION tags — checked by counting rule\n"
            "  • Document length / truncation — if rule checks pass, the design is "
            "structurally complete; do NOT claim truncation just because you see a "
            "section that mentions something briefly\n\n"
            "ORIGINATE-mode context: the design SHOULD anchor closely on a recommended "
            "hypothesis (produced upstream by HypothesisAgent). Restating and "
            "operationalising the hypothesis is the correct workflow, NOT derivative "
            "behaviour. Originality was already decided at the hypothesis stage.\n\n"
            "FAIL only on these three semantic problems:\n"
            "  (a) The phenomenon is fundamentally not agent-based (purely qualitative, "
            "      no individuals interacting)\n"
            "  (b) The design has zero measurable outputs (no DataCollector columns, "
            "      no metrics to track)\n"
            "  (c) The design's mechanism CONTRADICTS the recommended hypothesis "
            "      (e.g. hypothesis says 'observation drives cascade' but design "
            "      implements pure signal-based decisions)\n\n"
            "If none of (a)/(b)/(c) apply, return PASS even if you have minor stylistic concerns."
        ),
    },
}


@dataclass
class ResearchSpec:
    """Structured output of ModeDetector. Passed to all downstream agents."""

    mode: Literal["reproduce", "originate"]

    # Reproduce-mode fields
    paper_ref: str = ""          # Detected paper title / authors / year
    paper_doi: str = ""

    # Originate-mode fields
    phenomenon: str = ""         # What phenomenon the researcher wants to model
    research_question: str = ""  # Core RQ extracted from story.md

    # Shared
    has_calibration_data: bool = False   # story.md mentions observable / empirical data
    calibration_data_path: str = ""      # path mentioned in story.md (e.g. "data/observed.csv")
    calibration_targets: list = field(default_factory=list)  # OUTPUT columns to fit (e.g. ["infected"])
    # INPUT params to estimate. Two parallel fields:
    #   - calibration_params: list[str] of names — for backwards compat & quick lookup
    #   - calibration_param_specs: list[dict] each {name, min, max, unit, default?}
    #     — carries range/unit info so CoderAgent uses the right scale and
    #       BayesianCalibrator uses spec bounds (not CSV-inferred ±50%).
    # The two MUST stay synchronised: every entry in specs has its name in params.
    calibration_params: list = field(default_factory=list)
    calibration_param_specs: list = field(default_factory=list)
    # External simulator — when set, pipeline copies this dir into workspace/model/
    # and skips Phase 1d (MechanismExtractor), Phase 2 (CoderAgent), Phase 3
    # (VerifierAgent). Lets users plug in a hand-crafted or third-party Python
    # model directly, bypassing LLM codegen — useful for reproducing NetLogo
    # models (where codegen introduces unavoidable tick-semantics drift), and
    # for fast iteration on calibration algorithms (no codegen randomness).
    # Set via CLI flag --external-model PATH or Pipeline constructor.
    external_model_path: str = ""
    confidence: float = 1.0             # LLM confidence in mode detection (0–1)

    # Thresholds for ViabilityChecker (set from _THRESHOLDS[mode])
    viability_max_assumptions: int = 5
    viability_max_missing_elements: int = 3
    viability_llm_question: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ResearchSpec":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class ModeDetector(BaseAgent):
    """
    Phase -1: infer research mode from story.md.

    Single LLM call → ResearchSpec.
    Writes research_spec.json to workspace for downstream agents to read.
    """

    def run(self, mode_override: str | None = None) -> ResearchSpec:
        """Detect mode and write research_spec.json. Returns ResearchSpec.

        Args:
            mode_override: If set ("reproduce" or "originate"), skips LLM
                           detection entirely. The user knows what they wrote
                           in story.md better than any LLM judge — when in doubt,
                           let them declare. Always wins over any cached spec.
        """
        story = self.workspace.read_story()

        # 1. User override always wins — write a fresh spec, ignore cache.
        if mode_override:
            if mode_override not in ("reproduce", "originate"):
                raise ValueError(
                    f"Invalid mode_override: {mode_override!r}. "
                    f"Must be 'reproduce' or 'originate'."
                )
            console.print(
                f"[bold cyan]Phase -1: Mode forced by user → "
                f"{mode_override.upper()}[/bold cyan]"
            )
            # Still extract metadata via LLM if we have a story — but force the
            # mode field. Free metadata (paper_ref / phenomenon) is useful for
            # downstream agents even when mode itself is fixed.
            if story:
                try:
                    detected = self._detect(story)
                    spec = self._make_spec(
                        mode=mode_override,
                        paper_ref=detected.paper_ref,
                        paper_doi=detected.paper_doi,
                        phenomenon=detected.phenomenon,
                        research_question=detected.research_question,
                        has_calibration_data=detected.has_calibration_data,
                        calibration_data_path=detected.calibration_data_path,
                        calibration_targets=detected.calibration_targets,
                        calibration_params=detected.calibration_params,
                        calibration_param_specs=detected.calibration_param_specs,
                        confidence=1.0,
                    )
                except Exception:
                    spec = self._make_spec(mode_override)
            else:
                spec = self._make_spec(mode_override)
            self._write_spec(spec)
            if spec.paper_ref:
                console.print(f"  [dim]Paper: {spec.paper_ref}[/dim]")
            elif spec.phenomenon:
                console.print(f"  [dim]Phenomenon: {spec.phenomenon[:80]}[/dim]")
            # Audit ledger entry for the forced detection
            try:
                self.workspace.audit.info(
                    phase="Phase -1",
                    text=(
                        f"Research mode FORCED by --mode flag: {spec.mode} "
                        f"(user override; LLM detection skipped)"
                    ),
                    actor="ModeDetector",
                    structured={"mode": spec.mode, "user_forced": True},
                )
            except Exception:
                pass
            return spec

        # 2. No override — reuse cached spec if present (idempotency for re-runs)
        existing = self._read_existing_spec()
        if existing:
            console.print(
                f"  [dim]Phase -1: research_spec.json already present "
                f"(mode={existing.mode}) — skipping detection. "
                f"Use --mode to override.[/dim]"
            )
            return existing

        # 3. No override, no cache → LLM detection
        if not story:
            console.print("  [yellow]⚠ No story.md — defaulting to originate mode[/yellow]")
            return self._make_spec("originate", phenomenon="(no story provided)")

        console.print("[bold cyan]Phase -1: Detecting research mode...[/bold cyan]")
        spec = self._detect(story)
        self._write_spec(spec)

        mode_label = "[green]REPRODUCE[/green]" if spec.mode == "reproduce" else "[blue]ORIGINATE[/blue]"
        console.print(
            f"  {mode_label} mode detected "
            f"[dim](confidence={spec.confidence:.0%})[/dim]"
        )
        if spec.mode == "reproduce" and spec.paper_ref:
            console.print(f"  [dim]Paper: {spec.paper_ref}[/dim]")
        elif spec.mode == "originate" and spec.phenomenon:
            console.print(f"  [dim]Phenomenon: {spec.phenomenon[:80]}[/dim]")

        # Audit: record mode detection as an info event for downstream phases
        self.workspace.audit.info(
            phase="Phase -1",
            text=(
                f"Research mode detected: {spec.mode} "
                f"(confidence={spec.confidence:.2f}); "
                f"{'paper_ref=' + spec.paper_ref if spec.mode == 'reproduce' else 'phenomenon=' + spec.phenomenon[:60]}"
            ),
            actor="ModeDetector",
            structured={
                "mode": spec.mode,
                "confidence": spec.confidence,
                "has_calibration_data": spec.has_calibration_data,
            },
        )

        return spec

    # ── internal ──────────────────────────────────────────────────────────────

    def _detect(self, story: str) -> ResearchSpec:
        system = (
            "You are a research pipeline configurator. "
            "Read a story.md and classify the research task. "
            "Output ONLY valid JSON, no other text."
        )
        prompt = (
            "## story.md\n"
            # 4000 (was 2000) — calibration_params often appears in a
            # "Parameters to estimate" table that lives ~2-3KB into the doc.
            # The 2000-char limit silently hid it from the LLM.
            f"{story[:4000]}\n\n"
            "Classify this into one of two modes.\n\n"
            "### REPRODUCE\n"
            "The story describes an EXISTING published model/paper that the "
            "researcher wants to recreate in code. The hypothesis is already "
            "fixed by the cited work — the task is implementation fidelity.\n\n"
            "STRONG reproduce signals (any ONE is usually decisive):\n"
            "  1. Specific paper citation with author + year (e.g. 'Schelling 1971', "
            "'Arthur (1994)', 'Axelrod and Hamilton 1981')\n"
            "  2. A named classic model ('Schelling segregation', 'El Farol Bar Problem', "
            "'Sugarscape', 'Wolf-Sheep Predation', 'Iterated Prisoner Dilemma')\n"
            "  3. Explicit verbs: 'reproduce', 'replicate', 'recreate', '复现', '重现'\n"
            "  4. DOI mentioned\n"
            "  5. Story phrased as 'Based on X et al., simulate Y' — even if Y is "
            "described in detail, the paper anchor makes it REPRODUCE.\n\n"
            "Counter-signal: detailed mechanism descriptions ALONE do NOT make it "
            "originate. Classic-model reproductions naturally include detailed agent "
            "rules — that's because the rules come from the cited paper, not because "
            "the researcher invented them. If you see a paper citation OR a named "
            "classic model, default to REPRODUCE unless the story explicitly says "
            "'I want to extend/modify' it.\n\n"
            "### ORIGINATE\n"
            "The researcher is building a NEW model from a phenomenon or research "
            "question. NO specific paper is being recreated.\n\n"
            "Strong originate signals:\n"
            "  1. 'I want to model', 'I observe', 'how does X cause Y'\n"
            "  2. Phenomenon described without citing a specific paper that already "
            "models it\n"
            "  3. Open research questions left for the model to answer\n"
            "  4. Explicit acknowledgement of uncertainty about mechanism\n\n"
            "### Disambiguation rule\n"
            "When BOTH signals appear, weight by intent:\n"
            "  - 'Reproduce Smith 2020 and extend with X' → REPRODUCE (extension is "
            "secondary)\n"
            "  - 'Like Smith 2020 but applied to Y' → REPRODUCE (Smith is the anchor)\n"
            "  - 'Inspired by Smith 2020, I want to study Z' → ORIGINATE only if Z is "
            "substantially different from Smith's claim\n\n"
            "Return JSON:\n"
            "{\n"
            '  "mode": "reproduce" or "originate",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "paper_ref": "Author Year Title (if reproduce, else empty)",\n'
            '  "paper_doi": "DOI if found, else empty",\n'
            '  "phenomenon": "1-sentence description (if originate, else empty)",\n'
            '  "research_question": "core RQ (if originate, else empty)",\n'
            '  "has_calibration_data": true/false,\n'
            '  "calibration_data_path": "path (e.g. data/observed.csv), or empty",\n'
            '  "calibration_targets": ["metric1", "metric2"],   // OUTPUT columns the simulation must reproduce (e.g. infected, susceptible)\n'
            '  "calibration_param_specs": [                      // INPUT params to ESTIMATE, with range + unit.\n'
            '    {                                               // Look for tables like "Parameters to estimate" or "Range / Unit" in story.md.\n'
            '      "name": "virus_spread_chance",                // EXACT name as used in story.md\n'
            '      "min": 0,                                     // lower bound from story\n'
            '      "max": 20,                                    // upper bound from story\n'
            '      "unit": "percent"                             // "percent" | "probability" | "count" | "rate" | other (verbatim from story)\n'
            '    }                                               // Empty list [] if no calibration. Only params the user explicitly asks to estimate;\n'
            '  ]                                                 // structural params (num_agents, periods) belong elsewhere.\n'
            "}"
        )

        try:
            raw = self.call_llm(system, prompt, max_tokens=512)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            parsed = json.loads(raw)
            mode = parsed.get("mode", "originate")
            if mode not in ("reproduce", "originate"):
                mode = "originate"
            # New richer format: calibration_param_specs (list of dicts).
            # Backwards-compat: fall back to calibration_params (list of names).
            param_specs = list(parsed.get("calibration_param_specs", []) or [])
            # Validate spec dicts: keep only well-formed ones.
            param_specs = [
                s for s in param_specs
                if isinstance(s, dict) and s.get("name")
            ]
            # Derive flat name list from specs (always synchronised)
            param_names_from_specs = [s["name"] for s in param_specs]
            # If LLM gave us only the legacy field, lift it
            legacy_names = list(parsed.get("calibration_params", []) or [])
            calibration_params = param_names_from_specs or legacy_names

            return self._make_spec(
                mode=mode,
                paper_ref=parsed.get("paper_ref", ""),
                paper_doi=parsed.get("paper_doi", ""),
                phenomenon=parsed.get("phenomenon", ""),
                research_question=parsed.get("research_question", ""),
                has_calibration_data=bool(parsed.get("has_calibration_data", False)),
                calibration_data_path=parsed.get("calibration_data_path", ""),
                calibration_targets=list(parsed.get("calibration_targets", []) or []),
                calibration_params=calibration_params,
                calibration_param_specs=param_specs,
                confidence=float(parsed.get("confidence", 0.8)),
            )
        except Exception as e:
            console.print(f"  [yellow]⚠ Mode detection failed ({e}) — defaulting to originate[/yellow]")
            return self._make_spec("originate")

    def _make_spec(
        self,
        mode: Literal["reproduce", "originate"],
        **kwargs,
    ) -> ResearchSpec:
        thresholds = _THRESHOLDS[mode]
        return ResearchSpec(
            mode=mode,
            viability_max_assumptions=thresholds["max_assumptions"],
            viability_max_missing_elements=thresholds["max_missing_elements"],
            viability_llm_question=thresholds["llm_question"],
            **kwargs,
        )

    def _write_spec(self, spec: ResearchSpec) -> None:
        spec_path = self.workspace.path / "research_spec.json"
        spec_path.write_text(
            json.dumps(spec.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _read_existing_spec(self) -> ResearchSpec | None:
        spec_path = self.workspace.path / "research_spec.json"
        if not spec_path.exists():
            return None
        try:
            data = json.loads(spec_path.read_text(encoding="utf-8"))
            return ResearchSpec.from_dict(data)
        except Exception:
            return None
