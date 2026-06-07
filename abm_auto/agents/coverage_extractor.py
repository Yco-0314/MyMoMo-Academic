"""Coverage extraction (ADR-014 1b) — the LLM EVIDENCE half of the D-LLM split.

Reads DESIGN + mechanism spec and emits closed-label `Mechanism` records. This
is evidence ONLY; the deterministic `CoverageGate.check` is the verdict (the
LLM cannot certify buildability — it can only describe each mechanism with
closed labels + honest markers, which the gate's deterministic contract-match /
verifiability logic then judges, anti-flatten backstops included).

The parsing + validation here are deterministic (given a JSON string → typed
Mechanisms) and self-tested; only `extract()` calls the LLM.
"""
from __future__ import annotations

import json
import re

from abm_auto.agents.base import BaseAgent
from abm_auto.codegen.coverage_gate import (
    CAPABILITIES,
    Mechanism,
    TRAINING_SIGNALS,
    VERIFIABLE_STD,
)

_KNOWN_MARKERS = {"adversarial", "multi_network", "generative",
                  "encoder_decoder", "deep_attention", "reward"}
_FAITHFULNESS = {"full", "partial", "none"}

# A marker is the load-bearing anti-flatten signal, so we do NOT trust the LLM's
# word on it (ADR-012). Each marker is kept ONLY if the DESIGN PROSE corroborates
# it — a hallucinated marker (the LLM tagging a plain 1-hidden-layer net
# "encoder_decoder") is dropped, so it can't false-halt a covered operator; a
# real one (the prose genuinely shows adversarial/reward structure) is kept, so
# anti-flatten holds. Deterministic, prose-grounded.
_MARKER_PHRASES = {
    "adversarial": r"adversarial|\bgan\b|discriminator",
    "multi_network": r"discriminator|generator network|encoder[- ]?decoder|"
                     r"multiple (neural )?networks|two networks",
    "encoder_decoder": r"encoder[- ]?decoder|auto-?encoder|\bvae\b|variational",
    "deep_attention": r"\battention\b|transformer|multi-head",
    "generative": r"generativ|synthesi[sz]|\bgan\b|\bvae\b",
    "reward": r"\breward\b|reinforcement|\bq-?learning\b|policy gradient|"
              r"td[- ]error|temporal difference|actor-critic",
}


def _corroborated_markers(raw, prose_low: str) -> frozenset:
    """Keep only LLM-emitted markers the prose actually supports."""
    return frozenset(
        mk for mk in raw
        if mk in _KNOWN_MARKERS and re.search(_MARKER_PHRASES[mk], prose_low)
    )

_SYSTEM = (
    "You extract a model's computational mechanisms as closed-label JSON "
    "evidence for a deterministic Coverage Gate. Prioritise accurate recall and "
    "honest structural markers. You do not decide buildability — you only "
    "describe each mechanism. Reply with one fenced ```json``` list, nothing else."
)


def _parse_json_list(text: str) -> list:
    """Pull a JSON list out of LLM output: fenced ```json``` block first, then a
    bare top-level [...]. Returns [] on anything unparseable (the recall floor +
    stub fallback cover a failed extraction)."""
    if not text:
        return []
    m = re.search(r"```json\s*(.*?)```", text, re.S | re.I)
    if not m:
        m = re.search(r"```\s*(\[.*?\])\s*```", text, re.S)
    blob = m.group(1) if m else None
    if blob is None:
        m2 = re.search(r"(\[.*\])", text, re.S)
        blob = m2.group(1) if m2 else None
    if blob is None:
        return []
    try:
        data = json.loads(blob)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _to_mechanism(rec: dict, i: int, prose_low: str = "") -> "Mechanism | None":
    """Validate one record against the closed vocabularies → a Mechanism, or
    None if the capability is unknown (a malformed record is dropped, not
    trusted). Markers are corroborated against the prose (hallucinated markers
    dropped); unknown training_signal / std are sanitised to safe defaults."""
    if not isinstance(rec, dict):
        return None
    cap = rec.get("capability")
    if cap not in CAPABILITIES:
        return None
    ts = rec.get("training_signal")
    if ts not in TRAINING_SIGNALS:
        ts = None
    markers = _corroborated_markers(rec.get("markers") or [], prose_low)
    std = rec.get("std_algorithm")
    if std not in VERIFIABLE_STD:
        std = None
    faith = rec.get("faithfulness")
    if faith not in _FAITHFULNESS:
        faith = "full"
    # a supervised item-predictor IS single_item -> item_distribution; fill the
    # contract triple so a plain learner matches FeedforwardLearner while an RL /
    # deep one (caught by markers/training_signal) does not.
    input_kind = output_kind = None
    if cap == "learned_predictor":
        input_kind, output_kind = "single_item", "item_distribution"
        # LLMs routinely OMIT training_signal for a plain learner. A learned
        # predictor with no reward/adversarial marker IS supervised — default
        # it so it matches the operator (else every FeedforwardLearner model
        # false-halts). Reward/adversarial markers still override via the gate's
        # _effective_training_signal backstop, so this can't launder an RL/GAN.
        if ts is None:
            ts = "supervised_pairs"
    name = str(rec.get("name") or f"mech_{i}")
    return Mechanism(name, cap, input_kind, output_kind, ts, markers, std, faith)


def records_to_mechanisms(records: list, prose: str = "") -> list:
    """Deterministic: validated Mechanism records from raw LLM JSON records.
    Markers are corroborated against `prose` (hallucinated ones dropped, real
    ones — like a genuine reward signal — kept so anti-flatten holds)."""
    prose_low = (prose or "").lower()
    out = []
    for i, rec in enumerate(records):
        m = _to_mechanism(rec, i, prose_low)
        if m is not None:
            out.append(m)
    return out


class CoverageExtractor(BaseAgent):
    """1b: LLM extraction of Mechanism records (evidence for the Coverage Gate)."""

    def extract(self, prose: str) -> list:
        template = self.load_prompt("coverage_extract")
        prompt = template.replace("{{ design }}", prose or "")
        out = self.call_llm(_SYSTEM, prompt, max_tokens=1536)
        return records_to_mechanisms(_parse_json_list(out), prose)
