"""Bounded in-process execution for one synthetic quick GIS contract cell."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from affine import Affine

from abm_auto.gis._gate import spatial_spread_gate
from abm_auto.gis._model_spec import GISModelSpec
from abm_auto.gis._raster_space import RasterField, RasterSpace
from abm_auto.gis._sir import run_raster_sir
from abm_auto.mir import NaturalLanguageModelContract, mir_digest
from abm_auto.mir._gis_adapter import gis_spec_to_mir, mir_to_gis_spec


QUICK_EVIDENCE_SCOPE = "quick_exploratory"
_SUPPORTED_CAPABILITY = "raster_sir"


@dataclass(frozen=True)
class QuickGISContractEligibility:
    """Deterministic eligibility result for the public synthetic GIS cell."""

    eligible: bool
    capability: str
    issues: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.eligible) is not bool:
            raise ValueError("eligible must be a bool")
        if not isinstance(self.capability, str):
            raise ValueError("capability must be a string")
        if not isinstance(self.issues, tuple) or not all(
            isinstance(issue, str) and issue for issue in self.issues
        ):
            raise ValueError("issues must be a tuple of non-empty strings")
        if self.eligible != (not self.issues):
            raise ValueError("eligible must match whether issues is empty")


@dataclass(frozen=True)
class QuickGISExecutionReceipt:
    """Compact result from one direct synthetic raster-SIR execution."""

    contract_id: str
    contract_revision: str
    mir_digest: str
    capability: str
    evidence_scope: str
    gate_passed: bool
    gate_message: str
    steps: int
    initial_infected: int
    peak_infected: int
    final_infected: int
    ever_infected_cells: int


def check_quick_gis_contract(
    contract: NaturalLanguageModelContract,
) -> QuickGISContractEligibility:
    """Check whether a contract is eligible for the one public quick GIS cell."""

    if type(contract) is not NaturalLanguageModelContract:
        return QuickGISContractEligibility(
            eligible=False,
            capability="",
            issues=("contract_not_exact",),
        )
    try:
        contract.validate()
    except Exception:
        return QuickGISContractEligibility(
            eligible=False,
            capability="",
            issues=("contract_invalid",),
        )

    issues: list[str] = []
    if contract.mode != "quick":
        issues.append("mode_not_quick")
    if contract.lock.status != "unlocked":
        issues.append("contract_not_unlocked")

    try:
        spec = mir_to_gis_spec(contract.mir)
    except Exception:
        return QuickGISContractEligibility(
            eligible=False,
            capability="",
            issues=tuple((*issues, "gis_projection_invalid")),
        )

    capability = spec.capability
    if capability != _SUPPORTED_CAPABILITY:
        issues.append("capability_not_raster_sir")
    if spec.spatial_type != "raster":
        issues.append("spatial_type_not_raster")
    if spec.mechanism != "sir":
        issues.append("mechanism_not_sir")
    if spec.data_path:
        issues.append("data_path_not_empty")
    if type(spec.seed) is not int:
        issues.append("seed_not_exact_int")
    if type(spec.params.get("steps", 60)) is not int:
        issues.append("steps_not_exact_int")

    try:
        round_trip = gis_spec_to_mir(spec)
    except Exception:
        issues.append("lossless_projection_failed")
    else:
        if mir_digest(round_trip) != contract.mir_digest:
            issues.append("mir_roundtrip_not_lossless")

    return QuickGISContractEligibility(
        eligible=not issues,
        capability=capability,
        issues=tuple(issues),
    )


def run_quick_gis_contract(
    contract: NaturalLanguageModelContract,
) -> QuickGISExecutionReceipt:
    """Run an eligible synthetic raster-SIR contract directly in this process."""

    eligibility = check_quick_gis_contract(contract)
    if not eligibility.eligible:
        raise ValueError(
            "quick GIS contract is not eligible: " + ", ".join(eligibility.issues)
        )
    return _execute_eligible_contract(contract)


def quick_gis_contract_gate(
    contract: NaturalLanguageModelContract,
    receipt: QuickGISExecutionReceipt,
) -> tuple[bool, str]:
    """Verify one receipt against a fresh direct execution of the same contract."""

    try:
        eligibility = check_quick_gis_contract(contract)
        if not eligibility.eligible:
            return _gate_failure(
                "contract is not eligible: " + ", ".join(eligibility.issues)
            )
        if type(receipt) is not QuickGISExecutionReceipt:
            return _gate_failure("receipt must be an exact QuickGISExecutionReceipt")
        receipt_issue = _receipt_issue(contract, receipt)
        if receipt_issue:
            return _gate_failure(receipt_issue)
        expected = _execute_eligible_contract(contract)
        if receipt != expected:
            return _gate_failure("receipt differs from fresh direct execution")
    except Exception as exc:
        return _gate_failure(f"unexpected direct execution failure: {exc}")

    return (
        True,
        "PASS: the bounded synthetic raster-SIR contract re-ran directly and "
        "matched its receipt. This is quick exploratory evidence only, not "
        "hostile-proof provenance, a scientific result, or a reproduction claim.",
    )


def _execute_eligible_contract(
    contract: NaturalLanguageModelContract,
) -> QuickGISExecutionReceipt:
    spec = mir_to_gis_spec(contract.mir)
    steps = spec.params.get("steps", 60)
    space = _synthetic_raster_space()
    result = run_raster_sir(space, seed=spec.seed, steps=steps)
    gate_passed, gate_message = spatial_spread_gate(result, space.field.data)
    history = result.infected_history
    return QuickGISExecutionReceipt(
        contract_id=contract.contract_id,
        contract_revision=contract.contract_revision,
        mir_digest=contract.mir_digest,
        capability=_SUPPORTED_CAPABILITY,
        evidence_scope=QUICK_EVIDENCE_SCOPE,
        gate_passed=gate_passed,
        gate_message=gate_message,
        steps=steps,
        initial_infected=history[0],
        peak_infected=max(history),
        final_infected=history[-1],
        ever_infected_cells=int(result.final_infected_field.sum()),
    )


def _synthetic_raster_space() -> RasterSpace:
    n = 24
    yy, xx = np.mgrid[0:n, 0:n]
    density = np.exp(
        -(((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (2 * (n / 5) ** 2))
    )
    transform = Affine(100, 0, 0, 0, -100, n * 100)
    return RasterSpace(
        RasterField(data=density, transform=transform, crs="EPSG:3857")
    )


def _receipt_issue(
    contract: NaturalLanguageModelContract,
    receipt: QuickGISExecutionReceipt,
) -> str:
    expected_strings = {
        "contract_id": contract.contract_id,
        "contract_revision": contract.contract_revision,
        "mir_digest": contract.mir_digest,
        "capability": _SUPPORTED_CAPABILITY,
        "evidence_scope": QUICK_EVIDENCE_SCOPE,
    }
    for field_name, expected in expected_strings.items():
        if getattr(receipt, field_name) != expected:
            return f"receipt {field_name} does not match the contract"
    if type(receipt.gate_passed) is not bool:
        return "receipt gate_passed must be a bool"
    if not isinstance(receipt.gate_message, str) or not receipt.gate_message:
        return "receipt gate_message must be non-empty text"
    values = (
        receipt.steps,
        receipt.initial_infected,
        receipt.peak_infected,
        receipt.final_infected,
        receipt.ever_infected_cells,
    )
    if any(type(value) is not int for value in values):
        return "receipt summary values must be exact ints"
    if receipt.steps < 1:
        return "receipt steps must be positive"
    if min(values[1:]) < 0:
        return "receipt infected counts must be non-negative"
    if receipt.peak_infected < receipt.initial_infected:
        return "receipt peak_infected is below initial_infected"
    if receipt.peak_infected < receipt.final_infected:
        return "receipt peak_infected is below final_infected"
    if receipt.ever_infected_cells < receipt.peak_infected:
        return "receipt ever_infected_cells is below peak_infected"
    return ""


def _gate_failure(reason: str) -> tuple[bool, str]:
    return False, f"FAIL: quick GIS contract gate failed: {reason}"
