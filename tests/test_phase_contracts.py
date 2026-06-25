"""Tests for ADR-021 D3 — typed Phase contracts (compose-time validation)."""
from __future__ import annotations

import pytest

from abm_auto.pipeline.contract import (
    PhaseContract,
    PhaseContractError,
    validate_pipeline,
)
from abm_auto.pipeline.phases.setup import (
    ExternalModelDeclarationPhase,
    InjectObservedDataPhase,
    ModeDetectorPhase,
)


def _first_three():
    # validate_pipeline only reads .contract and .name — agents are not needed.
    return [
        ModeDetectorPhase(agent=None),
        ExternalModelDeclarationPhase(),
        InjectObservedDataPhase(),
    ]


# --- 1. PhaseContract parse + unknown-key rejection ----------------------

def test_contract_instantiates_with_real_ctx_keys():
    c = PhaseContract(inputs=("spec",), outputs=("using_external_model",))
    assert c.inputs == ("spec",)


def test_contract_rejects_unknown_ctx_key():
    with pytest.raises(Exception, match="unknown PipelineContext keys"):
        PhaseContract(inputs=("not_a_real_field",))
    with pytest.raises(Exception, match="unknown PipelineContext keys"):
        PhaseContract(outputs=("bogus",))


# --- 2. validate_pipeline happy path -------------------------------------

def test_real_first_three_validate_clean():
    # ModeDetector produces `spec`; ExternalModel + InjectObserved consume it.
    validate_pipeline(_first_three())  # must not raise


# --- 3. validate_pipeline fail-fast on re-order --------------------------

def test_reorder_consumer_before_producer_raises():
    phases = _first_three()
    bad = [phases[2], phases[0], phases[1]]  # InjectObserved before ModeDetector
    with pytest.raises(PhaseContractError) as ei:
        validate_pipeline(bad)
    err = ei.value
    assert err.phase_name == InjectObservedDataPhase.name
    assert "spec" in err.missing_keys  # the silent-None-deref bug, now caught


# --- 5. uncontracted phases are opaque -----------------------------------

class _Uncontracted:
    name = "opaque"
    contract = None


def test_uncontracted_phases_neither_satisfy_nor_break():
    phases = _first_three()
    # interleave an uncontracted phase — it must not affect validity
    mixed = [phases[0], _Uncontracted(), phases[1], _Uncontracted(), phases[2]]
    validate_pipeline(mixed)  # still clean

    # an uncontracted phase cannot *supply* a missing key, either
    only_consumer = [_Uncontracted(), phases[2]]  # InjectObserved needs `spec`
    with pytest.raises(PhaseContractError):
        validate_pipeline(only_consumer)


def test_construction_time_fields_are_always_available():
    # a phase whose only inputs are construction-time fields validates with no producer
    p = ModeDetectorPhase(agent=None)  # inputs = mode_override, intent_override (ctime)
    validate_pipeline([p])  # must not raise
