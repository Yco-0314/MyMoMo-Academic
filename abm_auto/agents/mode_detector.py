"""
Phase -1: Research Intent Detection.

Runs before everything else — before LitReviewer, before DesignAgent.
Reads story.md and classifies what the user is actually trying to do, then
produces a ResearchSpec that all downstream agents use to calibrate their
behaviour and thresholds.

Four intents (the user's goal):
  reproduce    — replicate a specific published paper/model
  originate    — model a phenomenon / question from scratch
  cross_domain — transfer a mechanism validated in one domain to another
  idea         — an early-stage spark, not yet a modelable task

The intent is inferred from story.md (or declared up front via --intent / --mode).
It DERIVES the 2-way execution `mode` that downstream agents already consume:
  reproduce → reproduce ;  originate / cross_domain / idea → originate.
So adding the richer 4-way taxonomy leaves every downstream consumer untouched.

Two intents don't proceed straight to codegen. An `idea` is too vague to model,
and any low-confidence classification shouldn't silently drive an expensive run.
In both cases the detector halts with targeted clarifying questions
(clarification.md) — the batch-pipeline form of "fall back to asking". A
user-declared intent (override) is always taken at face value and never halts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Literal

from rich.console import Console

from abm_auto.agents.base import BaseAgent

console = Console()

# The 4-way user intent → the 2-way execution mode downstream agents consume.
_INTENT_TO_MODE = {
    "reproduce": "reproduce",
    "originate": "originate",
    "cross_domain": "originate",   # novel application of a known mechanism
    "idea": "originate",           # placeholder; shaping halts before execution
}
VALID_INTENTS = tuple(_INTENT_TO_MODE)

# Below this LLM confidence, an auto-detected (non-overridden) intent halts for
# confirmation instead of driving the run on a coin-flip.
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


def derive_mode(intent: str) -> str:
    """Map a 4-way user intent to the 2-way execution mode."""
    return _INTENT_TO_MODE.get(intent, "originate")


def needs_shaping(
    intent: str,
    confidence: float,
    *,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    overridden: bool = False,
) -> bool:
    """Whether to halt for clarification rather than proceed to codegen.

    An ``idea`` is too vague to model directly — it always shapes, even when
    declared (that's the point of declaring it). A low-confidence classification
    of any other kind shouldn't silently drive an expensive run either; it asks.
    A user-declared non-idea intent is taken at face value — never halts.
    """
    if intent == "idea":
        return True
    if overridden:
        return False
    return confidence < threshold

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
    """Structured output of the intent detector. Passed to all downstream agents."""

    mode: Literal["reproduce", "originate"]   # execution path (derived from intent)

    # 4-way user intent + why it was classified that way (for the halt message).
    intent: str = ""             # reproduce | originate | cross_domain | idea
    intent_reason: str = ""

    # Reproduce-mode fields
    paper_ref: str = ""          # Detected paper title / authors / year
    paper_doi: str = ""

    # Originate-mode fields
    phenomenon: str = ""         # What phenomenon the researcher wants to model
    research_question: str = ""  # Core RQ extracted from story.md

    # Cross-domain (method-transfer) fields
    source_domain: str = ""      # where the mechanism was validated
    target_domain: str = ""      # where the user wants to apply it
    transfer_method: str = ""    # the mechanism / method being transferred

    # Shaping (idea / low-confidence): set when the pipeline should halt and ask
    needs_clarification: bool = False
    clarification_questions: list = field(default_factory=list)

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

    def __post_init__(self) -> None:
        # Back-compat: specs written before the 4-way taxonomy carry only `mode`.
        # Treat their intent as the mode they declared.
        if not self.intent:
            self.intent = self.mode

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

    def run(
        self,
        mode_override: str | None = None,
        intent_override: str | None = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> ResearchSpec:
        """Detect intent and write research_spec.json. Returns ResearchSpec.

        Args:
            mode_override: legacy "reproduce" | "originate". Treated as an
                           intent override of the same name.
            intent_override: "reproduce" | "originate" | "cross_domain" | "idea".
                           When set, skips classification — the user declares.
                           Always wins over any cached spec. (A declared "idea"
                           still routes to the shaping loop; that's its purpose.)
            confidence_threshold: below this, an auto-detected intent halts for
                           clarification instead of driving the run.
        """
        story = self.workspace.read_story()

        # Resolve an explicit override (intent flag wins; --mode maps to intent).
        declared = intent_override or mode_override
        if declared is not None:
            if intent_override is not None and intent_override not in VALID_INTENTS:
                raise ValueError(
                    f"Invalid intent_override: {intent_override!r}. "
                    f"Must be one of {VALID_INTENTS}."
                )
            if mode_override is not None and intent_override is None \
                    and mode_override not in ("reproduce", "originate"):
                raise ValueError(
                    f"Invalid mode_override: {mode_override!r}. "
                    f"Must be 'reproduce' or 'originate'."
                )

        # 1. User override always wins — write a fresh spec, ignore cache.
        if declared is not None:
            console.print(
                f"[bold cyan]Phase -1: Intent declared by user → "
                f"{declared.upper()}[/bold cyan]"
            )
            # Still extract metadata via the LLM if we have a story — but force
            # the intent. Free metadata (paper_ref / phenomenon / transfer) is
            # useful downstream even when the intent itself is fixed.
            extra: dict = {}
            if story:
                try:
                    d = self._detect(story)
                    extra = dict(
                        paper_ref=d.paper_ref, paper_doi=d.paper_doi,
                        phenomenon=d.phenomenon, research_question=d.research_question,
                        source_domain=d.source_domain, target_domain=d.target_domain,
                        transfer_method=d.transfer_method,
                        has_calibration_data=d.has_calibration_data,
                        calibration_data_path=d.calibration_data_path,
                        calibration_targets=d.calibration_targets,
                        calibration_params=d.calibration_params,
                        calibration_param_specs=d.calibration_param_specs,
                    )
                except Exception:
                    extra = {}
            spec = self._make_spec(declared, confidence=1.0,
                                   intent_reason="declared by user", **extra)
            self._finalize(spec, story, overridden=True,
                           confidence_threshold=confidence_threshold)
            return spec

        # 2. No override — reuse cached spec if present (idempotency for re-runs)
        existing = self._read_existing_spec()
        if existing:
            console.print(
                f"  [dim]Phase -1: research_spec.json already present "
                f"(intent={existing.intent}) — skipping detection. "
                f"Use --intent to override.[/dim]"
            )
            return existing

        # 3. No override, no cache → LLM classification
        if not story:
            console.print("  [yellow]⚠ No story.md — defaulting to originate[/yellow]")
            spec = self._make_spec("originate", phenomenon="(no story provided)")
            self._write_spec(spec)
            return spec

        console.print("[bold cyan]Phase -1: Detecting research intent...[/bold cyan]")
        spec = self._detect(story)
        self._finalize(spec, story, overridden=False,
                       confidence_threshold=confidence_threshold)
        return spec

    def _finalize(
        self,
        spec: ResearchSpec,
        story: str,
        *,
        overridden: bool,
        confidence_threshold: float,
    ) -> None:
        """Decide shaping, print the verdict, persist, and audit."""
        if needs_shaping(spec.intent, spec.confidence,
                         threshold=confidence_threshold, overridden=overridden):
            spec.needs_clarification = True
            if story and not spec.clarification_questions:
                spec.clarification_questions = self._make_clarification(story, spec)
            self._write_spec(spec)
            self._write_clarification(spec)
            self._announce_shaping(spec)
        else:
            self._write_spec(spec)
            self._announce(spec)
        try:
            self.workspace.audit.info(
                phase="Phase -1",
                text=(
                    f"Research intent: {spec.intent} → mode {spec.mode} "
                    f"(confidence={spec.confidence:.2f}"
                    f"{', user-declared' if overridden else ''}"
                    f"{', NEEDS CLARIFICATION' if spec.needs_clarification else ''})"
                ),
                actor="ModeDetector",
                structured={
                    "intent": spec.intent, "mode": spec.mode,
                    "confidence": spec.confidence,
                    "needs_clarification": spec.needs_clarification,
                    "user_declared": overridden,
                },
            )
        except Exception:
            pass

    def _announce(self, spec: ResearchSpec) -> None:
        labels = {
            "reproduce": "[green]REPRODUCE[/green]",
            "originate": "[blue]ORIGINATE[/blue]",
            "cross_domain": "[magenta]CROSS-DOMAIN[/magenta]",
            "idea": "[yellow]IDEA[/yellow]",
        }
        console.print(
            f"  {labels.get(spec.intent, spec.intent)} "
            f"[dim](confidence={spec.confidence:.0%})[/dim]"
        )
        if spec.intent == "reproduce" and spec.paper_ref:
            console.print(f"  [dim]Paper: {spec.paper_ref}[/dim]")
        elif spec.intent == "cross_domain" and spec.transfer_method:
            console.print(
                f"  [dim]Transfer: {spec.transfer_method} "
                f"({spec.source_domain or '?'} → {spec.target_domain or '?'})[/dim]"
            )
        elif spec.phenomenon:
            console.print(f"  [dim]Phenomenon: {spec.phenomenon[:80]}[/dim]")

    def _announce_shaping(self, spec: ResearchSpec) -> None:
        why = ("reads as an early-stage idea" if spec.intent == "idea"
               else f"intent is ambiguous (confidence {spec.confidence:.0%})")
        console.print(
            f"  [yellow]⏸ Phase -1: {why}.[/yellow] "
            f"[dim]Best guess: {spec.intent}"
            f"{' — ' + spec.intent_reason if spec.intent_reason else ''}.[/dim]"
        )
        if spec.clarification_questions:
            console.print("  [yellow]To sharpen it into a modelable task, answer in "
                          "story.md (see clarification.md):[/yellow]")
            for q in spec.clarification_questions:
                console.print(f"    [dim]• {q}[/dim]")
        console.print("  [dim]Or declare it: re-run with "
                      "--intent reproduce|originate|cross_domain.[/dim]")

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
            "Classify the user's INTENT into exactly one of four categories.\n\n"
            "### reproduce\n"
            "Replicate an EXISTING published model/paper. The hypothesis is fixed "
            "by the cited work — the task is implementation fidelity.\n"
            "Strong signals (any ONE is usually decisive):\n"
            "  1. Specific paper citation with author + year (e.g. 'Schelling 1971')\n"
            "  2. A named classic model ('Schelling segregation', 'El Farol Bar', "
            "'Sugarscape', 'Wolf-Sheep', 'Iterated Prisoner Dilemma')\n"
            "  3. Verbs: 'reproduce', 'replicate', 'recreate', '复现', '重现'\n"
            "  4. DOI mentioned\n"
            "Counter-signal: detailed mechanism descriptions ALONE do NOT make it "
            "originate — a reproduction naturally includes detailed rules from the "
            "cited paper.\n\n"
            "### originate\n"
            "Build a NEW model from a phenomenon or research question. NO specific "
            "paper is recreated, NO method explicitly borrowed from another field.\n"
            "Strong signals: 'I want to model', 'I observe', 'how does X cause Y', "
            "an open research question, acknowledged uncertainty about mechanism.\n\n"
            "### cross_domain\n"
            "Transfer a mechanism/method VALIDATED IN ONE DOMAIN to a DIFFERENT "
            "domain. The method is borrowed, the application is new.\n"
            "Strong signals: 'apply the X model from <field A> to <field B>', "
            "'use <method> (from physics/biology/economics) to study <other field>', "
            "naming both a source method and a different target phenomenon.\n\n"
            "### idea\n"
            "An early-stage spark, NOT yet a modelable task: a one-liner, a vague "
            "'what if', a topic with no agents / no mechanism / no measurable "
            "outcome specified. Too underspecified to code a faithful model.\n"
            "Signals: very short, no mechanism, no agents named, no outcome, "
            "'I'm curious about…', 'something like…', open brainstorm.\n\n"
            "### Disambiguation\n"
            "  - 'Reproduce Smith 2020 and extend' → reproduce (anchor wins)\n"
            "  - 'Apply Smith 2020's opinion model to traffic' → cross_domain\n"
            "  - 'I want to study Z' (Z well-specified, no paper) → originate\n"
            "  - 'I wonder if cities segregate like birds flock' → idea (no mechanism)\n"
            "Set confidence < 0.7 when genuinely torn between two categories.\n\n"
            "Return JSON:\n"
            "{\n"
            '  "intent": "reproduce" | "originate" | "cross_domain" | "idea",\n'
            '  "intent_reason": "one short sentence — the deciding signal",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "paper_ref": "Author Year Title (if reproduce, else empty)",\n'
            '  "paper_doi": "DOI if found, else empty",\n'
            '  "phenomenon": "1-sentence description (if originate, else empty)",\n'
            '  "research_question": "core RQ (else empty)",\n'
            '  "source_domain": "(cross_domain) where the method was validated, else empty",\n'
            '  "target_domain": "(cross_domain) where to apply it, else empty",\n'
            '  "transfer_method": "(cross_domain) the mechanism being transferred, else empty",\n'
            '  "has_calibration_data": true/false,\n'
            '  "calibration_data_path": "path (e.g. data/observed.csv), or empty",\n'
            '  "calibration_targets": ["metric1", "metric2"],   // OUTPUT columns the simulation must reproduce\n'
            '  "calibration_param_specs": [                      // INPUT params to ESTIMATE, with range + unit.\n'
            '    {                                               // Look for tables like "Parameters to estimate" in story.md.\n'
            '      "name": "virus_spread_chance",                // EXACT name as used in story.md\n'
            '      "min": 0, "max": 20,                          // bounds from story\n'
            '      "unit": "percent"                             // "percent" | "probability" | "count" | "rate" | other\n'
            '    }                                               // Empty list [] if no calibration.\n'
            '  ]\n'
            "}"
        )

        try:
            raw = self.call_llm(system, prompt, max_tokens=512)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            parsed = json.loads(raw)
            intent = parsed.get("intent", "originate")
            if intent not in VALID_INTENTS:
                intent = "originate"
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
                intent,
                intent_reason=parsed.get("intent_reason", ""),
                paper_ref=parsed.get("paper_ref", ""),
                paper_doi=parsed.get("paper_doi", ""),
                phenomenon=parsed.get("phenomenon", ""),
                research_question=parsed.get("research_question", ""),
                source_domain=parsed.get("source_domain", ""),
                target_domain=parsed.get("target_domain", ""),
                transfer_method=parsed.get("transfer_method", ""),
                has_calibration_data=bool(parsed.get("has_calibration_data", False)),
                calibration_data_path=parsed.get("calibration_data_path", ""),
                calibration_targets=list(parsed.get("calibration_targets", []) or []),
                calibration_params=calibration_params,
                calibration_param_specs=param_specs,
                confidence=float(parsed.get("confidence", 0.8)),
            )
        except Exception as e:
            console.print(f"  [yellow]⚠ Intent detection failed ({e}) — defaulting to originate[/yellow]")
            return self._make_spec("originate", confidence=0.5,
                                   intent_reason="detection failed; defaulted")

    def _make_spec(self, intent: str, **kwargs) -> ResearchSpec:
        mode = derive_mode(intent)
        thresholds = _THRESHOLDS[mode]
        return ResearchSpec(
            mode=mode,
            intent=intent,
            viability_max_assumptions=thresholds["max_assumptions"],
            viability_max_missing_elements=thresholds["max_missing_elements"],
            viability_llm_question=thresholds["llm_question"],
            **kwargs,
        )

    # ── shaping (idea / low-confidence) ─────────────────────────────────────────

    def _make_clarification(self, story: str, spec: ResearchSpec) -> list:
        """Generate 3-5 targeted questions that would turn this story into a
        modelable task. Falls back to a generic checklist on any LLM failure."""
        system = (
            "You help researchers sharpen a vague modeling idea into a concrete "
            "agent-based-model spec. Output ONLY a JSON list of 3-5 short questions."
        )
        prompt = (
            f"## story.md\n{story[:3000]}\n\n"
            f"This was classified as '{spec.intent}' "
            f"(confidence {spec.confidence:.0%}): {spec.intent_reason}\n\n"
            "Ask the 3-5 MOST decisive questions whose answers would make this "
            "codeable as an ABM: who are the agents, what do they do each step, "
            "what drives their decisions, what outcome is measured, and (if it "
            "resembles existing work) which paper/method anchors it.\n"
            'Return JSON: ["question 1", "question 2", ...]'
        )
        try:
            raw = self.call_llm(system, prompt, max_tokens=400).strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            questions = json.loads(raw)
            questions = [str(q).strip() for q in questions if str(q).strip()]
            if questions:
                return questions[:5]
        except Exception:
            pass
        return [
            "Who are the agents, and how many?",
            "What does each agent do on a single time step?",
            "What drives an agent's decisions (its rule or payoff)?",
            "What measurable outcome should the model produce?",
            "Is there a paper or known model this resembles?",
        ]

    def _write_clarification(self, spec: ResearchSpec) -> None:
        lines = [
            "# Clarification needed\n",
            f"The pipeline paused at Phase -1. Your story was read as "
            f"**{spec.intent}** (confidence {spec.confidence:.0%})"
            + (f" — {spec.intent_reason}" if spec.intent_reason else "") + ".\n",
            "It isn't yet specified enough to model faithfully. Answer these in "
            "`story.md`, then re-run:\n",
        ]
        for q in spec.clarification_questions:
            lines.append(f"- {q}")
        lines.append(
            "\nOr, if you already know the intent, skip this by re-running with "
            "`--intent reproduce|originate|cross_domain`."
        )
        (self.workspace.path / "clarification.md").write_text(
            "\n".join(lines), encoding="utf-8"
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
