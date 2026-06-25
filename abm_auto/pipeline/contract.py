"""ADR-021 D3 — typed Phase contracts (compose-time validation).

Make each Phase's data contract explicit so a re-order that breaks a downstream
read fails at *pipeline construction time*, not 18 phases deep at runtime
(ADR-021 pain #3). A Phase opts in by setting a `contract: PhaseContract` class
attribute naming the `PipelineContext` keys it reads (`inputs`) and writes
(`outputs`). `validate_pipeline` walks the phase list and asserts every input key
is either a construction-time ctx field or produced by an earlier phase.

Follows the same validate-at-parse-time DISCIPLINE as `GISModelSpec.validate()`
(a typed schema checked before downstream work), implemented here with a pydantic
`model_validator`: declaring an unknown ctx key is rejected at parse time.

Anti-fabrication (ADR-013): a contract is a *verifiable* structural claim (key
present/absent in the produced set), checked by code — never an LLM judgement.

Additive, opt-in: uncontracted phases are opaque pass-throughs; the compose-time
check runs only when ABM_VALIDATE_CONTRACTS=1.
"""
from __future__ import annotations

from dataclasses import fields as _dc_fields
from typing import Iterable, List, Tuple

from pydantic import BaseModel, ConfigDict, model_validator

from abm_auto.pipeline.phase import PipelineContext

# Every declared key must be a real PipelineContext field.
_CTX_FIELDS = {f.name for f in _dc_fields(PipelineContext)}

# Construction-time fields are populated in Pipeline.__init__ and are therefore
# always available to any phase. The rest are phase-mutated and must be produced
# by an earlier phase's `outputs` before a later phase may declare them as input.
CONSTRUCTION_TIME_FIELDS: frozenset = frozenset({
    "workspace", "executor", "memory", "story_path",
    "iterations", "max_retries", "peer_review", "lang", "seed",
    "fetch_citations", "baseline_path", "auto_lit_review",
    "mode_override", "intent_override", "external_model_path", "observed_path",
    "sensitivity_method", "sensitivity_samples", "benchmark_archetype",
})


class PhaseContract(BaseModel):
    """The ctx keys a phase reads (`inputs`) and writes (`outputs`)."""

    model_config = ConfigDict(frozen=True)

    inputs: Tuple[str, ...] = ()
    outputs: Tuple[str, ...] = ()

    @model_validator(mode="after")
    def _keys_are_real_ctx_fields(self) -> "PhaseContract":
        unknown = sorted(
            k for k in (*self.inputs, *self.outputs) if k not in _CTX_FIELDS
        )
        if unknown:
            raise ValueError(
                f"contract declares unknown PipelineContext keys {unknown}; "
                f"valid keys are {sorted(_CTX_FIELDS)}"
            )
        return self


class PhaseContractError(Exception):
    """Raised at compose time when a phase's inputs are not yet produced."""

    def __init__(self, phase_name: str, missing_keys: Iterable[str]):
        self.phase_name = phase_name
        self.missing_keys = sorted(missing_keys)
        super().__init__(
            f"phase {phase_name!r} requires ctx keys {self.missing_keys} "
            f"that no earlier phase produces (and that are not construction-time fields)"
        )


def validate_pipeline(phases: List) -> None:
    """Assert prev.outputs ⊆ next.inputs across the contracted phases.

    Walks the phase list accumulating produced ctx keys (seeded with the
    construction-time fields). For each contracted phase, every input key must be
    in the produced set; otherwise raise `PhaseContractError` on the first gap.
    Uncontracted phases (`contract is None`) are opaque — they neither satisfy nor
    break the chain, so the existing 24 phases are unaffected.
    """
    produced = set(CONSTRUCTION_TIME_FIELDS)
    for phase in phases:
        contract = getattr(phase, "contract", None)
        if contract is None:
            continue
        missing = [k for k in contract.inputs if k not in produced]
        if missing:
            raise PhaseContractError(getattr(phase, "name", repr(phase)), missing)
        produced.update(contract.outputs)
