"""Tests for the bounded in-process quick GIS contract execution cell."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from abm_auto.gis._contract_execution import (
    QUICK_EVIDENCE_SCOPE,
    QuickGISExecutionReceipt,
    check_quick_gis_contract,
    quick_gis_contract_gate,
    run_quick_gis_contract,
)
from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.mir import (
    MIR,
    RoutingDecision,
    create_model_contract,
    load_model_contract,
    lock_contract,
    promote_to_research,
)
from abm_auto.mir._gis_adapter import gis_spec_to_mir


_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "reproduce"
    / "natural-language-model-contract"
    / "public-v4-quick-raster-sir.json"
)


def _routing() -> RoutingDecision:
    return RoutingDecision(
        requested_mode="quick",
        resolved_mode="quick",
        rationale=("Public synthetic quick GIS fixture.",),
        overridden=False,
    )


def _contract_from_spec(spec: GISModelSpec):
    return create_model_contract(
        contract_id="public-v4-quick-raster-sir",
        branch_id="public-v4",
        mode="quick",
        mir=gis_spec_to_mir(spec),
        assumptions=(),
        unresolved_decisions=(),
        routing=_routing(),
        source="system",
    )


def _quick_contract():
    return _contract_from_spec(
        GISModelSpec(
            spatial_type="raster",
            mechanism="sir",
            capability="raster_sir",
            params={"steps": 24},
            seed=17,
        )
    )


def _locked_contract():
    promoted = promote_to_research(
        _quick_contract(),
        rationale="Promote this synthetic fixture for lifecycle testing.",
        source="system",
    )
    return lock_contract(
        promoted,
        reason="Lock this synthetic fixture for lifecycle testing.",
        source="system",
    )


def test_eligible_synthetic_contract_runs_directly_and_is_gateable() -> None:
    contract = _quick_contract()

    eligibility = check_quick_gis_contract(contract)
    receipt = run_quick_gis_contract(contract)

    assert eligibility.eligible is True
    assert eligibility.capability == "raster_sir"
    assert eligibility.issues == ()
    assert receipt.contract_id == contract.contract_id
    assert receipt.contract_revision == contract.contract_revision
    assert receipt.mir_digest == contract.mir_digest
    assert receipt.capability == "raster_sir"
    assert receipt.evidence_scope == QUICK_EVIDENCE_SCOPE
    assert receipt.steps == 24
    assert receipt.initial_infected == 1
    assert receipt.peak_infected >= receipt.initial_infected
    assert receipt.ever_infected_cells >= receipt.peak_infected
    assert receipt.gate_passed is True
    assert quick_gis_contract_gate(contract, receipt)[0] is True


def test_direct_execution_is_deterministic() -> None:
    contract = _quick_contract()

    assert run_quick_gis_contract(contract) == run_quick_gis_contract(contract)


@pytest.mark.parametrize(
    ("contract", "issue"),
    [
        (_locked_contract(), "contract_not_unlocked"),
        (
            _contract_from_spec(
                GISModelSpec(
                    spatial_type="raster",
                    mechanism="sir",
                    capability="raster_sir",
                    data_path="observed.tif",
                    params={"steps": 24},
                    seed=17,
                )
            ),
            "data_path_not_empty",
        ),
        (
            _contract_from_spec(
                GISModelSpec(
                    spatial_type="network",
                    mechanism="routing_load",
                    capability="network_routing_load",
                    data_path="roads.shp",
                    params={},
                    seed=17,
                )
            ),
            "capability_not_raster_sir",
        ),
        (
            _contract_from_spec(
                GISModelSpec(
                    spatial_type="raster",
                    mechanism="sir",
                    capability="raster_sir",
                    params={"steps": True},
                    seed=17,
                )
            ),
            "steps_not_exact_int",
        ),
    ],
)
def test_ineligible_contracts_are_rejected_before_execution(contract, issue: str) -> None:
    eligibility = check_quick_gis_contract(contract)

    assert eligibility.eligible is False
    assert issue in eligibility.issues
    with pytest.raises(ValueError, match="not eligible"):
        run_quick_gis_contract(contract)


def test_lossy_mir_contract_is_rejected_before_execution() -> None:
    original = _quick_contract()
    lossy_mir = original.mir
    lossy_mir.entities.append({"name": "not represented by GISModelSpec"})
    lossy = create_model_contract(
        contract_id=original.contract_id,
        branch_id=original.branch_id,
        mode="quick",
        mir=lossy_mir,
        assumptions=(),
        unresolved_decisions=(),
        routing=_routing(),
        source="system",
    )

    eligibility = check_quick_gis_contract(lossy)

    assert eligibility.eligible is False
    assert "mir_roundtrip_not_lossless" in eligibility.issues
    with pytest.raises(ValueError, match="not eligible"):
        run_quick_gis_contract(lossy)


def test_public_fixture_is_constructor_generated_and_round_trips() -> None:
    fixture = load_model_contract(_FIXTURE)

    assert fixture.to_json() == _FIXTURE.read_text(encoding="utf-8").strip()
    assert fixture == _quick_contract()
    assert check_quick_gis_contract(fixture).eligible is True


def test_gate_rejects_receipts_that_do_not_match_a_fresh_direct_run() -> None:
    contract = _quick_contract()
    receipt = run_quick_gis_contract(contract)
    forged = replace(receipt, peak_infected=receipt.peak_infected + 1)

    ok, message = quick_gis_contract_gate(contract, forged)

    assert ok is False
    assert "fresh direct execution" in message


def test_adapter_source_has_no_template_or_process_runner_surface() -> None:
    import abm_auto.gis._contract_execution as execution

    source = Path(execution.__file__).read_text(encoding="utf-8")

    for forbidden in (
        "subprocess",
        "tempfile",
        "_templates",
        "gis_codegen_gate",
        "render(",
        "Popen",
    ):
        assert forbidden not in source


def test_gate_rejects_wrong_receipt_type() -> None:
    ok, message = quick_gis_contract_gate(_quick_contract(), object())

    assert ok is False
    assert "exact QuickGISExecutionReceipt" in message


def test_receipt_type_is_immutable() -> None:
    receipt = run_quick_gis_contract(_quick_contract())

    assert isinstance(receipt, QuickGISExecutionReceipt)
    with pytest.raises((AttributeError, TypeError)):
        receipt.steps = 999
