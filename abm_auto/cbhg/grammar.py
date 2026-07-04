"""A CBHG-style human-interpretable rule grammar — PROTOTYPE (experimental, additive,
import-isolated; mirrors optional extension packages, base engine untouched).

Demonstrates the transferable lesson from the Cell 2025 PhysiCell "Cell Behavior Hypothesis
Grammar" paper, mapped onto mymomo: a constrained, human-readable rule grammar as the
auditable middle layer between intent and an executable model. Three deterministic steps —
PARSE (human sentence -> structured Rule), COMPILE (rules -> runnable mechanistic model),
AUDIT (flag rules lacking provenance -> CAVEATED, reusing mymomo's CLEAN/CAVEATED honesty
vocabulary). The point is that LLM ambiguity is confined to "propose rules in English"; the
rules themselves are human-diffable and the trust layer can flag ungrounded ones.

Rule sentence form (CBHG-flavored):
    In <cell_type>, <signal> increases|decreases <target>; half-max <h>, Hill <n>, max <a>[; cite <ref>].
e.g.
    In tumor, oxygen increases proliferation; half-max 0.5, Hill 4, max 3.0; cite Smith2020.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

_NUM = r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"   # float incl. negatives (validated below) + sci-notation
_RULE_RE = re.compile(
    r"^In\s+(?P<cell>[\w-]+),\s+(?P<signal>[\w-]+)\s+(?P<dir>increases|decreases)\s+"
    r"(?P<target>[\w-]+);\s*half-max\s+(?P<half>" + _NUM + r"),\s*Hill\s+(?P<hill>" + _NUM + r"),\s*"
    r"max\s+(?P<max>" + _NUM + r")(?:;\s*cite\s+(?P<cite>.+?))?\s*\.?\s*$"
)

# a citation counts as provenance only if it has real content — bare "." or placeholders
# (the regex can capture a stray ".") must NOT pass the audit as grounded.
_PLACEHOLDERS = {"", ".", "?", "??", "???", "x", "na", "n/a", "none", "todo", "tbd", "xxx", "tba"}


def _is_grounded(cite) -> bool:
    if not cite:
        return False
    norm = cite.strip().strip(".,;: ").lower()
    if norm in _PLACEHOLDERS:
        return False
    return len(re.sub(r"[^A-Za-z0-9]", "", cite)) >= 3


@dataclass(frozen=True)
class Rule:
    cell_type: str
    signal: str
    direction: str            # "increases" | "decreases"
    target: str
    half_max: float
    hill: float
    max_response: float
    citation: str | None = None

    def __post_init__(self):
        # physically-invalid parameters are a malformed rule, not a silently-compiled NaN model
        if self.half_max <= 0:
            raise ValueError(f"half-max must be > 0, got {self.half_max}")
        if self.hill <= 0:
            raise ValueError(f"Hill power must be > 0, got {self.hill}")
        if self.max_response < 0:
            raise ValueError(f"max must be >= 0 (direction carries the sign), got {self.max_response}")

    @property
    def sign(self) -> int:
        return 1 if self.direction == "increases" else -1


def parse_rule(line: str) -> Rule:
    """Parse one human-readable rule sentence. Raises ValueError on a malformed line (the
    parse 'gate' — ambiguous English never silently becomes a model)."""
    m = _RULE_RE.match(line.strip())
    if not m:
        raise ValueError(f"malformed rule (expected CBHG sentence form): {line!r}")
    g = m.groupdict()
    return Rule(
        cell_type=g["cell"], signal=g["signal"], direction=g["dir"], target=g["target"],
        half_max=float(g["half"]), hill=float(g["hill"]), max_response=float(g["max"]),
        citation=(g["cite"].strip() if g["cite"] else None),
    )


def parse_rules(text: str) -> list[Rule]:
    """Parse a rules block (one sentence per non-empty, non-comment line)."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(parse_rule(line))
    return out


def _hill(x: np.ndarray, half: float, n: float) -> np.ndarray:
    xn = np.clip(x, 0, None) ** n
    return xn / (half ** n + xn)


class CompiledModel:
    """Deterministic compilation of rules into a runnable mechanistic model. Each target's
    value is the signed sum of its rules' Hill responses, applied per matching cell_type."""

    def __init__(self, rules: list[Rule]):
        self.rules = list(rules)
        self.targets = sorted({r.target for r in rules})

    def run(self, cell_types: np.ndarray, signals: dict) -> dict:
        cell_types = np.asarray(cell_types)
        n = len(cell_types)
        out = {t: np.zeros(n) for t in self.targets}
        for r in self.rules:
            if r.signal not in signals:
                raise KeyError(f"rule needs signal {r.signal!r} not provided (have {list(signals)})")
            mask = cell_types == r.cell_type
            resp = r.sign * r.max_response * _hill(np.asarray(signals[r.signal]), r.half_max, r.hill)
            out[r.target] = out[r.target] + np.where(mask, resp, 0.0)
        return out


def compile_model(rules: list[Rule]) -> CompiledModel:
    return CompiledModel(rules)


@dataclass
class RuleAudit:
    """Honest aggregate over a rule set, reusing mymomo's CLEAN/CAVEATED vocabulary. A rule
    without provenance does not make the model wrong, but it must not pass as grounded."""

    status: str                       # "CLEAN" | "CAVEATED"
    ungrounded: list                  # rules lacking a citation

    def render(self) -> str:
        head = f"rule audit: {self.status} ({len(self.ungrounded)} ungrounded rule(s))"
        if self.ungrounded:
            head += " | " + "; ".join(f"{r.signal} {r.direction} {r.target}" for r in self.ungrounded)
        return head + "\n(CAVEATED = unproven provenance, not a grounding guarantee)"


def audit_rules(rules: list[Rule]) -> RuleAudit:
    """Flag rules without real provenance. CLEAN iff every rule carries a non-placeholder
    citation (a bare '.', 'TODO', etc. do NOT count as grounded)."""
    ungrounded = [r for r in rules if not _is_grounded(r.citation)]
    return RuleAudit(status="CAVEATED" if ungrounded else "CLEAN", ungrounded=ungrounded)


_PHYSICELL_HEADER = "cell_type,signal,response,behavior,saturation,half_max,hill_power,applies_to_dead"


def to_physicell_csv(rules: list[Rule], *, header: bool = False, applies_to_dead: int = 0) -> str:
    """Emit rules so the SAME human-readable grammar can target the real PhysiCell engine (not
    just the in-Python responder). Positional column order (the documented PhysiCell v2/v3 rules
    format):
        cell_type, signal, direction, behavior, max_response, half_max, hill_power, applies_to_dead
    Mapping: ``target`` -> behavior, ``max_response`` -> saturation/max-response value,
    ``direction`` -> response.

    ``header`` defaults to FALSE because PhysiCell's core rules loader is POSITIONAL and
    HEADERLESS — it parses every non-empty line as a rule, so a header row makes it look up a
    cell definition named "cell_type" and ``exit(-1)``. Pass ``header=True`` ONLY for a human
    preview (the column NAMES are our labels, not PhysiCell's; the positional ORDER is what the
    engine reads). ``citation`` is mymomo provenance and is deliberately NOT emitted (not part
    of PhysiCell's schema; it lives in the audit layer)."""
    lines = [_PHYSICELL_HEADER] if header else []
    for r in rules:
        lines.append(
            f"{r.cell_type},{r.signal},{r.direction},{r.target},"
            f"{r.max_response},{r.half_max},{r.hill},{applies_to_dead}"
        )
    return "\n".join(lines) + "\n"
