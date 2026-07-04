"""abm_auto.cbhg — CBHG-style human-interpretable rule grammar (PROTOTYPE, experimental).

Additive, import-isolated (mirrors optional extension packages); not wired into any
pipeline. Demonstrates a constrained, auditable rule grammar as the middle layer between
intent and an executable model — the transferable idea from the Cell 2025 PhysiCell Cell
Behavior Hypothesis Grammar paper, in mymomo's trust idiom. See ``grammar.py``.
"""
from abm_auto.cbhg.grammar import (
    CompiledModel,
    Rule,
    RuleAudit,
    audit_rules,
    compile_model,
    parse_rule,
    parse_rules,
    to_physicell_csv,
)

__all__ = [
    "Rule",
    "parse_rule",
    "parse_rules",
    "CompiledModel",
    "compile_model",
    "RuleAudit",
    "audit_rules",
    "to_physicell_csv",
]
