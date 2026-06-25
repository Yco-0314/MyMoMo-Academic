"""ADR-021 D4 — the inline `Critic` seam (per-phase soft adversarial gate).

End "review only at the end" (ADR-021 pain #4): give the anti-fabrication discipline
reach at Phase granularity. A `Critic` runs after a named Phase and emits structured,
**verifiable** `(violations, evidence)` — never free-form prose.

Anti-fabrication 命门 (ADR-013, generator ≠ gate): the Critic SPLITS generate/judge.
An LLM *generates* candidate findings; a deterministic `_verify` keeps only the ones
whose evidence is structurally confirmed against the real workspace artefact (the
claimed quote must literally appear in it). The LLM's word alone never becomes a
`Violation`. The Critic binds to the **refutation** tier — it can reject obvious
defects but never self-certifies the output "correct".

Naming note: `Critic` is ADR-021 candidate #7 — the name may change before merge; the
seam shape (structured verifiable violations, soft per-Phase gate) is what is locked.

Additive: lives in agents/. Zero changes to runtime/codegen/calibration.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from abm_auto.agents.base import BaseAgent
from abm_auto.config import DEFAULT_MODEL
from abm_auto.verification.gate import Verdict


@dataclass
class Violation:
    code: str
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)  # auditable structural pointer


@dataclass
class CriticReport:
    violations: List[Violation] = field(default_factory=list)
    gate_name: str = "critic"

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_verdict(self) -> Verdict:
        """An ADR-013 harness-compatible Verdict. Refutation tier: a pass means
        'not refuted', never 'verified'. Live Harness routing is deferred (D4 Non-goal)."""
        return Verdict(
            passed=self.passed,
            tier="refutation",
            gate_name=self.gate_name,
            reasons=[v.message for v in self.violations],
            evidence={"violations": [v.evidence for v in self.violations]},
        )


class Critic(BaseAgent):
    """Base: generate candidate findings (LLM), keep only deterministically-verified ones.

    Subclasses set `after_phase` + `gate_name`, implement `_artefact_text(ctx)` (the
    artefact whose content the evidence must match) and `generate(ctx)` (the LLM step).
    Tests inject a `generator` to bypass the LLM entirely.
    """

    after_phase: str = ""
    gate_name: str = "critic"

    def __init__(self, client=None, workspace=None, model: str = DEFAULT_MODEL,
                 lang: str = "zh", generator: Optional[Callable[[Any], List[dict]]] = None):
        super().__init__(client, workspace, model=model, lang=lang)
        self._generator = generator

    # -- the seam ----------------------------------------------------------
    def run(self, ctx) -> CriticReport:
        candidates = self._generator(ctx) if self._generator is not None else self.generate(ctx)
        violations = [v for c in candidates if (v := self._verify_one(c, ctx)) is not None]
        return CriticReport(violations=violations, gate_name=self.gate_name)

    def _verify_one(self, candidate: dict, ctx) -> Optional[Violation]:
        """Deterministic gate: the candidate's evidence quote must literally appear in
        the artefact. An LLM-only claim with no matching quote is DROPPED (命门)."""
        evidence = dict(candidate.get("evidence") or {})
        quote = (evidence.get("quote") or "").strip()
        text = self._artefact_text(ctx)
        if not quote or quote not in text:
            return None  # unverifiable → discarded, never emitted
        evidence["artefact"] = self.gate_name
        evidence["verified"] = True
        return Violation(
            code=str(candidate.get("code", "UNSPECIFIED")),
            message=str(candidate.get("message", "")),
            evidence=evidence,
        )

    # -- adapter hooks -----------------------------------------------------
    def _artefact_text(self, ctx) -> str:
        raise NotImplementedError

    def generate(self, ctx) -> List[dict]:
        """LLM step: return a list of candidate-finding dicts {code, message, evidence:{quote}}."""
        raise NotImplementedError

    def _llm_candidates(self, ctx, instruction: str, artefact: str) -> List[dict]:
        """Shared LLM-call + robust JSON parse for adapters' generate()."""
        system = (
            f"{instruction}\n\nReturn ONLY a JSON array of objects with keys "
            f'"code", "message", "evidence" (evidence is an object with a "quote" field '
            f"copying the EXACT substring from the artefact that proves the finding). "
            f"Empty array if none."
        )
        raw = self._complete(system, artefact)
        return _parse_candidates(raw)

    def _complete(self, system: str, user: str) -> str:
        # Route through BaseAgent.call_llm so the Critic gets the SAME retry/backoff on
        # transient LLM errors (rate-limit / connection / 413) as every other agent,
        # instead of calling the client directly with zero retries.
        return self.call_llm(system=system, user=user, max_tokens=1500)


def _parse_candidates(raw: str) -> List[dict]:
    """Extract a JSON array from possibly-noisy LLM output; never raise."""
    if not raw:
        return []
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return [d for d in data if isinstance(d, dict)]
    except (json.JSONDecodeError, TypeError):
        return []


class DesignCritic(Critic):
    """Adapter #1 — runs after DesignViabilityPhase over DESIGN.md."""

    after_phase = "Phase 1+1c (Design + Viability)"
    gate_name = "design_critic"

    def _artefact_text(self, ctx) -> str:
        path = ctx.workspace.design_path
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def generate(self, ctx) -> List[dict]:
        return self._llm_candidates(
            ctx,
            "You are a skeptical ABM design reviewer. Find DESIGN.md defects: "
            "unjustified parameters, circular mechanisms, untestable claims.",
            self._artefact_text(ctx),
        )


class MechanismCritic(Critic):
    """Adapter #2 — runs after MechanismExtractorPhase over mechanism_spec.{md,json}."""

    after_phase = "Phase 1d (MechanismExtractor)"
    gate_name = "mechanism_critic"

    def _artefact_text(self, ctx) -> str:
        path = ctx.workspace.mechanism_spec_path
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        json_path = ctx.workspace.path / "mechanism_spec.json"
        if json_path.exists():
            text += "\n" + json_path.read_text(encoding="utf-8")
        return text

    def generate(self, ctx) -> List[dict]:
        return self._llm_candidates(
            ctx,
            "You are a skeptical mechanism reviewer. Find spec ambiguities that become "
            "mechanism drift: undefined update order, missing units, unbounded parameters.",
            self._artefact_text(ctx),
        )
