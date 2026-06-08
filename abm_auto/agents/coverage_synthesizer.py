"""Operator synthesizer (ADR-015 option B) — the LLM DRAFT seam.

Drafts candidate operator CODE for an audited verification paradigm. The code is
then verified in an ISOLATED subprocess by the audited oracle
(`synthesis_phase.verify_in_subprocess`); this agent NEVER execs it. The drafter
is the only LLM-facing part of self-extension — everything downstream (the
oracle, the sandbox, the internalize gate) is deterministic.

`draft_code` returns a source string defining `build` per the paradigm protocol;
parse/extraction is deterministic (self-tested), only the LLM call is the seam.
"""
from __future__ import annotations

import re

from abm_auto.agents.base import BaseAgent

# Per-paradigm CANDIDATE PROTOCOL — what `build` must be (matches the oracles in
# synthesis_oracles.py). Injected into the prompt so the LLM drafts to spec.
PROTOCOLS = {
    "tabular_q_learning": (
        "Define `build(n_states, n_actions)` returning an object with:\n"
        "  - `.update(s, a, r, s2)` — one temporal-difference learning step\n"
        "  - `.best_action(s) -> int` — the greedy action in state s\n"
        "An external loop trains it on an unknown finite MDP; it must learn a\n"
        "good (reward-maximising) policy. A plain tabular Q-learning update works."
    ),
    "kalman_filter": (
        "Define `build()` returning an object with:\n"
        "  - `.update(obs)` — fold in one noisy scalar observation\n"
        "  - `.estimate() -> float` — current best estimate of the true value\n"
        "It receives noisy observations of an unknown (roughly constant) scalar\n"
        "and its estimate must converge near the truth."
    ),
    "linear_program": (
        "Define `build()` returning a function `solve(c, A_ub, b_ub)` that returns\n"
        "a list x of 2 numbers MINIMISING the dot product c·x subject to\n"
        "A_ub · x <= b_ub (row-wise) and x >= 0."
    ),
}

_SYSTEM = (
    "You implement a small, correct numerical operator in pure Python to a fixed "
    "protocol. An independent oracle verifies it in a sandbox; you cannot see the "
    "oracle. Output exactly one fenced ```python``` block."
)


def extract_python(text: str) -> str:
    """Deterministic: the fenced ```python``` block (or the whole text if the
    model forgot the fence). Empty string on nothing usable."""
    if not text:
        return ""
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.S | re.I)
    if m:
        return m.group(1).strip()
    return text.strip() if "def build" in text else ""


class OperatorSynthesizer(BaseAgent):
    """1 of ADR-015's two seams: drafts candidate operator code (the other is the
    audited oracle, which is NOT here — it verifies in a sandbox)."""

    def draft_code(self, mechanism, oracle_paradigm: str, feedback: "str | None" = None) -> str:
        protocol = PROTOCOLS.get(oracle_paradigm)
        if protocol is None:
            return ""                            # no audited paradigm → nothing to draft
        fb = ("\n## Your previous attempt FAILED the oracle — fix it and retry.\n"
              f"{feedback}\n") if feedback else ""
        prompt = (self.load_prompt("coverage_synthesize")
                  .replace("{{ capability }}", getattr(mechanism, "capability", "?"))
                  .replace("{{ paradigm }}", oracle_paradigm)
                  .replace("{{ protocol }}", protocol)
                  .replace("{{ feedback }}", fb))
        return extract_python(self.call_llm(_SYSTEM, prompt, max_tokens=1024))
