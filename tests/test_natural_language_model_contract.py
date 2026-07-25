import hashlib
import json
import os
import stat
import subprocess
import sys
from collections import UserList
from dataclasses import replace
from pathlib import Path

import pytest

import abm_auto.mir as mir_api
import abm_auto.mir._model_contract as model_contract
from abm_auto.mir import (
    MODEL_CONTRACT_MAX_BYTES,
    MODEL_CONTRACT_SCHEMA,
    SEMANTIC_PATCH_SCHEMA,
    AssumptionRecord,
    ContractLock,
    MIR,
    MIRFidelity,
    MIRMetadata,
    MIRProcess,
    MIRRun,
    MIRSpace,
    NaturalLanguageModelContract,
    RevisionRecord,
    RoutingDecision,
    SemanticPatch,
    SemanticPatchOperation,
    UnresolvedDecision,
    apply_semantic_patch,
    branch_contract,
    contract_revision_digest,
    contract_state_digest,
    create_model_contract,
    lock_contract,
    load_model_contract,
    load_semantic_patch,
    mir_digest,
    netlogo_controls_to_mir,
    netlogo_model_to_mir,
    patch_digest,
    promote_to_research,
    research_readiness,
    revision_digest,
    semantic_patch_equivalence_gate,
    state_digest,
)


_FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reproduce"
    / "natural-language-model-contract"
)


def _threshold_mir() -> MIR:
    return MIR(
        metadata=MIRMetadata(
            name="Threshold adoption",
            description="Adoption begins after a local threshold is met.",
            domain="social",
            provenance={"source": "user"},
        ),
        entities=[{"name": "person"}],
        state=[{"name": "adopted", "type": "bool"}],
        space=MIRSpace(spatial_type="network"),
        processes=[
            MIRProcess(
                mechanism="threshold_adoption",
                params={"threshold": 0.4},
            )
        ],
        run=MIRRun(seed=7, params={"steps": 12}),
    )


def _assumption() -> AssumptionRecord:
    return AssumptionRecord(
        assumption_id="threshold-source",
        statement="The initial threshold is supplied by the user.",
        target_path="/mir/processes/0/params/threshold",
        source="user",
        materiality="material",
        confirmed=True,
    )


def _inferred_assumption() -> AssumptionRecord:
    return AssumptionRecord(
        assumption_id="threshold-source",
        statement="The initial threshold is inferred from the request.",
        target_path="/mir/processes/0/params/threshold",
        source="inferred",
        materiality="material",
        confirmed=False,
    )


def _second_assumption() -> AssumptionRecord:
    return AssumptionRecord(
        assumption_id="step-count-default",
        statement="The run length uses the default step count.",
        target_path="/mir/run/params/steps",
        source="default",
        materiality="low",
        confirmed=False,
    )


def _decision() -> UnresolvedDecision:
    return UnresolvedDecision(
        decision_id="network-choice",
        question="Which observed social network should be used?",
        target_path="/mir/relations",
        materiality="low",
        status="open",
        resolution="",
    )


def _second_decision() -> UnresolvedDecision:
    return UnresolvedDecision(
        decision_id="crs-choice",
        question="Which coordinate reference system should be used?",
        target_path="/mir/space/crs",
        materiality="low",
        status="open",
        resolution="",
    )


def _routing() -> RoutingDecision:
    return RoutingDecision(
        requested_mode="quick",
        resolved_mode="quick",
        rationale=("explicit quick-mode request",),
        overridden=False,
    )


def _contract(*, source: str = "conversation") -> NaturalLanguageModelContract:
    return create_model_contract(
        contract_id="threshold-demo",
        branch_id="main",
        mode="quick",
        mir=_threshold_mir(),
        assumptions=(_assumption(),),
        unresolved_decisions=(_decision(),),
        routing=_routing(),
        source=source,
    )


def _contract_from_mir(mir: MIR) -> NaturalLanguageModelContract:
    return create_model_contract(
        contract_id="threshold-demo",
        branch_id="main",
        mode="quick",
        mir=mir,
        assumptions=(),
        unresolved_decisions=(),
        routing=_routing(),
        source="conversation",
    )


def _contract_with_audit_records(
    *,
    assumptions,
    unresolved_decisions,
) -> NaturalLanguageModelContract:
    return create_model_contract(
        contract_id="threshold-demo",
        branch_id="main",
        mode="quick",
        mir=_threshold_mir(),
        assumptions=assumptions,
        unresolved_decisions=unresolved_decisions,
        routing=_routing(),
        source="conversation",
    )


def _mode_contract(
    *,
    mode: str,
    requested_mode: str,
    assumptions=(),
    unresolved_decisions=(),
) -> NaturalLanguageModelContract:
    overridden = requested_mode != "auto" and requested_mode != mode
    return create_model_contract(
        contract_id="threshold-demo",
        branch_id="main",
        mode=mode,
        mir=_threshold_mir(),
        assumptions=assumptions,
        unresolved_decisions=unresolved_decisions,
        routing=RoutingDecision(
            requested_mode=requested_mode,
            resolved_mode=mode,
            rationale=(f"{requested_mode} request resolved to {mode}",),
            overridden=overridden,
        ),
        source="conversation",
    )


def _promoted_research_contract(
    *,
    requested_mode: str = "quick",
    assumptions=(),
    unresolved_decisions=(),
) -> NaturalLanguageModelContract:
    quick = _mode_contract(
        mode="quick",
        requested_mode=requested_mode,
        assumptions=assumptions,
        unresolved_decisions=unresolved_decisions,
    )
    return promote_to_research(
        quick,
        rationale="Escalate this model for research use.",
        source="panel",
    )


def _ready_research_contract(
    *,
    requested_mode: str = "research",
) -> NaturalLanguageModelContract:
    if requested_mode == "research":
        return _mode_contract(
            mode="research",
            requested_mode=requested_mode,
            assumptions=(_assumption(), _second_assumption()),
            unresolved_decisions=(_decision(),),
        )
    return _promoted_research_contract(
        requested_mode=requested_mode,
        assumptions=(_assumption(), _second_assumption()),
        unresolved_decisions=(_decision(),),
    )


def _canonical_digest(value) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _semantic_patch(
    contract: NaturalLanguageModelContract,
    operations,
    *,
    source: str = "conversation",
    rationale: str = "Apply a semantic edit.",
) -> SemanticPatch:
    return SemanticPatch(
        schema=SEMANTIC_PATCH_SCHEMA,
        base_contract_revision=contract.contract_revision,
        source=source,
        rationale=rationale,
        operations=tuple(operations),
    )


def _assert_patch_rejected_without_mutation(
    contract: NaturalLanguageModelContract,
    patch: SemanticPatch,
    expected_message: str,
) -> ValueError:
    before = contract.to_dict()

    with pytest.raises(ValueError) as exc_info:
        model_contract.apply_semantic_patch(contract, patch)

    assert expected_message in str(exc_info.value)
    assert contract.to_dict() == before
    return exc_info.value


def _assert_persisted_contract_rejected(
    contract: NaturalLanguageModelContract,
    expected_message: str,
) -> None:
    before = contract.to_dict()

    with pytest.raises(ValueError, match=expected_message):
        contract.validate()
    with pytest.raises(ValueError, match=expected_message):
        NaturalLanguageModelContract.from_dict(before)

    assert contract.to_dict() == before


def _rehash_revision(
    contract: NaturalLanguageModelContract,
    revision: RevisionRecord,
    *,
    parent_contract_revision: str,
    state_digest_value: str | None = None,
    mir_digest_value: str | None = None,
) -> RevisionRecord:
    resulting_state_digest = (
        revision.state_digest
        if state_digest_value is None
        else state_digest_value
    )
    resulting_mir_digest = (
        revision.mir_digest if mir_digest_value is None else mir_digest_value
    )
    current_revision = contract_revision_digest(
        contract_id=contract.contract_id,
        parent_contract_revision=parent_contract_revision,
        branch_id=revision.branch_id,
        action=revision.action,
        source=revision.source,
        rationale=revision.rationale,
        patch_digest=revision.patch_digest,
        state_digest=resulting_state_digest,
        mir_digest=resulting_mir_digest,
    )
    return replace(
        revision,
        contract_revision=current_revision,
        parent_contract_revision=parent_contract_revision,
        state_digest=resulting_state_digest,
        mir_digest=resulting_mir_digest,
    )


def _rewrite_current_state(
    contract: NaturalLanguageModelContract,
    **changes,
) -> NaturalLanguageModelContract:
    provisional = replace(contract, **changes)
    latest = _rehash_revision(
        contract,
        contract.lineage[-1],
        parent_contract_revision=contract.lineage[-1].parent_contract_revision,
        state_digest_value=state_digest(provisional),
    )
    return replace(
        provisional,
        contract_revision=latest.contract_revision,
        parent_contract_revision=latest.parent_contract_revision,
        lineage=contract.lineage[:-1] + (latest,),
    )


def _redigested_confirmed_non_patch_contract(
    *,
    source: str,
    lifecycle: str,
) -> NaturalLanguageModelContract:
    unconfirmed = replace(
        _inferred_assumption(),
        source=source,
        materiality="low",
        confirmed=False,
    )
    confirmed = (replace(unconfirmed, confirmed=True),)

    if lifecycle == "create-only":
        created = _mode_contract(
            mode="research",
            requested_mode="research",
            assumptions=(unconfirmed,),
        )
        return _rewrite_current_state(created, assumptions=confirmed)

    if lifecycle != "promote-lock":
        raise AssertionError(f"unknown lifecycle: {lifecycle}")

    created = _mode_contract(
        mode="quick",
        requested_mode="quick",
        assumptions=(unconfirmed,),
    )
    promoted = promote_to_research(
        created,
        rationale="Promote the hostile fixture.",
        source="conversation",
    )
    locked = lock_contract(
        promoted,
        reason="Lock the hostile fixture.",
        source="conversation",
    )

    created_state = replace(created, assumptions=confirmed)
    root = _rehash_revision(
        locked,
        locked.lineage[0],
        parent_contract_revision="",
        state_digest_value=state_digest(created_state),
    )
    promoted_state = replace(promoted, assumptions=confirmed)
    promote_revision = _rehash_revision(
        locked,
        locked.lineage[1],
        parent_contract_revision=root.contract_revision,
        state_digest_value=state_digest(promoted_state),
    )
    lock_state = replace(
        locked,
        assumptions=confirmed,
        lock=replace(
            locked.lock,
            locked_contract_revision=promote_revision.contract_revision,
        ),
    )
    lock_revision = _rehash_revision(
        locked,
        locked.lineage[2],
        parent_contract_revision=promote_revision.contract_revision,
        state_digest_value=state_digest(lock_state),
    )
    return replace(
        lock_state,
        contract_revision=lock_revision.contract_revision,
        parent_contract_revision=promote_revision.contract_revision,
        lineage=(root, promote_revision, lock_revision),
    )


def _redigested_preconfirmed_state_neutral_patch_contract(
    *,
    source: str,
    patch_kind: str,
) -> NaturalLanguageModelContract:
    unconfirmed = replace(
        _inferred_assumption(),
        source=source,
        materiality="low",
        confirmed=False,
    )
    created = _mode_contract(
        mode="research",
        requested_mode="research",
        assumptions=(unconfirmed,),
    )
    if patch_kind == "no-op":
        threshold = created.mir.processes[0].params["threshold"]
    elif patch_kind == "mir-only":
        threshold = 0.6
    else:
        raise AssertionError(f"unknown patch kind: {patch_kind}")
    patch = _semantic_patch(
        created,
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/processes/0/params/threshold",
                value=threshold,
            ),
        ),
        rationale=f"Apply a hostile {patch_kind} patch.",
    )
    patched = apply_semantic_patch(created, patch)
    confirmed = (replace(unconfirmed, confirmed=True),)

    created_state = replace(created, assumptions=confirmed)
    root = _rehash_revision(
        patched,
        patched.lineage[0],
        parent_contract_revision="",
        state_digest_value=state_digest(created_state),
    )
    patched_state = replace(patched, assumptions=confirmed)
    patch_revision = _rehash_revision(
        patched,
        patched.lineage[1],
        parent_contract_revision=root.contract_revision,
        state_digest_value=state_digest(patched_state),
    )
    return replace(
        patched_state,
        contract_revision=patch_revision.contract_revision,
        parent_contract_revision=root.contract_revision,
        lineage=(root, patch_revision),
    )


def _assert_lineage_is_fully_redigested(
    contract: NaturalLanguageModelContract,
) -> None:
    assert contract.lineage[-1].state_digest == state_digest(contract)
    for index, revision in enumerate(contract.lineage):
        expected_parent = (
            ""
            if index == 0
            else contract.lineage[index - 1].contract_revision
        )
        assert revision.parent_contract_revision == expected_parent
        assert revision.contract_revision == contract_revision_digest(
            contract_id=contract.contract_id,
            parent_contract_revision=revision.parent_contract_revision,
            branch_id=revision.branch_id,
            action=revision.action,
            source=revision.source,
            rationale=revision.rationale,
            patch_digest=revision.patch_digest,
            state_digest=revision.state_digest,
            mir_digest=revision.mir_digest,
        )


def _locked_contract() -> NaturalLanguageModelContract:
    return lock_contract(
        _ready_research_contract(),
        reason="Freeze the reviewed contract.",
        source="system",
    )


def _locked_research_child() -> NaturalLanguageModelContract:
    child = branch_contract(
        _locked_contract(),
        branch_id="child",
        mode="research",
        rationale="Open a research child.",
        source="conversation",
    )
    return lock_contract(
        child,
        reason="Freeze the research child.",
        source="system",
    )


def _redigested_research_lock_branch(
    contract: NaturalLanguageModelContract,
) -> NaturalLanguageModelContract:
    root = _rehash_revision(
        contract,
        contract.lineage[0],
        parent_contract_revision="",
        state_digest_value=state_digest(contract),
        mir_digest_value=contract.mir_digest,
    )
    lock_reason = "Freeze the imported research contract."
    locked_state = replace(
        contract,
        lock=ContractLock(
            status="locked",
            locked_mir_digest=contract.mir_digest,
            locked_contract_revision=root.contract_revision,
            reason=lock_reason,
        ),
    )
    lock_prototype = RevisionRecord(
        contract_revision="0" * 64,
        parent_contract_revision=root.contract_revision,
        branch_id=contract.branch_id,
        action="lock",
        source="system",
        rationale=lock_reason,
        patch_digest=None,
        mir_digest=contract.mir_digest,
        state_digest=state_digest(locked_state),
    )
    lock_revision = _rehash_revision(
        contract,
        lock_prototype,
        parent_contract_revision=root.contract_revision,
        state_digest_value=state_digest(locked_state),
        mir_digest_value=contract.mir_digest,
    )

    branch_rationale = "Open a quick child from the imported lock."
    child_routing = RoutingDecision(
        requested_mode=contract.routing.requested_mode,
        resolved_mode="quick",
        rationale=contract.routing.rationale + (branch_rationale,),
        overridden=(
            contract.routing.requested_mode != "auto"
            and contract.routing.requested_mode != "quick"
        ),
    )
    child_state = replace(
        contract,
        branch_id="imported-child",
        mode="quick",
        routing=child_routing,
        lock=ContractLock(),
    )
    branch_prototype = RevisionRecord(
        contract_revision="0" * 64,
        parent_contract_revision=lock_revision.contract_revision,
        branch_id=child_state.branch_id,
        action="branch",
        source="import",
        rationale=branch_rationale,
        patch_digest=None,
        mir_digest=contract.mir_digest,
        state_digest=state_digest(child_state),
    )
    branch_revision = _rehash_revision(
        contract,
        branch_prototype,
        parent_contract_revision=lock_revision.contract_revision,
        state_digest_value=state_digest(child_state),
        mir_digest_value=contract.mir_digest,
    )
    return replace(
        child_state,
        contract_revision=branch_revision.contract_revision,
        parent_contract_revision=lock_revision.contract_revision,
        lineage=(root, lock_revision, branch_revision),
    )


@pytest.mark.parametrize(
    ("requested_mode", "resolved_mode", "expected_overridden"),
    [
        ("auto", "quick", False),
        ("auto", "research", False),
        ("quick", "quick", False),
        ("research", "research", False),
        ("quick", "research", True),
        ("research", "quick", True),
    ],
)
def test_routing_decision_uses_canonical_overridden_truth_table(
    requested_mode,
    resolved_mode,
    expected_overridden,
):
    routing = RoutingDecision(
        requested_mode=requested_mode,
        resolved_mode=resolved_mode,
        rationale=("Resolve the requested mode.",),
        overridden=expected_overridden,
    )

    routing.validate()
    assert RoutingDecision.from_dict(routing.to_dict()) == routing


@pytest.mark.parametrize(
    ("requested_mode", "resolved_mode"),
    [
        ("auto", "quick"),
        ("auto", "research"),
        ("quick", "quick"),
        ("research", "research"),
        ("quick", "research"),
        ("research", "quick"),
    ],
)
def test_persisted_contract_rejects_inconsistent_overridden_after_redigest(
    requested_mode,
    resolved_mode,
):
    contract = _mode_contract(
        mode=resolved_mode,
        requested_mode=requested_mode,
    )
    forged = _rewrite_current_state(
        contract,
        routing=replace(
            contract.routing,
            overridden=not contract.routing.overridden,
        ),
    )

    _assert_persisted_contract_rejected(
        forged,
        "routing.overridden.*requested_mode.*resolved_mode",
    )


def test_create_model_contract_is_deterministic_and_preserves_mir_exactly():
    mir = _threshold_mir()

    first = create_model_contract(
        contract_id="threshold-demo",
        branch_id="main",
        mode="quick",
        mir=mir,
        assumptions=(),
        unresolved_decisions=(),
        routing=_routing(),
        source="conversation",
    )
    second = create_model_contract(
        contract_id="threshold-demo",
        branch_id="main",
        mode="quick",
        mir=mir,
        assumptions=(),
        unresolved_decisions=(),
        routing=_routing(),
        source="conversation",
    )

    assert first == second
    assert first.schema == MODEL_CONTRACT_SCHEMA
    assert first.mir.to_dict() == mir.to_dict()
    assert first.mir.to_json() == mir.to_json()
    assert first.mir_digest == mir_digest(mir)
    assert first.mir_digest == _canonical_digest(mir.to_dict())
    assert first.lock == ContractLock(
        status="unlocked",
        locked_mir_digest="",
        locked_contract_revision="",
        reason="",
    )
    assert first.parent_contract_revision == ""
    assert len(first.lineage) == 1
    assert first.lineage[0].action == "create"
    assert first.lineage[0].source == "conversation"
    assert first.lineage[0].contract_revision == first.contract_revision
    assert first.lineage[0].mir_digest == first.mir_digest
    expected_state_digest = _canonical_digest(
        {
            "mode": "quick",
            "assumptions": [],
            "unresolved_decisions": [],
            "routing": {
                "requested_mode": "quick",
                "resolved_mode": "quick",
                "rationale": ["explicit quick-mode request"],
                "overridden": False,
            },
            "lock": {
                "status": "unlocked",
                "locked_mir_digest": "",
                "locked_contract_revision": "",
                "reason": "",
            },
        }
    )
    expected_revision_digest = _canonical_digest(
        {
            "contract_id": "threshold-demo",
            "parent_contract_revision": "",
            "branch_id": "main",
            "action": "create",
            "source": "conversation",
            "rationale": "create model contract",
            "state_digest": expected_state_digest,
            "mir_digest": _canonical_digest(mir.to_dict()),
        }
    )
    assert state_digest(first) == expected_state_digest
    assert first.lineage[0].state_digest == expected_state_digest
    assert first.contract_revision == expected_revision_digest


@pytest.mark.parametrize("source", ["inferred", "default"])
@pytest.mark.parametrize("materiality", ["low", "material"])
def test_create_rejects_preconfirmed_inferred_or_default_lock_bypass(
    source,
    materiality,
):
    assumption = replace(
        _inferred_assumption(),
        source=source,
        materiality=materiality,
        confirmed=True,
    )

    with pytest.raises(
        ValueError,
        match=rf"assumptions\[0\]\.confirmed.*{source}.*contract creation",
    ):
        _mode_contract(
            mode="research",
            requested_mode="research",
            assumptions=(assumption,),
        )


@pytest.mark.parametrize("source", ["inferred", "default"])
@pytest.mark.parametrize("lifecycle", ["create-only", "promote-lock"])
def test_persisted_confirmed_assumption_requires_patch_revision_evidence(
    tmp_path,
    source,
    lifecycle,
):
    forged = _redigested_confirmed_non_patch_contract(
        source=source,
        lifecycle=lifecycle,
    )
    _assert_lineage_is_fully_redigested(forged)
    assert "patch" not in {revision.action for revision in forged.lineage}
    expected_message = (
        r"confirmed inferred/default assumptions.*state-changing patch revision.*"
        r"proves only.*contract state changed during a patch.*"
        r"not which fields changed.*RevisionRecord stores only.*digest"
    )

    with pytest.raises(ValueError, match=expected_message):
        NaturalLanguageModelContract.from_dict(forged.to_dict())
    with pytest.raises(ValueError, match=expected_message):
        NaturalLanguageModelContract.from_json(forged.to_json())

    path = tmp_path / f"{lifecycle}-{source}.json"
    path.write_text(forged.to_json(), encoding="utf-8")
    with pytest.raises(ValueError, match=expected_message):
        load_model_contract(path)


@pytest.mark.parametrize("source", ["inferred", "default"])
@pytest.mark.parametrize("patch_kind", ["no-op", "mir-only"])
def test_persisted_preconfirmed_state_neutral_patch_cannot_lock(
    tmp_path,
    source,
    patch_kind,
):
    forged = _redigested_preconfirmed_state_neutral_patch_contract(
        source=source,
        patch_kind=patch_kind,
    )
    _assert_lineage_is_fully_redigested(forged)
    root, patch_revision = forged.lineage
    assert patch_revision.action == "patch"
    assert patch_revision.state_digest == root.state_digest
    if patch_kind == "no-op":
        assert patch_revision.mir_digest == root.mir_digest
    else:
        assert patch_revision.mir_digest != root.mir_digest
    expected_message = (
        r"confirmed inferred/default assumptions.*state-changing patch revision.*"
        r"proves only.*contract state changed during a patch.*"
        r"not which fields changed.*RevisionRecord stores only.*digest"
    )

    with pytest.raises(ValueError, match=expected_message):
        NaturalLanguageModelContract.from_dict(forged.to_dict())
    with pytest.raises(ValueError, match=expected_message):
        NaturalLanguageModelContract.from_json(forged.to_json())

    path = tmp_path / f"{patch_kind}-{source}.json"
    path.write_text(forged.to_json(), encoding="utf-8")
    with pytest.raises(ValueError, match=expected_message):
        load_model_contract(path)
    with pytest.raises(ValueError, match=expected_message):
        lock_contract(
            forged,
            reason="Attempt to lock without confirmation state evidence.",
            source="conversation",
        )


@pytest.mark.parametrize("source", ["inferred", "default"])
def test_patch_confirmation_revision_allows_research_readiness_and_lock(source):
    assumption = replace(
        _inferred_assumption(),
        source=source,
        materiality="material",
        confirmed=False,
    )
    contract = _mode_contract(
        mode="research",
        requested_mode="research",
        assumptions=(assumption,),
    )
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/assumptions/0/confirmed",
                value=True,
            ),
        ),
        rationale="Confirm the sourced assumption after contract creation.",
    )

    assert research_readiness(contract)["ready"] is False

    confirmed = apply_semantic_patch(contract, patch)
    restored = NaturalLanguageModelContract.from_json(confirmed.to_json())

    assert confirmed.assumptions[0].source == source
    assert confirmed.assumptions[0].confirmed is True
    assert confirmed.lineage[-1].action == "patch"
    assert (
        confirmed.lineage[-1].state_digest
        != confirmed.lineage[-2].state_digest
    )
    assert restored == confirmed
    assert research_readiness(restored)["ready"] is True

    locked = lock_contract(
        restored,
        reason="Lock after an explicit confirmation revision.",
        source="conversation",
    )
    child = branch_contract(
        locked,
        branch_id=f"{source}-confirmation-child",
        mode="quick",
        rationale="Branch after the confirmation revision and lock.",
        source="conversation",
    )
    restored_child = NaturalLanguageModelContract.from_json(child.to_json())

    assert locked.lock.status == "locked"
    assert [revision.action for revision in restored_child.lineage] == [
        "create",
        "patch",
        "lock",
        "branch",
    ]
    restored_child.validate()


def test_contract_round_trip_is_strict_and_canonical():
    contract = _contract()

    restored = NaturalLanguageModelContract.from_json(contract.to_json())

    assert restored == contract
    assert restored.to_dict() == contract.to_dict()
    assert restored.to_json() == contract.to_json()
    assert contract.to_json() == json.dumps(
        contract.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    contract.validate()


def test_create_revision_is_source_aware_but_state_and_mir_are_not():
    conversation = _contract(source="conversation")
    panel = _contract(source="panel")

    expected_mir_digest = _canonical_digest(_threshold_mir().to_dict())
    expected_state_digest = _canonical_digest(
        {
            "mode": "quick",
            "assumptions": [
                {
                    "assumption_id": "threshold-source",
                    "statement": "The initial threshold is supplied by the user.",
                    "target_path": "/mir/processes/0/params/threshold",
                    "source": "user",
                    "materiality": "material",
                    "confirmed": True,
                }
            ],
            "unresolved_decisions": [
                {
                    "decision_id": "network-choice",
                    "question": "Which observed social network should be used?",
                    "target_path": "/mir/relations",
                    "materiality": "low",
                    "status": "open",
                    "resolution": "",
                }
            ],
            "routing": {
                "requested_mode": "quick",
                "resolved_mode": "quick",
                "rationale": ["explicit quick-mode request"],
                "overridden": False,
            },
            "lock": {
                "status": "unlocked",
                "locked_mir_digest": "",
                "locked_contract_revision": "",
                "reason": "",
            },
        }
    )
    conversation_revision_payload = {
        "contract_id": "threshold-demo",
        "parent_contract_revision": "",
        "branch_id": "main",
        "action": "create",
        "source": "conversation",
        "rationale": "create model contract",
        "state_digest": expected_state_digest,
        "mir_digest": expected_mir_digest,
    }
    panel_revision_payload = {
        **conversation_revision_payload,
        "source": "panel",
    }
    expected_conversation_revision = _canonical_digest(conversation_revision_payload)
    expected_panel_revision = _canonical_digest(panel_revision_payload)

    assert conversation.mir_digest == panel.mir_digest == expected_mir_digest
    assert state_digest(conversation) == state_digest(panel) == expected_state_digest
    assert conversation.lineage[0].state_digest == expected_state_digest
    assert panel.lineage[0].state_digest == expected_state_digest
    assert conversation.contract_revision == expected_conversation_revision
    assert panel.contract_revision == expected_panel_revision
    assert conversation.contract_revision != panel.contract_revision
    assert conversation.lineage[0].source == "conversation"
    assert panel.lineage[0].source == "panel"
    assert expected_conversation_revision == contract_revision_digest(
        contract_id="threshold-demo",
        parent_contract_revision="",
        branch_id="main",
        action="create",
        source="conversation",
        rationale="create model contract",
        patch_digest=None,
        state_digest=expected_state_digest,
        mir_digest=expected_mir_digest,
    )


def test_semantic_patch_round_trip_and_digest_ignore_producer_metadata():
    operation = SemanticPatchOperation(
        op="replace",
        path="/mir/processes/0/params/threshold",
        value=0.6,
    )
    conversation = SemanticPatch(
        schema=SEMANTIC_PATCH_SCHEMA,
        base_contract_revision="a" * 64,
        source="conversation",
        rationale="Raise the adoption threshold.",
        operations=(operation,),
    )
    panel = SemanticPatch(
        schema=SEMANTIC_PATCH_SCHEMA,
        base_contract_revision="b" * 64,
        source="panel",
        rationale="Slider edit.",
        operations=(operation,),
    )

    conversation.validate()
    panel.validate()
    assert SemanticPatch.from_json(conversation.to_json()) == conversation
    assert patch_digest(conversation) == patch_digest(panel)
    assert patch_digest(conversation) == _canonical_digest([operation.to_dict()])


def test_patch_digest_accepts_any_non_string_operation_sequence():
    operation = SemanticPatchOperation(
        op="replace",
        path="/mir/processes/0/params/threshold",
        value=0.6,
    )

    assert patch_digest(UserList([operation])) == patch_digest((operation,))


@pytest.mark.parametrize("value", ["operation", b"operation"])
def test_patch_digest_rejects_text_and_bytes_sequences(value):
    with pytest.raises(
        ValueError,
        match="patch must be a SemanticPatch or operation sequence",
    ):
        patch_digest(value)


def test_patch_digest_rejects_empty_custom_sequence():
    with pytest.raises(ValueError, match="operations must be a non-empty sequence"):
        patch_digest(UserList())


def test_patch_digest_rejects_wrong_custom_sequence_element():
    with pytest.raises(
        ValueError,
        match=r"operations\[0\] must be a SemanticPatchOperation",
    ):
        patch_digest(UserList([object()]))


def test_patch_digest_validates_custom_sequence_operations():
    invalid = SemanticPatchOperation(
        op="move",
        path="/mir/processes/0/params/threshold",
        value=0.6,
    )

    with pytest.raises(ValueError, match=r"operations\[0\]\.op"):
        patch_digest(UserList([invalid]))


def test_apply_semantic_patch_supports_constrained_json_patch_operations():
    contract = _contract()
    before = contract.to_dict()
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/metadata/name",
                value="Revised threshold adoption",
            ),
            SemanticPatchOperation(
                op="replace",
                path="/mir/processes/0/params/threshold",
                value=0.6,
            ),
            SemanticPatchOperation(
                op="add",
                path="/mir/run/params/climate~1risk",
                value="high",
            ),
            SemanticPatchOperation(
                op="add",
                path="/mir/run/params/sensor~0id",
                value=17,
            ),
            SemanticPatchOperation(
                op="add",
                path="/mir/run/params/01",
                value="dictionary key",
            ),
            SemanticPatchOperation(
                op="add",
                path="/mir/entities/0",
                value={"name": "observer"},
            ),
            SemanticPatchOperation(
                op="add",
                path="/mir/entities/-",
                value={"name": "institution"},
            ),
            SemanticPatchOperation(op="remove", path="/mir/state/0"),
            SemanticPatchOperation(
                op="replace",
                path="/assumptions/0/confirmed",
                value=False,
            ),
            SemanticPatchOperation(
                op="replace",
                path="/unresolved_decisions/0/status",
                value="resolved",
            ),
            SemanticPatchOperation(
                op="replace",
                path="/unresolved_decisions/0/resolution",
                value="Use the observed school network.",
            ),
        ),
        rationale="Revise the model through all supported operations.",
    )

    result = model_contract.apply_semantic_patch(contract, patch)

    patched_mir = result.mir
    assert contract.to_dict() == before
    assert patched_mir.metadata.name == "Revised threshold adoption"
    assert patched_mir.processes[0].params["threshold"] == 0.6
    assert patched_mir.run.params == {
        "steps": 12,
        "climate/risk": "high",
        "sensor~id": 17,
        "01": "dictionary key",
    }
    assert patched_mir.entities == [
        {"name": "observer"},
        {"name": "person"},
        {"name": "institution"},
    ]
    assert patched_mir.state == []
    assert result.assumptions[0].confirmed is False
    assert result.unresolved_decisions[0].status == "resolved"
    assert (
        result.unresolved_decisions[0].resolution
        == "Use the observed school network."
    )
    assert result.parent_contract_revision == contract.contract_revision
    assert result.contract_revision != contract.contract_revision
    assert len(result.lineage) == len(contract.lineage) + 1
    assert result.lineage[-1].action == "patch"
    assert result.lineage[-1].source == patch.source
    assert result.lineage[-1].rationale == patch.rationale
    assert result.lineage[-1].patch_digest == patch_digest(patch)
    assert result.lineage[-1].mir_digest == result.mir_digest
    assert result.lineage[-1].state_digest == state_digest(result)
    result.validate()


def test_conversation_and_panel_patch_results_share_semantic_identity_only():
    contract = _contract()
    before = contract.to_dict()
    operations = (
        SemanticPatchOperation(
            op="replace",
            path="/mir/processes/0/params/threshold",
            value=0.6,
        ),
    )
    conversation_patch = _semantic_patch(
        contract,
        operations,
        source="conversation",
        rationale="Raise the threshold.",
    )
    panel_patch = _semantic_patch(
        contract,
        operations,
        source="panel",
        rationale="Raise the threshold.",
    )

    conversation = model_contract.apply_semantic_patch(contract, conversation_patch)
    panel = model_contract.apply_semantic_patch(contract, panel_patch)

    assert contract.to_dict() == before
    assert patch_digest(conversation_patch) == patch_digest(panel_patch)
    assert conversation.mir_digest == panel.mir_digest
    assert conversation.mir.to_dict() == panel.mir.to_dict()
    assert state_digest(conversation) == state_digest(panel)
    assert conversation.lineage[-1].source == "conversation"
    assert panel.lineage[-1].source == "panel"
    assert conversation.lineage[-1].patch_digest == panel.lineage[-1].patch_digest
    assert conversation.contract_revision != panel.contract_revision
    assert conversation.parent_contract_revision == contract.contract_revision
    assert panel.parent_contract_revision == contract.contract_revision


@pytest.mark.parametrize(
    "path",
    [
        "/schema",
        "/contract_id",
        "/branch_id",
        "/mode",
        "/routing",
        "/lock",
        "/mir_digest",
        "/contract_revision",
        "/parent_contract_revision",
        "/lineage",
        "/mir/metadata/provenance",
        "/mir/fidelity",
        "/mir/trace",
        "/mir/extensions",
        "/mir/extensions/private",
    ],
)
def test_apply_semantic_patch_rejects_every_forbidden_root_atomically(path):
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="replace", path=path, value=None),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, path)


def test_apply_semantic_patch_authorizes_all_paths_before_mutation():
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/run/params/missing",
                value=True,
            ),
            SemanticPatchOperation(op="replace", path="/schema", value="other"),
        ),
    )

    _assert_patch_rejected_without_mutation(contract, patch, "/schema")


def test_apply_semantic_patch_rejects_stale_base_revision_atomically():
    contract = _contract()
    patch = replace(
        _semantic_patch(
            contract,
            (
                SemanticPatchOperation(
                    op="replace",
                    path="/mir/metadata/name",
                    value="stale edit",
                ),
            ),
        ),
        base_contract_revision="0" * 64,
    )

    _assert_patch_rejected_without_mutation(
        contract,
        patch,
        "base_contract_revision",
    )


def test_apply_semantic_patch_rejects_unsupported_operation_atomically():
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="move",
                path="/mir/metadata/name",
                value="unsupported",
            ),
        ),
    )

    _assert_patch_rejected_without_mutation(contract, patch, "operations[0].op")


@pytest.mark.parametrize(
    "path",
    [
        "mir/metadata/name",
        "/mir/run/params/bad~2escape",
        "/mir/run/params/trailing~",
    ],
)
def test_apply_semantic_patch_rejects_malformed_json_pointer_atomically(path):
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="replace", path=path, value="invalid"),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, "operations[0].path")


def test_empty_json_pointer_is_valid_but_document_root_is_not_patchable():
    contract = _contract()
    operation = SemanticPatchOperation(op="replace", path="", value={})
    patch = _semantic_patch(contract, (operation,))

    assert model_contract._decode_json_pointer("", field_name="path") == ()
    operation.validate()
    error = _assert_patch_rejected_without_mutation(
        contract,
        patch,
        "root-object replacement",
    )
    assert "operations[0].path" in str(error)


@pytest.mark.parametrize("path", ["/", "/mir", "/mir/metadata", "/mir/run"])
def test_apply_semantic_patch_rejects_disallowed_parent_paths_atomically(path):
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="replace", path=path, value={}),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, path)


@pytest.mark.parametrize("op", ["replace", "remove"])
def test_apply_semantic_patch_rejects_missing_target_atomically(op):
    contract = _contract()
    operation_kwargs = {
        "op": op,
        "path": "/mir/run/params/missing",
    }
    if op == "replace":
        operation_kwargs["value"] = True
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(**operation_kwargs),),
    )

    _assert_patch_rejected_without_mutation(
        contract,
        patch,
        "/mir/run/params/missing",
    )


@pytest.mark.parametrize(
    ("op", "path"),
    [
        ("replace", "/mir/entities/-1"),
        ("replace", "/mir/entities/01"),
        ("replace", "/mir/entities/2"),
        ("add", "/mir/entities/2"),
        ("replace", "/mir/entities/-"),
        ("remove", "/mir/entities/-"),
        ("add", "/mir/run/params/-"),
        ("add", "/mir/entities/-/name"),
    ],
)
def test_apply_semantic_patch_rejects_invalid_list_index_atomically(op, path):
    contract = _contract()
    operation_kwargs = {"op": op, "path": path}
    if op != "remove":
        operation_kwargs["value"] = {"name": "invalid"}
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(**operation_kwargs),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, path)


def test_apply_semantic_patch_rejects_very_long_array_index_deterministically():
    contract = _contract()
    index = "9" * 5000
    path = f"/mir/entities/{index}"
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="replace", path=path, value={}),),
    )

    error = _assert_patch_rejected_without_mutation(contract, patch, "array index")

    assert path in str(error)
    assert "Exceeds the limit" not in str(error)


def test_apply_semantic_patch_rejects_unknown_mir_field_atomically():
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="add",
                path="/mir/processes/0/unknown",
                value="must not be dropped",
            ),
        ),
    )

    _assert_patch_rejected_without_mutation(contract, patch, "unknown")


@pytest.mark.parametrize("value", [True, 7.0])
def test_apply_semantic_patch_rejects_silent_mir_type_coercion(value):
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/run/seed",
                value=value,
            ),
        ),
    )

    _assert_patch_rejected_without_mutation(contract, patch, "round-trip exactly")


@pytest.mark.parametrize(
    "path",
    [
        "/assumptions/0/unknown",
        "/unresolved_decisions/0/unknown",
    ],
)
def test_apply_semantic_patch_rejects_unknown_record_field_atomically(path):
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="add", path=path, value=True),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, "unknown")


def test_apply_semantic_patch_rejects_silently_defaulted_record_field():
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="remove",
                path="/unresolved_decisions/0/resolution",
            ),
        ),
    )

    _assert_patch_rejected_without_mutation(contract, patch, "round-trip exactly")


@pytest.mark.parametrize("path", ["/assumptions", "/unresolved_decisions"])
def test_apply_semantic_patch_rejects_removing_required_record_root(path):
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="remove", path=path),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, path.removeprefix("/"))


@pytest.mark.parametrize(
    ("assumptions", "unresolved_decisions", "expected_message"),
    [
        (
            (
                _assumption(),
                replace(_assumption(), statement="A duplicate assumption record."),
            ),
            (_decision(),),
            "duplicate assumption_id",
        ),
        (
            (_assumption(),),
            (
                _decision(),
                replace(_decision(), question="A duplicate decision record?"),
            ),
            "duplicate decision_id",
        ),
    ],
)
def test_contract_rejects_duplicate_audit_record_ids(
    assumptions,
    unresolved_decisions,
    expected_message,
):
    with pytest.raises(ValueError, match=expected_message):
        _contract_with_audit_records(
            assumptions=assumptions,
            unresolved_decisions=unresolved_decisions,
        )


@pytest.mark.parametrize(
    ("path", "value", "expected_message"),
    [
        (
            "/assumptions/0/assumption_id",
            "renamed-threshold-source",
            "existing assumption_id 'threshold-source' must be preserved",
        ),
        (
            "/assumptions/0/source",
            "user",
            "source for assumption_id 'threshold-source' must not change",
        ),
        (
            "/unresolved_decisions/0/decision_id",
            "renamed-network-choice",
            "existing decision_id 'network-choice' must be preserved",
        ),
    ],
)
def test_patch_rejects_direct_audit_identity_or_source_rewrite(
    path,
    value,
    expected_message,
):
    contract = _contract_with_audit_records(
        assumptions=(_inferred_assumption(),),
        unresolved_decisions=(_decision(),),
    )
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="replace", path=path, value=value),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, expected_message)


@pytest.mark.parametrize(
    ("path", "value", "expected_message"),
    [
        (
            "/assumptions/0",
            replace(
                _inferred_assumption(),
                source="user",
                confirmed=True,
            ).to_dict(),
            "source for assumption_id 'threshold-source' must not change",
        ),
        (
            "/unresolved_decisions/0",
            replace(
                _decision(),
                decision_id="renamed-network-choice",
            ).to_dict(),
            "existing decision_id 'network-choice' must be preserved",
        ),
    ],
)
def test_patch_rejects_whole_audit_record_identity_or_source_replacement(
    path,
    value,
    expected_message,
):
    contract = _contract_with_audit_records(
        assumptions=(_inferred_assumption(),),
        unresolved_decisions=(_decision(),),
    )
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="replace", path=path, value=value),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, expected_message)


@pytest.mark.parametrize(
    ("path", "value", "expected_message"),
    [
        (
            "/assumptions",
            [_second_assumption().to_dict()],
            "existing assumption_id 'threshold-source' must be preserved",
        ),
        (
            "/assumptions",
            [
                replace(
                    _inferred_assumption(),
                    source="user",
                    confirmed=True,
                ).to_dict(),
                _second_assumption().to_dict(),
            ],
            "source for assumption_id 'threshold-source' must not change",
        ),
        (
            "/unresolved_decisions",
            [_second_decision().to_dict()],
            "existing decision_id 'network-choice' must be preserved",
        ),
    ],
)
def test_patch_rejects_whole_audit_list_identity_or_source_replacement(
    path,
    value,
    expected_message,
):
    contract = _contract_with_audit_records(
        assumptions=(_inferred_assumption(), _second_assumption()),
        unresolved_decisions=(_decision(), _second_decision()),
    )
    patch = _semantic_patch(
        contract,
        (SemanticPatchOperation(op="replace", path=path, value=value),),
    )

    _assert_patch_rejected_without_mutation(contract, patch, expected_message)


@pytest.mark.parametrize(
    ("operations", "expected_message"),
    [
        (
            (
                SemanticPatchOperation(op="remove", path="/assumptions/0"),
                SemanticPatchOperation(
                    op="add",
                    path="/assumptions/-",
                    value=replace(
                        _inferred_assumption(),
                        source="user",
                        confirmed=True,
                    ).to_dict(),
                ),
            ),
            "source for assumption_id 'threshold-source' must not change",
        ),
        (
            (
                SemanticPatchOperation(
                    op="remove",
                    path="/unresolved_decisions/0",
                ),
                SemanticPatchOperation(
                    op="add",
                    path="/unresolved_decisions/-",
                    value=replace(
                        _decision(),
                        decision_id="renamed-network-choice",
                    ).to_dict(),
                ),
            ),
            "existing decision_id 'network-choice' must be preserved",
        ),
    ],
)
def test_patch_rejects_remove_add_audit_identity_bypass(
    operations,
    expected_message,
):
    contract = _contract_with_audit_records(
        assumptions=(_inferred_assumption(),),
        unresolved_decisions=(_decision(),),
    )
    patch = _semantic_patch(contract, operations)

    _assert_patch_rejected_without_mutation(contract, patch, expected_message)


@pytest.mark.parametrize(
    ("operations", "expected_message"),
    [
        (
            (
                SemanticPatchOperation(
                    op="add",
                    path="/assumptions/-",
                    value=replace(
                        _inferred_assumption(),
                        statement="A duplicate existing assumption.",
                    ).to_dict(),
                ),
            ),
            "duplicate assumption_id",
        ),
        (
            (
                SemanticPatchOperation(
                    op="add",
                    path="/unresolved_decisions/-",
                    value=replace(
                        _decision(),
                        question="A duplicate existing decision?",
                    ).to_dict(),
                ),
            ),
            "duplicate decision_id",
        ),
        (
            (
                SemanticPatchOperation(
                    op="add",
                    path="/assumptions/-",
                    value=replace(
                        _second_assumption(),
                        assumption_id="new-duplicate",
                    ).to_dict(),
                ),
                SemanticPatchOperation(
                    op="add",
                    path="/assumptions/-",
                    value=replace(
                        _second_assumption(),
                        assumption_id="new-duplicate",
                        statement="Another new duplicate assumption.",
                    ).to_dict(),
                ),
            ),
            "duplicate assumption_id",
        ),
        (
            (
                SemanticPatchOperation(
                    op="add",
                    path="/unresolved_decisions/-",
                    value=replace(
                        _second_decision(),
                        decision_id="new-duplicate",
                    ).to_dict(),
                ),
                SemanticPatchOperation(
                    op="add",
                    path="/unresolved_decisions/-",
                    value=replace(
                        _second_decision(),
                        decision_id="new-duplicate",
                        question="Another new duplicate decision?",
                    ).to_dict(),
                ),
            ),
            "duplicate decision_id",
        ),
    ],
)
def test_patch_rejects_existing_and_new_duplicate_audit_ids(
    operations,
    expected_message,
):
    contract = _contract_with_audit_records(
        assumptions=(_inferred_assumption(),),
        unresolved_decisions=(_decision(),),
    )
    patch = _semantic_patch(contract, operations)

    _assert_patch_rejected_without_mutation(contract, patch, expected_message)


def test_patch_allows_audit_confirmation_resolution_append_and_id_based_reorder():
    original_assumptions = (_inferred_assumption(), _second_assumption())
    original_decisions = (_decision(), _second_decision())
    contract = _contract_with_audit_records(
        assumptions=original_assumptions,
        unresolved_decisions=original_decisions,
    )
    before = contract.to_dict()
    confirmed_assumption = replace(original_assumptions[0], confirmed=True)
    resolved_decision = replace(
        original_decisions[0],
        status="resolved",
        resolution="Use the observed school network.",
    )
    added_assumption = AssumptionRecord(
        assumption_id="observed-network-available",
        statement="The observed school network is available.",
        target_path="/mir/relations",
        source="user",
        materiality="material",
        confirmed=True,
    )
    added_decision = UnresolvedDecision(
        decision_id="metric-choice",
        question="Which adoption metric should be reported?",
        target_path="/mir/metrics",
        materiality="low",
        status="open",
        resolution="",
    )
    expected_assumptions = (
        added_assumption,
        original_assumptions[1],
        confirmed_assumption,
    )
    expected_decisions = (
        added_decision,
        original_decisions[1],
        resolved_decision,
    )
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/assumptions/0/confirmed",
                value=True,
            ),
            SemanticPatchOperation(
                op="replace",
                path="/unresolved_decisions/0/status",
                value="resolved",
            ),
            SemanticPatchOperation(
                op="replace",
                path="/unresolved_decisions/0/resolution",
                value=resolved_decision.resolution,
            ),
            SemanticPatchOperation(
                op="add",
                path="/assumptions/-",
                value=added_assumption.to_dict(),
            ),
            SemanticPatchOperation(
                op="add",
                path="/unresolved_decisions/-",
                value=added_decision.to_dict(),
            ),
            SemanticPatchOperation(
                op="replace",
                path="/assumptions",
                value=[record.to_dict() for record in expected_assumptions],
            ),
            SemanticPatchOperation(
                op="replace",
                path="/unresolved_decisions",
                value=[record.to_dict() for record in expected_decisions],
            ),
        ),
    )

    result = model_contract.apply_semantic_patch(contract, patch)

    assert contract.to_dict() == before
    assert result.assumptions == expected_assumptions
    assert result.unresolved_decisions == expected_decisions
    assert {
        record.assumption_id: record.source for record in result.assumptions
    } == {
        "threshold-source": "inferred",
        "step-count-default": "default",
        "observed-network-available": "user",
    }
    result.validate()


def test_audit_identity_preflight_failure_prevents_fresh_result_apply(monkeypatch):
    contract = _contract_with_audit_records(
        assumptions=(_inferred_assumption(),),
        unresolved_decisions=(_decision(),),
    )
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/assumptions/0/source",
                value="user",
            ),
        ),
    )
    fresh_apply_calls = []
    original_fresh_apply = model_contract._apply_patch_to_fresh_copy

    def spy_fresh_apply(source, prepared_operations):
        fresh_apply_calls.append((source, prepared_operations))
        return original_fresh_apply(source, prepared_operations)

    monkeypatch.setattr(
        model_contract,
        "_apply_patch_to_fresh_copy",
        spy_fresh_apply,
    )

    _assert_patch_rejected_without_mutation(
        contract,
        patch,
        "source for assumption_id 'threshold-source' must not change",
    )
    assert fresh_apply_calls == []


def test_audit_identity_consistency_runs_in_preflight_and_formal_result(monkeypatch):
    contract = _contract_with_audit_records(
        assumptions=(_inferred_assumption(),),
        unresolved_decisions=(_decision(),),
    )
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/assumptions/0/confirmed",
                value=True,
            ),
        ),
    )
    calls = []
    original_validate = model_contract._validate_patch_audit_identities

    def spy_validate(*args, **kwargs):
        calls.append((args, kwargs))
        return original_validate(*args, **kwargs)

    monkeypatch.setattr(
        model_contract,
        "_validate_patch_audit_identities",
        spy_validate,
    )

    result = model_contract.apply_semantic_patch(contract, patch)

    assert result.assumptions[0].confirmed is True
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("invalid_operation", "expected_message"),
    [
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/run/params/missing",
                value=False,
            ),
            "/mir/run/params/missing",
        ),
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/entities/9",
                value={"name": "missing"},
            ),
            "/mir/entities/9",
        ),
    ],
)
def test_patch_preflight_failure_prevents_fresh_result_apply(
    monkeypatch,
    invalid_operation,
    expected_message,
):
    contract = _contract()
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="add",
                path="/mir/run/params/temporary",
                value=True,
            ),
            invalid_operation,
        ),
    )
    fresh_apply_calls = []
    original_fresh_apply = model_contract._apply_patch_to_fresh_copy

    def spy_fresh_apply(source, prepared_operations):
        fresh_apply_calls.append((source, prepared_operations))
        return original_fresh_apply(source, prepared_operations)

    monkeypatch.setattr(
        model_contract,
        "_apply_patch_to_fresh_copy",
        spy_fresh_apply,
    )

    _assert_patch_rejected_without_mutation(
        contract,
        patch,
        expected_message,
    )
    assert fresh_apply_calls == []


def test_patch_runs_validation_and_result_phases_with_operation_dependencies(
    monkeypatch,
):
    contract = _contract()
    before = contract.to_dict()
    operations = (
        SemanticPatchOperation(
            op="add",
            path="/mir/run/params/generated",
            value={"values": []},
        ),
        SemanticPatchOperation(
            op="add",
            path="/mir/run/params/generated/values/-",
            value=7,
        ),
    )
    patch = _semantic_patch(contract, operations)
    calls = []
    original_apply = model_contract._apply_patch_operation

    def spy_apply(document, operation, tokens):
        calls.append((document, operation.path))
        return original_apply(document, operation, tokens)

    monkeypatch.setattr(model_contract, "_apply_patch_operation", spy_apply)

    result = model_contract.apply_semantic_patch(contract, patch)

    paths = [operation.path for operation in operations]
    assert [path for _, path in calls] == paths + paths
    assert calls[0][0] is calls[1][0]
    assert calls[2][0] is calls[3][0]
    assert calls[0][0] is not calls[2][0]
    assert result.mir.run.params["generated"] == {"values": [7]}
    assert contract.to_dict() == before


def test_apply_semantic_patch_rejects_locked_contract_atomically():
    contract = _locked_contract()
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/metadata/name",
                value="locked edit",
            ),
        ),
    )

    _assert_patch_rejected_without_mutation(contract, patch, "locked")


@pytest.mark.parametrize(
    ("requested_mode", "expected_overridden"),
    [("quick", True), ("auto", False)],
)
def test_promote_to_research_preserves_semantics_and_updates_routing(
    requested_mode,
    expected_overridden,
):
    contract = _mode_contract(
        mode="quick",
        requested_mode=requested_mode,
        assumptions=(_inferred_assumption(), _second_assumption()),
        unresolved_decisions=(_decision(),),
    )
    before = contract.to_dict()

    promoted = promote_to_research(
        contract,
        rationale="Escalate this model for research use.",
        source="panel",
    )

    assert promoted.mode == "research"
    assert promoted.mir.to_dict() == contract.mir.to_dict()
    assert promoted.mir_digest == contract.mir_digest
    assert promoted.assumptions == contract.assumptions
    assert promoted.unresolved_decisions == contract.unresolved_decisions
    assert promoted.lock == contract.lock
    assert promoted.routing == RoutingDecision(
        requested_mode=requested_mode,
        resolved_mode="research",
        rationale=contract.routing.rationale
        + ("Escalate this model for research use.",),
        overridden=expected_overridden,
    )
    assert promoted.parent_contract_revision == contract.contract_revision
    assert promoted.lineage[:-1] == contract.lineage
    assert promoted.lineage[-1].action == "promote"
    assert promoted.lineage[-1].source == "panel"
    assert promoted.lineage[-1].rationale == "Escalate this model for research use."
    assert promoted.lineage[-1].mir_digest == contract.mir_digest
    assert promoted.lineage[-1].contract_revision == promoted.contract_revision
    assert contract.to_dict() == before
    promoted.validate()


@pytest.mark.parametrize(
    ("rationale", "source", "expected_message"),
    [
        ("", "conversation", "rationale"),
        ("   ", "conversation", "rationale"),
        ("research promotion", "cli", "source"),
    ],
)
def test_promote_to_research_rejects_invalid_metadata_atomically(
    rationale,
    source,
    expected_message,
):
    contract = _contract()
    before = contract.to_dict()

    with pytest.raises(ValueError, match=expected_message):
        promote_to_research(contract, rationale=rationale, source=source)

    assert contract.to_dict() == before


def test_promote_to_research_rejects_research_and_locked_contracts_atomically():
    research = _ready_research_contract()
    locked = lock_contract(
        research,
        reason="Freeze the reviewed research contract.",
        source="system",
    )

    for contract, expected_message in (
        (research, "unlocked quick"),
        (locked, "locked"),
    ):
        before = contract.to_dict()
        with pytest.raises(ValueError, match=expected_message):
            promote_to_research(
                contract,
                rationale="Invalid repeat promotion.",
                source="conversation",
            )
        assert contract.to_dict() == before


def test_research_readiness_returns_exact_sorted_stable_ids():
    assumptions = (
        replace(_inferred_assumption(), assumption_id="z-threshold"),
        replace(_inferred_assumption(), assumption_id="a-threshold"),
        _second_assumption(),
    )
    decisions = (
        replace(
            _decision(),
            decision_id="z-network",
            materiality="material",
        ),
        replace(
            _decision(),
            decision_id="a-network",
            materiality="material",
        ),
        _second_decision(),
    )
    contract = _mode_contract(
        mode="quick",
        requested_mode="auto",
        assumptions=assumptions,
        unresolved_decisions=decisions,
    )

    report = research_readiness(contract)

    assert report == {
        "ready": False,
        "issues": [
            "mode_not_research",
            "unconfirmed_material_assumptions",
            "open_material_decisions",
        ],
        "unconfirmed_material_assumptions": ["a-threshold", "z-threshold"],
        "open_material_decisions": ["a-network", "z-network"],
    }
    assert list(report) == [
        "ready",
        "issues",
        "unconfirmed_material_assumptions",
        "open_material_decisions",
    ]


def test_research_readiness_ignores_low_materiality_open_records():
    contract = _mode_contract(
        mode="research",
        requested_mode="research",
        assumptions=(_assumption(), _second_assumption()),
        unresolved_decisions=(_decision(), _second_decision()),
    )

    assert research_readiness(contract) == {
        "ready": True,
        "issues": [],
        "unconfirmed_material_assumptions": [],
        "open_material_decisions": [],
    }


def test_resolving_material_records_with_patch_allows_research_readiness():
    contract = _mode_contract(
        mode="research",
        requested_mode="research",
        assumptions=(_inferred_assumption(),),
        unresolved_decisions=(replace(_decision(), materiality="material"),),
    )
    assert research_readiness(contract) == {
        "ready": False,
        "issues": [
            "unconfirmed_material_assumptions",
            "open_material_decisions",
        ],
        "unconfirmed_material_assumptions": ["threshold-source"],
        "open_material_decisions": ["network-choice"],
    }
    patch = _semantic_patch(
        contract,
        (
            SemanticPatchOperation(
                op="replace",
                path="/assumptions/0/confirmed",
                value=True,
            ),
            SemanticPatchOperation(
                op="replace",
                path="/unresolved_decisions/0/resolution",
                value="Use the reviewed observed network.",
            ),
            SemanticPatchOperation(
                op="replace",
                path="/unresolved_decisions/0/status",
                value="resolved",
            ),
        ),
        source="panel",
        rationale="Confirm the material model choices.",
    )

    resolved = model_contract.apply_semantic_patch(contract, patch)

    assert research_readiness(resolved) == {
        "ready": True,
        "issues": [],
        "unconfirmed_material_assumptions": [],
        "open_material_decisions": [],
    }


def test_research_readiness_validates_stored_contract_identities():
    contract = replace(_ready_research_contract(), mir_digest="0" * 64)
    before = contract.to_dict()

    with pytest.raises(ValueError, match="mir_digest"):
        research_readiness(contract)

    assert contract.to_dict() == before


def test_research_readiness_reports_locked_contract_with_stable_issue_id():
    locked = lock_contract(
        _ready_research_contract(),
        reason="Freeze the reviewed research contract.",
        source="system",
    )

    assert research_readiness(locked) == {
        "ready": False,
        "issues": ["contract_locked"],
        "unconfirmed_material_assumptions": [],
        "open_material_decisions": [],
    }


def test_lock_contract_freezes_pre_lock_identities_without_recursive_revision():
    contract = _ready_research_contract()
    before = contract.to_dict()
    pre_lock_revision = contract.contract_revision
    pre_lock_mir_digest = contract.mir_digest

    locked = lock_contract(
        contract,
        reason="Freeze the reviewed research contract.",
        source="system",
    )

    assert locked.mode == "research"
    assert locked.mir.to_dict() == contract.mir.to_dict()
    assert locked.mir.metadata.provenance == contract.mir.metadata.provenance
    assert locked.mir_digest == pre_lock_mir_digest
    assert locked.assumptions == contract.assumptions
    assert locked.unresolved_decisions == contract.unresolved_decisions
    assert locked.routing == contract.routing
    assert locked.lock == ContractLock(
        status="locked",
        locked_mir_digest=pre_lock_mir_digest,
        locked_contract_revision=pre_lock_revision,
        reason="Freeze the reviewed research contract.",
    )
    assert locked.parent_contract_revision == pre_lock_revision
    assert locked.contract_revision != pre_lock_revision
    assert locked.lock.locked_contract_revision != locked.contract_revision
    assert locked.lineage[:-1] == contract.lineage
    assert locked.lineage[-1].action == "lock"
    assert locked.lineage[-1].source == "system"
    assert locked.lineage[-1].parent_contract_revision == pre_lock_revision
    assert locked.lineage[-1].state_digest == state_digest(locked)
    assert locked.contract_revision == contract_revision_digest(
        contract_id=locked.contract_id,
        parent_contract_revision=pre_lock_revision,
        branch_id=locked.branch_id,
        action="lock",
        source="system",
        rationale="Freeze the reviewed research contract.",
        patch_digest=None,
        state_digest=state_digest(locked),
        mir_digest=pre_lock_mir_digest,
    )
    assert contract.to_dict() == before
    assert NaturalLanguageModelContract.from_json(locked.to_json()) == locked
    locked.validate()


@pytest.mark.parametrize(
    ("reason", "source", "expected_message"),
    [
        ("", "system", "reason"),
        ("   ", "system", "reason"),
        ("research lock", "cli", "source"),
    ],
)
def test_lock_contract_rejects_invalid_metadata_atomically(
    reason,
    source,
    expected_message,
):
    contract = _ready_research_contract()
    before = contract.to_dict()

    with pytest.raises(ValueError, match=expected_message):
        lock_contract(contract, reason=reason, source=source)

    assert contract.to_dict() == before


def test_lock_contract_rejects_readiness_issues_in_deterministic_order():
    contract = _mode_contract(
        mode="quick",
        requested_mode="quick",
        assumptions=(_inferred_assumption(),),
        unresolved_decisions=(replace(_decision(), materiality="material"),),
    )
    before = contract.to_dict()

    with pytest.raises(ValueError) as exc_info:
        lock_contract(
            contract,
            reason="Invalid early lock.",
            source="system",
        )

    assert str(exc_info.value) == (
        "contract is not ready for research lock: mode_not_research, "
        "unconfirmed_material_assumptions, open_material_decisions"
    )
    assert contract.to_dict() == before


def test_locked_research_contract_rejects_patch_promotion_and_repeat_lock():
    locked = lock_contract(
        _ready_research_contract(),
        reason="Freeze the reviewed research contract.",
        source="system",
    )
    patch = _semantic_patch(
        locked,
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/metadata/name",
                value="locked edit",
            ),
        ),
    )
    before = locked.to_dict()

    with pytest.raises(ValueError, match="locked"):
        model_contract.apply_semantic_patch(locked, patch)
    with pytest.raises(ValueError, match="locked"):
        promote_to_research(
            locked,
            rationale="Invalid locked promotion.",
            source="conversation",
        )
    with pytest.raises(ValueError, match="locked"):
        lock_contract(
            locked,
            reason="Invalid repeated lock.",
            source="system",
        )

    assert locked.to_dict() == before


def test_branch_contract_creates_unlocked_child_from_locked_research_source():
    source = lock_contract(
        _ready_research_contract(),
        reason="Freeze the reviewed research contract.",
        source="system",
    )
    before = source.to_dict()
    source_revision = source.contract_revision

    child = branch_contract(
        source,
        branch_id="quick-sensitivity",
        mode="quick",
        rationale="Explore a quick sensitivity variant.",
        source="import",
    )

    assert child.contract_id == source.contract_id
    assert child.branch_id == "quick-sensitivity"
    assert child.mode == "quick"
    assert child.mir.to_dict() == source.mir.to_dict()
    assert child.mir.metadata.provenance == source.mir.metadata.provenance
    assert child.mir_digest == source.mir_digest
    assert child.assumptions == source.assumptions
    assert child.unresolved_decisions == source.unresolved_decisions
    assert child.lock == ContractLock()
    assert child.routing == RoutingDecision(
        requested_mode="research",
        resolved_mode="quick",
        rationale=source.routing.rationale
        + ("Explore a quick sensitivity variant.",),
        overridden=True,
    )
    assert child.parent_contract_revision == source_revision
    assert child.lineage[:-1] == source.lineage
    assert child.lineage[-1].action == "branch"
    assert child.lineage[-1].source == "import"
    assert child.lineage[-1].branch_id == "quick-sensitivity"
    assert child.lineage[-1].parent_contract_revision == source_revision
    assert child.lineage[-1].mir_digest == source.mir_digest
    assert child.lineage[-1].contract_revision == child.contract_revision
    assert source.to_dict() == before

    exposed_mir = child.mir
    exposed_mir.metadata.provenance["source"] = "mutated"
    exposed_mir.processes[0].params["threshold"] = 0.9
    assert child.mir.to_dict() == source.mir.to_dict()
    assert child.mir_digest == source.mir_digest
    child.validate()


@pytest.mark.parametrize(
    ("requested_mode", "expected_overridden"),
    [("quick", True), ("auto", False)],
)
def test_branch_contract_preserves_promoted_request_and_recomputes_override(
    requested_mode,
    expected_overridden,
):
    source = lock_contract(
        _ready_research_contract(requested_mode=requested_mode),
        reason="Freeze the promoted research contract.",
        source="system",
    )

    child = branch_contract(
        source,
        branch_id=f"{requested_mode}-research-child",
        mode="research",
        rationale="Open an unlocked research child.",
        source="conversation",
    )

    assert child.routing.requested_mode == requested_mode
    assert child.routing.resolved_mode == "research"
    assert child.routing.overridden is expected_overridden
    assert child.routing.rationale == source.routing.rationale + (
        "Open an unlocked research child.",
    )
    assert child.lock.status == "unlocked"


@pytest.mark.parametrize(
    ("branch_id", "mode", "rationale", "source", "expected_message"),
    [
        ("", "quick", "new branch", "conversation", "branch_id"),
        ("   ", "quick", "new branch", "conversation", "branch_id"),
        ("main", "quick", "new branch", "conversation", "different"),
        ("child", "auto", "new branch", "conversation", "mode"),
        ("child", "quick", "", "conversation", "rationale"),
        ("child", "quick", "   ", "conversation", "rationale"),
        ("child", "quick", "new branch", "cli", "source"),
    ],
)
def test_branch_contract_rejects_invalid_arguments_atomically(
    branch_id,
    mode,
    rationale,
    source,
    expected_message,
):
    contract = lock_contract(
        _ready_research_contract(),
        reason="Freeze the reviewed research contract.",
        source="system",
    )
    before = contract.to_dict()

    with pytest.raises(ValueError, match=expected_message):
        branch_contract(
            contract,
            branch_id=branch_id,
            mode=mode,
            rationale=rationale,
            source=source,
        )

    assert contract.to_dict() == before


def test_branch_contract_rejects_unlocked_sources_atomically():
    unlocked_research = _ready_research_contract()
    unlocked_quick = _contract()

    for contract, expected_message in (
        (unlocked_research, "locked research"),
        (unlocked_quick, "locked research"),
    ):
        before = contract.to_dict()
        with pytest.raises(ValueError, match=expected_message):
            branch_contract(
                contract,
                branch_id="invalid-child",
                mode="quick",
                rationale="Invalid source state.",
                source="conversation",
            )
        assert contract.to_dict() == before


def test_branch_contract_rejects_reusing_any_lineage_branch_id_atomically():
    locked_child = _locked_research_child()
    before = locked_child.to_dict()

    with pytest.raises(ValueError, match="branch_id.*already used.*lineage"):
        branch_contract(
            locked_child,
            branch_id="main",
            mode="research",
            rationale="Attempt to return to the root branch identity.",
            source="conversation",
        )

    assert locked_child.to_dict() == before


def test_persisted_branch_rejects_reused_lineage_id_after_full_redigest():
    locked_child = _locked_research_child()
    rationale = "Forge a return to the root branch identity."
    routing = RoutingDecision(
        requested_mode=locked_child.routing.requested_mode,
        resolved_mode="research",
        rationale=locked_child.routing.rationale + (rationale,),
        overridden=(
            locked_child.routing.requested_mode != "auto"
            and locked_child.routing.requested_mode != "research"
        ),
    )
    provisional = replace(
        locked_child,
        branch_id="main",
        mode="research",
        routing=routing,
        lock=ContractLock(),
    )
    branch_prototype = RevisionRecord(
        contract_revision="0" * 64,
        parent_contract_revision=locked_child.contract_revision,
        branch_id="main",
        action="branch",
        source="import",
        rationale=rationale,
        patch_digest=None,
        mir_digest=locked_child.mir_digest,
        state_digest=state_digest(provisional),
    )
    branch_revision = _rehash_revision(
        locked_child,
        branch_prototype,
        parent_contract_revision=locked_child.contract_revision,
        state_digest_value=state_digest(provisional),
        mir_digest_value=locked_child.mir_digest,
    )
    forged = replace(
        provisional,
        contract_revision=branch_revision.contract_revision,
        parent_contract_revision=locked_child.contract_revision,
        lineage=locked_child.lineage + (branch_revision,),
    )

    _assert_persisted_contract_rejected(
        forged,
        "branch_id.*already appeared.*branch action",
    )


def test_persisted_quick_locked_contract_is_rejected_after_redigest():
    locked = _locked_contract()
    routing = RoutingDecision(
        requested_mode="research",
        resolved_mode="quick",
        rationale=locked.routing.rationale + ("Forge quick mode after lock.",),
        overridden=True,
    )
    forged = _rewrite_current_state(locked, mode="quick", routing=routing)

    _assert_persisted_contract_rejected(
        forged,
        "locked contract.*research mode",
    )


def test_persisted_locked_contract_rejects_unconfirmed_material_assumption():
    locked = _locked_contract()
    assumptions = (
        replace(_assumption(), confirmed=False),
        _second_assumption(),
    )
    forged = _rewrite_current_state(locked, assumptions=assumptions)

    _assert_persisted_contract_rejected(
        forged,
        "unconfirmed material assumptions.*threshold-source",
    )


def test_persisted_locked_contract_rejects_open_material_decision():
    locked = _locked_contract()
    decisions = (replace(_decision(), materiality="material"),)
    forged = _rewrite_current_state(
        locked,
        unresolved_decisions=decisions,
    )

    _assert_persisted_contract_rejected(
        forged,
        "open material decisions.*network-choice",
    )


def test_persisted_create_to_branch_transition_is_rejected_after_redigest():
    base = _contract()
    branch_id = "forged-child"
    provisional = replace(base, branch_id=branch_id)
    branch_prototype = replace(
        base.lineage[-1],
        parent_contract_revision=base.contract_revision,
        branch_id=branch_id,
        action="branch",
        source="system",
        rationale="Forge a branch without a source lock.",
    )
    branch_revision = _rehash_revision(
        base,
        branch_prototype,
        parent_contract_revision=base.contract_revision,
        state_digest_value=state_digest(provisional),
    )
    forged = replace(
        provisional,
        contract_revision=branch_revision.contract_revision,
        parent_contract_revision=base.contract_revision,
        lineage=base.lineage + (branch_revision,),
    )

    _assert_persisted_contract_rejected(
        forged,
        "branch action.*directly follow a lock action",
    )


def test_persisted_lock_to_patch_transition_is_rejected_after_redigest():
    locked = _locked_contract()
    provisional = replace(locked, lock=ContractLock())
    patch_prototype = RevisionRecord(
        contract_revision="0" * 64,
        parent_contract_revision=locked.contract_revision,
        branch_id=locked.branch_id,
        action="patch",
        source="conversation",
        rationale="Forge a patch directly after lock.",
        patch_digest="a" * 64,
        mir_digest=locked.mir_digest,
        state_digest=state_digest(provisional),
    )
    patch_revision = _rehash_revision(
        locked,
        patch_prototype,
        parent_contract_revision=locked.contract_revision,
        state_digest_value=state_digest(provisional),
    )
    forged = replace(
        provisional,
        contract_revision=patch_revision.contract_revision,
        parent_contract_revision=locked.contract_revision,
        lineage=locked.lineage + (patch_revision,),
    )

    _assert_persisted_contract_rejected(
        forged,
        "revision after a lock action.*branch",
    )


def test_persisted_repeated_promote_transition_is_rejected_after_redigest():
    promoted = _promoted_research_contract()
    provisional = promoted
    promote_prototype = replace(
        promoted.lineage[-1],
        parent_contract_revision=promoted.contract_revision,
        rationale="Forge a repeated promotion.",
    )
    repeated_promote = _rehash_revision(
        promoted,
        promote_prototype,
        parent_contract_revision=promoted.contract_revision,
        state_digest_value=state_digest(provisional),
    )
    forged = replace(
        provisional,
        contract_revision=repeated_promote.contract_revision,
        parent_contract_revision=promoted.contract_revision,
        lineage=promoted.lineage + (repeated_promote,),
    )

    _assert_persisted_contract_rejected(
        forged,
        "promote action.*cannot directly follow another promote action",
    )


def test_persisted_promote_rejects_research_source_after_full_redigest():
    base = _ready_research_contract()
    rationale = "Forge a promotion from an already-research contract."
    routing = RoutingDecision(
        requested_mode=base.routing.requested_mode,
        resolved_mode="research",
        rationale=base.routing.rationale + (rationale,),
        overridden=False,
    )
    provisional = replace(base, routing=routing)
    promote_prototype = RevisionRecord(
        contract_revision="0" * 64,
        parent_contract_revision=base.contract_revision,
        branch_id=base.branch_id,
        action="promote",
        source="panel",
        rationale=rationale,
        patch_digest=None,
        mir_digest=base.mir_digest,
        state_digest=state_digest(provisional),
    )
    promote_revision = _rehash_revision(
        base,
        promote_prototype,
        parent_contract_revision=base.contract_revision,
        state_digest_value=state_digest(provisional),
    )
    forged = replace(
        provisional,
        contract_revision=promote_revision.contract_revision,
        parent_contract_revision=base.contract_revision,
        lineage=base.lineage + (promote_revision,),
    )

    _assert_persisted_contract_rejected(
        forged,
        "promote action predecessor state_digest.*previous revision",
    )


def test_persisted_lock_rejects_quick_to_research_transition_after_full_redigest():
    base = _mode_contract(
        mode="quick",
        requested_mode="quick",
        assumptions=(_assumption(), _second_assumption()),
        unresolved_decisions=(_decision(),),
    )
    reason = "Forge promotion and lock as one action."
    routing = RoutingDecision(
        requested_mode=base.routing.requested_mode,
        resolved_mode="research",
        rationale=base.routing.rationale + (reason,),
        overridden=True,
    )
    lock = ContractLock(
        status="locked",
        locked_mir_digest=base.mir_digest,
        locked_contract_revision=base.contract_revision,
        reason=reason,
    )
    provisional = replace(base, mode="research", routing=routing, lock=lock)
    lock_prototype = RevisionRecord(
        contract_revision="0" * 64,
        parent_contract_revision=base.contract_revision,
        branch_id=base.branch_id,
        action="lock",
        source="system",
        rationale=reason,
        patch_digest=None,
        mir_digest=base.mir_digest,
        state_digest=state_digest(provisional),
    )
    lock_revision = _rehash_revision(
        base,
        lock_prototype,
        parent_contract_revision=base.contract_revision,
        state_digest_value=state_digest(provisional),
    )
    forged = replace(
        provisional,
        contract_revision=lock_revision.contract_revision,
        parent_contract_revision=base.contract_revision,
        lineage=base.lineage + (lock_revision,),
    )

    _assert_persisted_contract_rejected(
        forged,
        "lock action predecessor state_digest.*previous revision",
    )


@pytest.mark.parametrize("smuggled_field", ["assumptions", "decisions", "routing"])
def test_persisted_branch_rejects_non_branch_state_change_after_full_redigest(
    smuggled_field,
):
    locked = lock_contract(
        _ready_research_contract(requested_mode="quick"),
        reason="Freeze the promoted contract before branching.",
        source="system",
    )
    child = branch_contract(
        locked,
        branch_id="forged-child",
        mode="quick",
        rationale="Open a quick child.",
        source="conversation",
    )

    if smuggled_field == "assumptions":
        changes = {
            "assumptions": (
                replace(
                    child.assumptions[0],
                    statement="Smuggle an assumption edit into branching.",
                ),
                *child.assumptions[1:],
            )
        }
    elif smuggled_field == "decisions":
        changes = {
            "unresolved_decisions": (
                replace(
                    child.unresolved_decisions[0],
                    question="Smuggle a decision edit into branching?",
                ),
                *child.unresolved_decisions[1:],
            )
        }
    else:
        changes = {
            "routing": replace(
                child.routing,
                rationale=(
                    "Smuggle an earlier routing rationale into branching.",
                    *child.routing.rationale[1:],
                ),
            )
        }

    forged = _rewrite_current_state(child, **changes)

    _assert_persisted_contract_rejected(
        forged,
        "branch action predecessor state_digest.*previous revision",
    )


@pytest.mark.parametrize("action", ["promote", "branch"])
def test_persisted_routed_lifecycle_action_requires_matching_final_rationale(action):
    if action == "promote":
        contract = _promoted_research_contract()
    else:
        contract = branch_contract(
            _locked_contract(),
            branch_id="child",
            mode="quick",
            rationale="Open a valid child.",
            source="conversation",
        )
    routing = replace(
        contract.routing,
        rationale=contract.routing.rationale[:-1] + ("Forged rationale.",),
    )
    forged = _rewrite_current_state(contract, routing=routing)

    _assert_persisted_contract_rejected(
        forged,
        f"{action} action routing rationale.*revision rationale",
    )


def test_persisted_lock_requires_reason_to_match_revision_rationale():
    locked = _locked_contract()
    forged = _rewrite_current_state(
        locked,
        lock=replace(locked.lock, reason="Forged lock reason."),
    )

    _assert_persisted_contract_rejected(
        forged,
        "lock action reason.*revision rationale",
    )


@pytest.mark.parametrize(
    ("blocker", "expected_message"),
    [
        (
            "assumption",
            "lock action has unconfirmed material assumptions: threshold-source",
        ),
        (
            "decision",
            "lock action has open material decisions: network-choice",
        ),
    ],
)
def test_persisted_historical_lock_rejects_unready_records_after_full_redigest(
    blocker,
    expected_message,
):
    assumptions = (
        (replace(_assumption(), confirmed=False),)
        if blocker == "assumption"
        else (_assumption(),)
    )
    decisions = (
        (replace(_decision(), materiality="material"),)
        if blocker == "decision"
        else (_decision(),)
    )
    research = _mode_contract(
        mode="research",
        requested_mode="research",
        assumptions=assumptions,
        unresolved_decisions=decisions,
    )
    forged = _redigested_research_lock_branch(research)

    _assert_persisted_contract_rejected(forged, expected_message)


def test_persisted_historical_lock_readiness_accepts_ready_redigested_branch():
    research = _ready_research_contract()
    child = _redigested_research_lock_branch(research)

    restored = NaturalLanguageModelContract.from_dict(child.to_dict())

    assert [revision.action for revision in restored.lineage] == [
        "create",
        "lock",
        "branch",
    ]
    restored.validate()


def test_persisted_lock_revision_rejects_mir_drift_after_full_redigest():
    locked = _locked_contract()
    root, lock_revision = locked.lineage
    forged_root = _rehash_revision(
        locked,
        root,
        parent_contract_revision="",
        mir_digest_value="f" * 64,
    )
    forged_lock_record = replace(
        locked.lock,
        locked_contract_revision=forged_root.contract_revision,
    )
    provisional = replace(
        locked,
        lock=forged_lock_record,
        parent_contract_revision=forged_root.contract_revision,
    )
    forged_lock_revision = _rehash_revision(
        locked,
        lock_revision,
        parent_contract_revision=forged_root.contract_revision,
        state_digest_value=state_digest(provisional),
        mir_digest_value=locked.mir_digest,
    )
    forged = replace(
        provisional,
        contract_revision=forged_lock_revision.contract_revision,
        lineage=(forged_root, forged_lock_revision),
    )

    _assert_persisted_contract_rejected(
        forged,
        "lock action.*mir_digest.*previous revision",
    )


def test_persisted_promote_revision_rejects_mir_drift_after_full_redigest():
    promoted = _promoted_research_contract()
    root, promote_revision = promoted.lineage
    forged_root = _rehash_revision(
        promoted,
        root,
        parent_contract_revision="",
        mir_digest_value="e" * 64,
    )
    forged_promote_revision = _rehash_revision(
        promoted,
        promote_revision,
        parent_contract_revision=forged_root.contract_revision,
        state_digest_value=state_digest(promoted),
        mir_digest_value=promoted.mir_digest,
    )
    forged = replace(
        promoted,
        contract_revision=forged_promote_revision.contract_revision,
        parent_contract_revision=forged_root.contract_revision,
        lineage=(forged_root, forged_promote_revision),
    )

    _assert_persisted_contract_rejected(
        forged,
        "promote action.*mir_digest.*previous revision",
    )


def test_persisted_branch_revision_rejects_mir_drift_after_full_redigest():
    locked = _locked_contract()
    child = branch_contract(
        locked,
        branch_id="child",
        mode="quick",
        rationale="Open a valid child before forging lineage.",
        source="conversation",
    )
    root, lock_revision, branch_revision = child.lineage
    forged_root = _rehash_revision(
        child,
        root,
        parent_contract_revision="",
        mir_digest_value="d" * 64,
    )
    forged_lock_revision = _rehash_revision(
        child,
        lock_revision,
        parent_contract_revision=forged_root.contract_revision,
        mir_digest_value="d" * 64,
    )
    forged_branch_revision = _rehash_revision(
        child,
        branch_revision,
        parent_contract_revision=forged_lock_revision.contract_revision,
        state_digest_value=state_digest(child),
        mir_digest_value=child.mir_digest,
    )
    forged = replace(
        child,
        contract_revision=forged_branch_revision.contract_revision,
        parent_contract_revision=forged_lock_revision.contract_revision,
        lineage=(
            forged_root,
            forged_lock_revision,
            forged_branch_revision,
        ),
    )

    _assert_persisted_contract_rejected(
        forged,
        "branch action.*mir_digest.*source lock revision",
    )


@pytest.mark.parametrize("branch_mode", ["quick", "research"])
def test_persisted_promote_lock_branch_and_followup_patch_remain_valid(branch_mode):
    promoted = _ready_research_contract(requested_mode="quick")
    locked = lock_contract(
        promoted,
        reason="Freeze the promoted research contract.",
        source="system",
    )
    child = branch_contract(
        locked,
        branch_id=f"{branch_mode}-child",
        mode=branch_mode,
        rationale=f"Open a valid {branch_mode} child.",
        source="conversation",
    )
    restored_child = NaturalLanguageModelContract.from_dict(child.to_dict())
    patch = _semantic_patch(
        restored_child,
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/processes/0/params/threshold",
                value=0.55,
            ),
        ),
        rationale="Tune the branched threshold.",
    )

    patched = model_contract.apply_semantic_patch(restored_child, patch)
    restored_patched = NaturalLanguageModelContract.from_dict(patched.to_dict())

    assert [revision.action for revision in restored_patched.lineage[-5:]] == [
        "create",
        "promote",
        "lock",
        "branch",
        "patch",
    ]
    assert restored_patched.mir.processes[0].params["threshold"] == 0.55
    restored_patched.validate()


def test_contract_validation_rejects_locked_state_without_current_lock_action():
    locked = lock_contract(
        _ready_research_contract(),
        reason="Freeze the reviewed research contract.",
        source="system",
    )
    latest = locked.lineage[-1]
    operation_digest = "a" * 64
    forged_revision = contract_revision_digest(
        contract_id=locked.contract_id,
        parent_contract_revision=latest.parent_contract_revision,
        branch_id=latest.branch_id,
        action="patch",
        source=latest.source,
        rationale=latest.rationale,
        patch_digest=operation_digest,
        state_digest=latest.state_digest,
        mir_digest=latest.mir_digest,
    )
    forged = replace(
        locked,
        contract_revision=forged_revision,
        lineage=locked.lineage[:-1]
        + (
            replace(
                latest,
                contract_revision=forged_revision,
                action="patch",
                patch_digest=operation_digest,
            ),
        ),
    )

    _assert_persisted_contract_rejected(forged, "locked.*lock action")


def test_contract_validation_rejects_unlocked_state_with_current_lock_action():
    locked = lock_contract(
        _ready_research_contract(),
        reason="Freeze the reviewed research contract.",
        source="system",
    )
    latest = locked.lineage[-1]
    provisional = replace(locked, lock=ContractLock())
    resulting_state_digest = state_digest(provisional)
    forged_revision = contract_revision_digest(
        contract_id=locked.contract_id,
        parent_contract_revision=latest.parent_contract_revision,
        branch_id=latest.branch_id,
        action="lock",
        source=latest.source,
        rationale=latest.rationale,
        patch_digest=None,
        state_digest=resulting_state_digest,
        mir_digest=latest.mir_digest,
    )
    forged = replace(
        provisional,
        contract_revision=forged_revision,
        lineage=locked.lineage[:-1]
        + (
            replace(
                latest,
                contract_revision=forged_revision,
                state_digest=resulting_state_digest,
            ),
        ),
    )

    _assert_persisted_contract_rejected(forged, "lock action.*locked")


def test_contract_validation_rejects_non_root_create_action():
    promoted = _promoted_research_contract()
    latest = promoted.lineage[-1]
    forged_revision = contract_revision_digest(
        contract_id=promoted.contract_id,
        parent_contract_revision=latest.parent_contract_revision,
        branch_id=latest.branch_id,
        action="create",
        source=latest.source,
        rationale=latest.rationale,
        patch_digest=None,
        state_digest=latest.state_digest,
        mir_digest=latest.mir_digest,
    )
    forged = replace(
        promoted,
        contract_revision=forged_revision,
        lineage=promoted.lineage[:-1]
        + (
            replace(
                latest,
                contract_revision=forged_revision,
                action="create",
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"lineage\[1\]\.action.*root"):
        forged.validate()


def test_contract_validation_requires_branch_action_to_change_branch_id():
    source = lock_contract(
        _ready_research_contract(),
        reason="Freeze the reviewed research contract.",
        source="system",
    )
    child = branch_contract(
        source,
        branch_id="child",
        mode="quick",
        rationale="Open a quick child.",
        source="conversation",
    )
    latest = child.lineage[-1]
    forged_revision = contract_revision_digest(
        contract_id=child.contract_id,
        parent_contract_revision=latest.parent_contract_revision,
        branch_id=source.branch_id,
        action="branch",
        source=latest.source,
        rationale=latest.rationale,
        patch_digest=None,
        state_digest=latest.state_digest,
        mir_digest=latest.mir_digest,
    )
    forged = replace(
        child,
        branch_id=source.branch_id,
        contract_revision=forged_revision,
        lineage=child.lineage[:-1]
        + (
            replace(
                latest,
                contract_revision=forged_revision,
                branch_id=source.branch_id,
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"lineage.*branch_id.*change"):
        forged.validate()


def test_contract_validation_forbids_branch_id_change_without_branch_action():
    promoted = _promoted_research_contract()
    latest = promoted.lineage[-1]
    forged_revision = contract_revision_digest(
        contract_id=promoted.contract_id,
        parent_contract_revision=latest.parent_contract_revision,
        branch_id="hidden-child",
        action="promote",
        source=latest.source,
        rationale=latest.rationale,
        patch_digest=None,
        state_digest=latest.state_digest,
        mir_digest=latest.mir_digest,
    )
    forged = replace(
        promoted,
        branch_id="hidden-child",
        contract_revision=forged_revision,
        lineage=promoted.lineage[:-1]
        + (
            replace(
                latest,
                contract_revision=forged_revision,
                branch_id="hidden-child",
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"lineage.*branch_id.*branch action"):
        forged.validate()


def test_contract_validation_requires_promote_action_to_end_in_research_mode():
    promoted = _promoted_research_contract()
    latest = promoted.lineage[-1]
    routing = RoutingDecision(
        requested_mode=promoted.routing.requested_mode,
        resolved_mode="quick",
        rationale=promoted.routing.rationale,
        overridden=False,
    )
    provisional = replace(promoted, mode="quick", routing=routing)
    resulting_state_digest = state_digest(provisional)
    forged_revision = contract_revision_digest(
        contract_id=promoted.contract_id,
        parent_contract_revision=latest.parent_contract_revision,
        branch_id=latest.branch_id,
        action="promote",
        source=latest.source,
        rationale=latest.rationale,
        patch_digest=None,
        state_digest=resulting_state_digest,
        mir_digest=latest.mir_digest,
    )
    forged = replace(
        provisional,
        contract_revision=forged_revision,
        lineage=promoted.lineage[:-1]
        + (
            replace(
                latest,
                contract_revision=forged_revision,
                state_digest=resulting_state_digest,
            ),
        ),
    )

    with pytest.raises(ValueError, match="promote action.*research"):
        forged.validate()


@pytest.mark.parametrize(
    ("mutate", "expected_message"),
    [
        (lambda mir: setattr(mir.metadata, "name", 7), "mir.metadata.name"),
        (
            lambda mir: setattr(mir.metadata, "description", []),
            "mir.metadata.description",
        ),
        (lambda mir: setattr(mir.metadata, "domain", None), "mir.metadata.domain"),
        (
            lambda mir: setattr(mir.metadata, "provenance", []),
            "mir.metadata.provenance",
        ),
        (
            lambda mir: setattr(mir.space, "spatial_type", 7),
            "mir.space.spatial_type",
        ),
        (lambda mir: setattr(mir.space, "crs", []), "mir.space.crs"),
        (lambda mir: setattr(mir.space, "data_path", {}), "mir.space.data_path"),
        (lambda mir: setattr(mir, "entities", "agent"), "mir.entities"),
        (lambda mir: setattr(mir, "entities", [7]), "mir.entities[0]"),
        (lambda mir: setattr(mir, "state", None), "mir.state"),
        (lambda mir: setattr(mir, "state", [None]), "mir.state[0]"),
        (lambda mir: setattr(mir, "relations", {}), "mir.relations"),
        (lambda mir: setattr(mir, "relations", ["edge"]), "mir.relations[0]"),
        (lambda mir: setattr(mir, "layers", "layer"), "mir.layers"),
        (lambda mir: setattr(mir, "layers", [7]), "mir.layers[0]"),
        (lambda mir: setattr(mir, "metrics", None), "mir.metrics"),
        (lambda mir: setattr(mir, "metrics", ["count"]), "mir.metrics[0]"),
        (lambda mir: setattr(mir.run, "seed", True), "mir.run.seed"),
        (lambda mir: setattr(mir.run, "seed", 7.0), "mir.run.seed"),
        (lambda mir: setattr(mir.run, "params", []), "mir.run.params"),
        (
            lambda mir: setattr(mir.fidelity, "capability", 7),
            "mir.fidelity.capability",
        ),
        (lambda mir: setattr(mir.fidelity, "gate", []), "mir.fidelity.gate"),
        (
            lambda mir: setattr(mir.fidelity, "required_tokens", ["token"]),
            "mir.fidelity.required_tokens",
        ),
        (
            lambda mir: setattr(mir.fidelity, "required_tokens", ("token", 7)),
            "mir.fidelity.required_tokens",
        ),
        (
            lambda mir: setattr(mir.fidelity, "wrong_space_tokens", "token"),
            "mir.fidelity.wrong_space_tokens",
        ),
        (
            lambda mir: setattr(mir.fidelity, "wrong_space_tokens", (7,)),
            "mir.fidelity.wrong_space_tokens",
        ),
        (
            lambda mir: setattr(mir.processes[0], "mechanism", 7),
            "mir.processes[0].mechanism",
        ),
        (
            lambda mir: setattr(mir.processes[0], "params", []),
            "mir.processes[0].params",
        ),
        (lambda mir: setattr(mir, "trace", []), "mir.trace"),
        (lambda mir: setattr(mir, "extensions", []), "mir.extensions"),
    ],
)
def test_contract_local_mir_type_integrity_rejects_hostile_values(
    mutate,
    expected_message,
):
    mir = _threshold_mir()
    mutate(mir)

    with pytest.raises(ValueError) as validate_error:
        model_contract._validate_mir(mir)
    assert expected_message in str(validate_error.value)

    with pytest.raises(ValueError) as digest_error:
        mir_digest(mir)
    assert expected_message in str(digest_error.value)

    with pytest.raises(ValueError) as create_error:
        _contract_from_mir(mir)
    assert expected_message in str(create_error.value)


def test_mir_nested_integer_key_is_rejected_instead_of_colliding_with_string_key():
    string_key_mir = _threshold_mir()
    string_key_mir.run.params = {"nested": {"1": "value"}}
    integer_key_mir = _threshold_mir()
    integer_key_mir.run.params = {"nested": {1: "value"}}

    assert mir_digest(string_key_mir) == _canonical_digest(string_key_mir.to_dict())
    with pytest.raises(ValueError, match="mir.*keys must be strings"):
        mir_digest(integer_key_mir)
    with pytest.raises(ValueError, match="mir.*keys must be strings"):
        _contract_from_mir(integer_key_mir)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_mir_nonfinite_number_is_rejected_by_digest_and_creation(value):
    mir = _threshold_mir()
    mir.run.params = {"nonfinite": value}

    with pytest.raises(ValueError, match="mir.*finite"):
        mir_digest(mir)
    with pytest.raises(ValueError, match="mir.*finite"):
        _contract_from_mir(mir)


def test_contract_json_normalizes_mir_fidelity_tuple_as_json_array():
    mir = _threshold_mir()
    mir.fidelity.required_tokens = ("run_threshold_adoption",)
    mir.fidelity.wrong_space_tokens = ("RasterSpace",)

    contract = _contract_from_mir(mir)
    encoded = contract.to_json()
    restored = NaturalLanguageModelContract.from_json(encoded)

    assert json.loads(encoded)["mir"]["fidelity"]["required_tokens"] == [
        "run_threshold_adoption"
    ]
    assert json.loads(encoded)["mir"]["fidelity"]["wrong_space_tokens"] == [
        "RasterSpace"
    ]
    assert restored.mir.fidelity.required_tokens == ("run_threshold_adoption",)
    assert restored.mir.fidelity.wrong_space_tokens == ("RasterSpace",)
    assert restored.mir_digest == contract.mir_digest


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("required_tokens", ["token"]),
        ("wrong_space_tokens", ["token"]),
    ],
)
def test_mir_fidelity_token_fields_require_tuple_instances(field_name, value):
    mir = _threshold_mir()
    setattr(mir.fidelity, field_name, value)

    with pytest.raises(ValueError, match=f"mir.fidelity.{field_name}.*tuple"):
        mir_digest(mir)


def test_mir_run_params_tuple_is_rejected_while_list_digest_is_stable():
    list_mir = _threshold_mir()
    list_mir.run.params = {"values": [1, 2]}
    tuple_mir = _threshold_mir()
    tuple_mir.run.params = {"values": (1, 2)}

    assert mir_digest(list_mir) == _canonical_digest(list_mir.to_dict())
    with pytest.raises(ValueError, match=r"mir\.run\.params\.values.*tuple"):
        mir_digest(tuple_mir)
    with pytest.raises(ValueError, match=r"mir\.run\.params\.values.*tuple"):
        _contract_from_mir(tuple_mir)


def test_mir_extensions_tuple_is_rejected_while_list_round_trip_is_stable():
    list_mir = _threshold_mir()
    list_mir.extensions = {"values": [1, 2]}
    tuple_mir = _threshold_mir()
    tuple_mir.extensions = {"values": (1, 2)}

    contract = _contract_from_mir(list_mir)
    assert NaturalLanguageModelContract.from_json(contract.to_json()) == contract
    with pytest.raises(ValueError, match=r"mir\.extensions\.values.*tuple"):
        mir_digest(tuple_mir)
    with pytest.raises(ValueError, match=r"mir\.extensions\.values.*tuple"):
        _contract_from_mir(tuple_mir)


def test_contract_to_dict_and_json_reject_non_fidelity_mir_tuple():
    mir = _threshold_mir()
    mir.run.params = {"values": (1, 2)}
    contract = replace(_contract(), mir=mir)

    with pytest.raises(ValueError, match=r"mir\.run\.params\.values.*tuple"):
        contract.to_dict()
    with pytest.raises(ValueError, match=r"mir\.run\.params\.values.*tuple"):
        contract.to_json()


@pytest.mark.parametrize(
    "payload",
    [
        {1: "integer-key"},
        {"nested": {1: "integer-key"}},
        float("nan"),
        float("inf"),
        float("-inf"),
        ("tuple", "is-not-json"),
    ],
)
def test_semantic_patch_operation_rejects_non_standard_json_payload(payload):
    operation = SemanticPatchOperation(
        op="add",
        path="/mir/entities/0",
        value=payload,
    )

    with pytest.raises(ValueError, match="value"):
        operation.validate()
    with pytest.raises(ValueError, match="value"):
        patch_digest((operation,))


def test_semantic_patch_operation_json_rejects_nonfinite_constant():
    text = '{"op":"add","path":"/mir/entities/0","value":NaN}'

    with pytest.raises(ValueError, match="NaN|finite|JSON"):
        SemanticPatchOperation.from_json(text)


def test_semantic_patch_operation_standard_json_payload_round_trips_stably():
    operation = SemanticPatchOperation(
        op="add",
        path="/mir/entities/0",
        value={"weights": [1, 2.5, None, True]},
    )

    restored = SemanticPatchOperation.from_json(operation.to_json())

    assert restored == operation
    assert patch_digest((restored,)) == patch_digest((operation,))
    assert isinstance(restored.value["weights"], list)


def test_contract_from_dict_rejects_nested_mir_integer_key():
    data = _contract().to_dict()
    data["mir"]["run"]["params"] = {"nested": {1: "integer-key"}}

    with pytest.raises(ValueError, match="mir.*keys must be strings"):
        NaturalLanguageModelContract.from_dict(data)


def test_create_rejects_malformed_mir_with_field_specific_value_error():
    mir = _threshold_mir()
    mir.processes = None

    with pytest.raises(ValueError, match="mir.processes"):
        _contract_from_mir(mir)


def test_mir_digest_rejects_malformed_mir_with_field_specific_value_error():
    mir = _threshold_mir()
    mir.processes = None

    with pytest.raises(ValueError, match="mir.processes"):
        mir_digest(mir)


def test_contract_validate_rejects_malformed_mir_with_field_specific_value_error():
    mir = _threshold_mir()
    mir.processes = None
    contract = replace(_contract(), mir=mir)

    with pytest.raises(ValueError, match="mir.processes"):
        contract.validate()


def test_contract_from_dict_rejects_malformed_mir_with_field_specific_value_error():
    data = _contract().to_dict()
    data["mir"]["processes"] = None

    with pytest.raises(ValueError, match="mir.processes"):
        NaturalLanguageModelContract.from_dict(data)


def _mir_with_cycle(field_name: str) -> MIR:
    mir = _threshold_mir()
    cycle = {}
    cycle["self"] = cycle
    if field_name == "trace":
        mir.trace = cycle
    elif field_name == "run.params":
        mir.run.params = {"cycle": cycle}
    elif field_name == "extensions":
        mir.extensions = {"cycle": cycle}
    else:
        raise AssertionError(field_name)
    return mir


@pytest.mark.parametrize("field_name", ["trace", "run.params", "extensions"])
def test_cyclic_mir_public_entries_raise_value_error(field_name):
    mir = _mir_with_cycle(field_name)

    with pytest.raises(ValueError, match="mir.*cycl"):
        mir_digest(mir)
    with pytest.raises(ValueError, match="mir.*cycl"):
        _contract_from_mir(mir)

    contract = replace(_contract(), mir=mir)
    with pytest.raises(ValueError, match="mir.*cycl"):
        contract.validate()
    with pytest.raises(ValueError, match="mir.*cycl"):
        contract.to_dict()
    with pytest.raises(ValueError, match="mir.*cycl"):
        contract.to_json()


@pytest.mark.parametrize("field_name", ["trace", "run.params", "extensions"])
def test_contract_from_dict_rejects_cyclic_mir(field_name):
    data = _contract().to_dict()
    cycle = {}
    cycle["self"] = cycle
    if field_name == "trace":
        data["mir"]["trace"] = cycle
    elif field_name == "run.params":
        data["mir"]["run"]["params"] = {"cycle": cycle}
    elif field_name == "extensions":
        data["mir"]["extensions"] = {"cycle": cycle}

    with pytest.raises(ValueError, match="mir.*cycl"):
        NaturalLanguageModelContract.from_dict(data)


def test_created_contract_snapshots_source_mir_and_defensively_reads_mir():
    source_mir = _threshold_mir()
    contract = _contract_from_mir(source_mir)
    expected = contract.to_dict()
    expected_json = contract.to_json()

    source_mir.metadata.name = "mutated source"
    source_mir.processes[0].params["threshold"] = 0.9
    source_mir.run.params["steps"] = 999

    assert contract.to_dict() == expected
    assert contract.to_json() == expected_json

    exposed_mir = contract.mir
    exposed_mir.metadata.name = "mutated read"
    exposed_mir.processes[0].params["threshold"] = 0.8
    exposed_mir.run.params["steps"] = 888

    assert contract.to_dict() == expected
    assert contract.to_json() == expected_json
    assert contract.mir_digest == expected["mir_digest"]
    assert contract.contract_revision == expected["contract_revision"]
    contract.validate()


def test_restored_contract_snapshots_input_dict_and_defensively_reads_mir():
    source = _contract().to_dict()
    restored = NaturalLanguageModelContract.from_dict(source)
    expected = restored.to_dict()

    source["mir"]["metadata"]["name"] = "mutated source dict"
    source["mir"]["processes"][0]["params"]["threshold"] = 0.9

    assert restored.to_dict() == expected

    exposed_mir = restored.mir
    exposed_mir.metadata.name = "mutated restored read"
    exposed_mir.processes[0].params["threshold"] = 0.8

    assert restored.to_dict() == expected
    assert restored.mir_digest == expected["mir_digest"]
    restored.validate()


def test_patch_operation_snapshots_payload_and_defensively_reads_value():
    payload = {"nested": {"weights": [1, 2]}}
    operation = SemanticPatchOperation(
        op="add",
        path="/mir/entities/0",
        value=payload,
    )
    expected_dict = {
        "op": "add",
        "path": "/mir/entities/0",
        "value": {"nested": {"weights": [1, 2]}},
    }
    expected_digest = _canonical_digest([expected_dict])

    payload["nested"]["weights"].append(3)

    assert operation.to_dict() == expected_dict
    assert patch_digest((operation,)) == expected_digest

    exposed_value = operation.value
    exposed_value["nested"]["weights"].append(4)

    assert operation.to_dict() == expected_dict
    assert patch_digest((operation,)) == expected_digest
    operation.validate()


def test_remove_operation_serializes_without_value():
    operation = SemanticPatchOperation(op="remove", path="/mir/entities/0")

    assert operation.to_dict() == {"op": "remove", "path": "/mir/entities/0"}
    assert SemanticPatchOperation.from_dict(operation.to_dict()) == operation


@pytest.mark.parametrize(
    ("record", "field", "value", "message"),
    [
        (_assumption(), "assumption_id", "", "assumption_id"),
        (_assumption(), "statement", "  ", "statement"),
        (_assumption(), "target_path", "mir/processes", "target_path"),
        (_assumption(), "target_path", "/mir/extensions/private", "target_path"),
        (_assumption(), "source", "assistant", "source"),
        (_assumption(), "materiality", "high", "materiality"),
        (_assumption(), "confirmed", "yes", "confirmed"),
        (_decision(), "decision_id", "", "decision_id"),
        (_decision(), "question", "", "question"),
        (_decision(), "target_path", "/lock", "target_path"),
        (_decision(), "materiality", "high", "materiality"),
        (_decision(), "status", "pending", "status"),
        (_decision(), "resolution", "already chosen", "resolution"),
        (_routing(), "requested_mode", "fast", "requested_mode"),
        (_routing(), "resolved_mode", "auto", "resolved_mode"),
        (_routing(), "rationale", (), "rationale"),
        (_routing(), "overridden", 0, "overridden"),
    ],
)
def test_record_validation_errors_name_the_bad_field(record, field, value, message):
    data = record.to_dict()
    data[field] = value

    with pytest.raises(ValueError, match=message):
        type(record).from_dict(data)


@pytest.mark.parametrize("record", [_assumption(), _decision()])
def test_record_target_path_rejects_document_root_at_allowed_root_layer(record):
    data = record.to_dict()
    data["target_path"] = ""

    with pytest.raises(ValueError) as exc_info:
        type(record).from_dict(data)

    assert "allowed model path" in str(exc_info.value)
    assert "RFC 6901" not in str(exc_info.value)


def test_resolved_decision_requires_a_non_empty_resolution():
    data = _decision().to_dict()
    data.update({"status": "resolved", "resolution": ""})

    with pytest.raises(ValueError, match="resolution"):
        UnresolvedDecision.from_dict(data)


def test_open_decision_defaults_missing_resolution_to_empty_string():
    data = _decision().to_dict()
    del data["resolution"]

    restored = UnresolvedDecision.from_dict(data)

    assert restored.resolution == ""


def test_resolved_decision_rejects_missing_resolution():
    data = _decision().to_dict()
    data["status"] = "resolved"
    del data["resolution"]

    with pytest.raises(ValueError, match="resolution"):
        UnresolvedDecision.from_dict(data)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (
            {
                "status": "unlocked",
                "locked_mir_digest": "a" * 64,
                "locked_contract_revision": "",
                "reason": "",
            },
            "locked_mir_digest",
        ),
        (
            {
                "status": "locked",
                "locked_mir_digest": "bad",
                "locked_contract_revision": "b" * 64,
                "reason": "research lock",
            },
            "locked_mir_digest",
        ),
        (
            {
                "status": "locked",
                "locked_mir_digest": "a" * 64,
                "locked_contract_revision": "b" * 64,
                "reason": "",
            },
            "reason",
        ),
    ],
)
def test_lock_validation_errors_name_the_bad_field(data, message):
    with pytest.raises(ValueError, match=message):
        ContractLock.from_dict(data)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(schema="other/schema"), "schema"),
        (lambda d: d.update(contract_id=""), "contract_id"),
        (lambda d: d.update(branch_id=""), "branch_id"),
        (lambda d: d.update(mode="auto"), "mode"),
        (
            lambda d: d["routing"].update(
                resolved_mode="research",
                overridden=True,
            ),
            "routing.resolved_mode",
        ),
        (lambda d: d.update(mir_digest="0" * 64), "mir_digest"),
        (lambda d: d.update(contract_revision="0" * 64), "contract_revision"),
        (lambda d: d["lineage"][0].update(state_digest="0" * 64), "state_digest"),
        (lambda d: d["lineage"][0].update(action="edit"), "action"),
        (lambda d: d["lineage"][0].update(source="unknown"), "source"),
        (lambda d: d["lineage"][0].update(patch_digest="a" * 64), "patch_digest"),
    ],
)
def test_contract_validation_rejects_malformed_schema_records_and_digests(
    mutate, message
):
    data = _contract().to_dict()
    mutate(data)

    with pytest.raises(ValueError, match=message):
        NaturalLanguageModelContract.from_dict(data)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(extra=True), "contract.*extra"),
        (lambda d: d["assumptions"][0].update(extra=True), "assumptions\\[0\\].*extra"),
        (
            lambda d: d["unresolved_decisions"][0].update(extra=True),
            "unresolved_decisions\\[0\\].*extra",
        ),
        (lambda d: d["routing"].update(extra=True), "routing.*extra"),
        (lambda d: d["lock"].update(extra=True), "lock.*extra"),
        (lambda d: d["lineage"][0].update(extra=True), "lineage\\[0\\].*extra"),
        (lambda d: d["mir"].update(extra=True), "mir.*extra"),
    ],
)
def test_contract_from_dict_rejects_unknown_top_level_and_nested_keys(mutate, message):
    data = _contract().to_dict()
    mutate(data)

    with pytest.raises(ValueError, match=message):
        NaturalLanguageModelContract.from_dict(data)


def test_json_loaders_reject_duplicate_keys_at_any_depth():
    duplicate_contract_key = (
        '{"schema":"%s","schema":"%s"}'
        % (MODEL_CONTRACT_SCHEMA, MODEL_CONTRACT_SCHEMA)
    )
    duplicate_patch_key = (
        '{"schema":"%s","operations":[{"op":"remove","op":"remove"}]}'
        % SEMANTIC_PATCH_SCHEMA
    )

    with pytest.raises(ValueError, match="duplicate JSON object key: schema"):
        NaturalLanguageModelContract.from_json(duplicate_contract_key)
    with pytest.raises(ValueError, match="duplicate JSON object key: op"):
        SemanticPatch.from_json(duplicate_patch_key)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.update(schema="other/patch"), "schema"),
        (lambda d: d.update(source="cli"), "source"),
        (lambda d: d.update(operations=[]), "operations"),
        (lambda d: d["operations"][0].update(op="move"), "operations\\[0\\].op"),
        (lambda d: d["operations"][0].update(path="not-a-pointer"), "operations\\[0\\].path"),
        (lambda d: d["operations"][0].pop("value"), "operations\\[0\\].value"),
    ],
)
def test_semantic_patch_validation_names_malformed_fields(mutate, message):
    patch = SemanticPatch(
        schema=SEMANTIC_PATCH_SCHEMA,
        base_contract_revision="a" * 64,
        source="conversation",
        rationale="change threshold",
        operations=(
            SemanticPatchOperation(
                op="replace",
                path="/mir/processes/0/params/threshold",
                value=0.6,
            ),
        ),
    )
    data = patch.to_dict()
    mutate(data)

    with pytest.raises(ValueError, match=message):
        SemanticPatch.from_dict(data)


def test_nested_record_from_dict_rejects_unknown_keys():
    data = _assumption().to_dict()
    data["confidence"] = 0.9

    with pytest.raises(ValueError, match="AssumptionRecord.*confidence"):
        AssumptionRecord.from_dict(data)


def test_nested_record_from_dict_rejects_non_string_mapping_key():
    data = _assumption().to_dict()
    data[7] = "unexpected"

    with pytest.raises(ValueError, match="AssumptionRecord keys must be strings"):
        AssumptionRecord.from_dict(data)


def test_revision_record_round_trip_is_strict():
    revision = _contract().lineage[0]

    assert RevisionRecord.from_dict(revision.to_dict()) == revision
    data = revision.to_dict()
    data["unknown"] = True
    with pytest.raises(ValueError, match="RevisionRecord.*unknown"):
        RevisionRecord.from_dict(data)


def test_non_patch_revision_rejects_even_null_patch_digest_key():
    data = _contract().lineage[0].to_dict()
    data["patch_digest"] = None

    with pytest.raises(ValueError, match="patch_digest"):
        RevisionRecord.from_dict(data)


def test_contract_rejects_truncated_patch_lineage_without_create_root():
    base = _contract()
    parent_revision = base.contract_revision
    resulting_state_digest = state_digest(base)
    operation_digest = "a" * 64
    patch_revision = contract_revision_digest(
        contract_id="threshold-demo",
        parent_contract_revision=parent_revision,
        branch_id="main",
        action="patch",
        source="panel",
        rationale="truncated patch history",
        patch_digest=operation_digest,
        state_digest=resulting_state_digest,
        mir_digest=base.mir_digest,
    )
    truncated = replace(
        base,
        contract_revision=patch_revision,
        parent_contract_revision=parent_revision,
        lineage=(
            RevisionRecord(
                contract_revision=patch_revision,
                parent_contract_revision=parent_revision,
                branch_id="main",
                action="patch",
                source="panel",
                rationale="truncated patch history",
                patch_digest=operation_digest,
                mir_digest=base.mir_digest,
                state_digest=resulting_state_digest,
            ),
        ),
    )

    with pytest.raises(ValueError, match=r"lineage\[0\]\.action.*create"):
        truncated.validate()


def test_contract_rejects_create_root_with_parent_revision():
    base = _contract()
    parent_revision = "b" * 64
    resulting_state_digest = state_digest(base)
    create_revision = contract_revision_digest(
        contract_id="threshold-demo",
        parent_contract_revision=parent_revision,
        branch_id="main",
        action="create",
        source="conversation",
        rationale="create model contract",
        patch_digest=None,
        state_digest=resulting_state_digest,
        mir_digest=base.mir_digest,
    )
    invalid_root = replace(
        base,
        contract_revision=create_revision,
        parent_contract_revision=parent_revision,
        lineage=(
            RevisionRecord(
                contract_revision=create_revision,
                parent_contract_revision=parent_revision,
                branch_id="main",
                action="create",
                source="conversation",
                rationale="create model contract",
                patch_digest=None,
                mir_digest=base.mir_digest,
                state_digest=resulting_state_digest,
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match=r"lineage\[0\]\.parent_contract_revision.*empty",
    ):
        invalid_root.validate()


def _equivalence_fixture_records():
    base = create_model_contract(
        contract_id="threshold-adoption-equivalence",
        branch_id="main",
        mode="quick",
        mir=_threshold_mir(),
        assumptions=(),
        unresolved_decisions=(),
        routing=_routing(),
        source="system",
    )
    operation = SemanticPatchOperation(
        op="replace",
        path="/mir/processes/0/params/threshold",
        value=0.6,
    )
    patches = tuple(
        SemanticPatch(
            schema=SEMANTIC_PATCH_SCHEMA,
            base_contract_revision=base.contract_revision,
            source=source,
            rationale="Set the threshold adoption parameter to 0.6.",
            operations=(operation,),
        )
        for source in ("conversation", "panel")
    )
    return base, patches[0], patches[1]


def _canonical_fixture_bytes(record) -> bytes:
    return (record.to_json() + "\n").encode("utf-8")


def _assert_gate_scope_is_cautious(message: str) -> None:
    lowered = message.lower()
    assert "structured-patch equivalence" in lowered
    assert "natural-language utterance" in lowered
    assert "llm extraction" in lowered
    assert "ui behavior" in lowered
    assert "runtime behavior" in lowered
    assert "construct validity" in lowered
    assert "scientific truth" in lowered


def test_committed_equivalence_fixture_is_canonical_and_passes_gate():
    base_path = _FIXTURE_DIR / "base-contract.json"
    conversation_path = _FIXTURE_DIR / "conversation-patch.json"
    panel_path = _FIXTURE_DIR / "panel-patch.json"
    expected_base, expected_conversation, expected_panel = (
        _equivalence_fixture_records()
    )

    base = load_model_contract(base_path)
    conversation_patch = load_semantic_patch(conversation_path)
    panel_patch = load_semantic_patch(panel_path)

    assert base == expected_base
    assert conversation_patch == expected_conversation
    assert panel_patch == expected_panel
    for path, record in (
        (base_path, expected_base),
        (conversation_path, expected_conversation),
        (panel_path, expected_panel),
    ):
        artifact_bytes = path.read_bytes()
        assert artifact_bytes == _canonical_fixture_bytes(record)
        assert artifact_bytes.count(b"\n") == 1
        assert artifact_bytes.endswith(b"\n")
        assert b": " not in artifact_bytes
        assert b", " not in artifact_bytes

    assert base.mode == "quick"
    assert base.mir.processes[0].mechanism == "threshold_adoption"
    assert base.mir.processes[0].params["threshold"] == 0.4
    for patch, source in (
        (conversation_patch, "conversation"),
        (panel_patch, "panel"),
    ):
        assert patch.base_contract_revision == base.contract_revision
        assert patch.source == source
        assert len(patch.operations) == 1
        assert patch.operations[0] == SemanticPatchOperation(
            op="replace",
            path="/mir/processes/0/params/threshold",
            value=0.6,
        )

    conversation_payload = conversation_patch.to_dict()
    panel_payload = panel_patch.to_dict()
    assert conversation_payload.pop("source") == "conversation"
    assert panel_payload.pop("source") == "panel"
    assert conversation_payload == panel_payload

    before = base.to_dict()
    passed, message = semantic_patch_equivalence_gate(
        base,
        conversation_patch,
        panel_patch,
    )
    conversation_result = model_contract.apply_semantic_patch(
        base,
        conversation_patch,
    )
    panel_result = model_contract.apply_semantic_patch(base, panel_patch)

    assert passed is True
    assert message.startswith("PASS:")
    _assert_gate_scope_is_cautious(message)
    assert base.to_dict() == before
    assert patch_digest(conversation_patch) == patch_digest(panel_patch)
    assert conversation_result.mir_digest == panel_result.mir_digest
    assert conversation_result.mir.to_dict() == panel_result.mir.to_dict()
    assert conversation_result.mir.processes[0].params["threshold"] == 0.6
    assert conversation_result.lineage[-1].source == "conversation"
    assert panel_result.lineage[-1].source == "panel"
    assert conversation_result.contract_revision != panel_result.contract_revision


def test_equivalence_fixture_status_records_result_and_strict_boundaries():
    status = (_FIXTURE_DIR / "STATUS.md").read_text(encoding="utf-8")
    lowered = status.lower()
    base, conversation_patch, panel_patch = _equivalence_fixture_records()
    conversation_result = model_contract.apply_semantic_patch(
        base,
        conversation_patch,
    )
    panel_result = model_contract.apply_semantic_patch(base, panel_patch)
    passed, gate_message = semantic_patch_equivalence_gate(
        base,
        conversation_patch,
        panel_patch,
    )
    normalized_status = " ".join(status.replace(">", "").split())

    assert MODEL_CONTRACT_SCHEMA in status
    assert SEMANTIC_PATCH_SCHEMA in status
    assert "/mir/processes/0/params/threshold" in status
    assert "`0.4` to `0.6`" in status
    assert "PASS: structured-patch equivalence only" in status
    assert "natural-language utterance equivalence" in lowered
    assert "llm extraction equivalence" in lowered
    assert "ui behavior equivalence" in lowered
    assert "runtime behavior equivalence" in lowered
    assert "construct validity" in lowered
    assert "scientific truth" in lowered
    assert "application lock" in lowered
    assert "not a scientific prediction lock" in lowered
    assert passed is True
    assert " ".join(gate_message.split()) in normalized_status
    assert base.contract_revision in status
    assert patch_digest(conversation_patch) in status
    assert conversation_result.mir_digest in status
    assert conversation_result.contract_revision in status
    assert panel_result.contract_revision in status


@pytest.mark.parametrize(
    ("mutation", "expected_message"),
    [
        ("operation", "patch digests differ"),
        ("value", "patch digests differ"),
        (
            "base_revision",
            "validation or patch application failed: "
            "patch.base_contract_revision does not match "
            "contract.contract_revision",
        ),
        ("source", "source labels must be distinct"),
        ("mir_divergence", "patch digests differ"),
    ],
)
def test_equivalence_gate_rejects_fixture_mutations(mutation, expected_message):
    base, conversation_patch, panel_patch = _equivalence_fixture_records()
    before = base.to_dict()
    mutated = panel_patch.to_dict()

    if mutation == "operation":
        mutated["operations"][0]["op"] = "add"
    elif mutation == "value":
        mutated["operations"][0]["value"] = 0.7
    elif mutation == "base_revision":
        mutated["base_contract_revision"] = "0" * 64
    elif mutation == "source":
        mutated["source"] = "conversation"
    elif mutation == "mir_divergence":
        mutated["operations"].append(
            {
                "op": "replace",
                "path": "/mir/metadata/description",
                "value": "A divergent model description.",
            }
        )
    else:  # pragma: no cover - parametrization is closed above
        raise AssertionError(f"unknown mutation {mutation}")

    passed, message = semantic_patch_equivalence_gate(
        base,
        conversation_patch,
        SemanticPatch.from_dict(mutated),
    )

    assert passed is False
    assert message.startswith("FAIL:")
    assert expected_message in message
    _assert_gate_scope_is_cautious(message)
    assert base.to_dict() == before


@pytest.mark.parametrize(
    ("operation", "expected_detail"),
    [
        (
            SemanticPatchOperation(op="replace", path="/schema", value="other"),
            "operations[0].path '/schema' is a forbidden path",
        ),
        (
            SemanticPatchOperation(
                op="replace",
                path="/mir/entities/01",
                value={"name": "invalid"},
            ),
            "invalid array index '01' at /mir/entities/01",
        ),
    ],
)
def test_equivalence_gate_preserves_deterministic_patch_value_errors(
    operation,
    expected_detail,
):
    base, conversation_patch, panel_patch = _equivalence_fixture_records()
    invalid_patch = replace(panel_patch, operations=(operation,))

    passed, message = semantic_patch_equivalence_gate(
        base,
        conversation_patch,
        invalid_patch,
    )

    assert passed is False
    assert (
        f"validation or patch application failed: {expected_detail}"
        in message
    )
    _assert_gate_scope_is_cautious(message)


def test_equivalence_gate_checks_resulting_mir_digest_match(monkeypatch):
    base, conversation_patch, panel_patch = _equivalence_fixture_records()
    real_apply = model_contract.apply_semantic_patch
    conversation_result = real_apply(base, conversation_patch)
    divergent_panel_patch = replace(
        panel_patch,
        operations=(
            SemanticPatchOperation(
                op="replace",
                path="/mir/processes/0/params/threshold",
                value=0.7,
            ),
        ),
    )
    divergent_panel_result = real_apply(base, divergent_panel_patch)

    def apply_divergent_result(contract, patch):
        assert contract is base
        if patch.source == "conversation":
            return conversation_result
        return divergent_panel_result

    monkeypatch.setattr(
        model_contract,
        "apply_semantic_patch",
        apply_divergent_result,
    )

    passed, message = semantic_patch_equivalence_gate(
        base,
        conversation_patch,
        panel_patch,
    )

    assert patch_digest(conversation_patch) == patch_digest(panel_patch)
    assert conversation_result.mir_digest != divergent_panel_result.mir_digest
    assert passed is False
    assert "resulting MIR digests differ" in message


def test_equivalence_gate_checks_full_mir_dict_after_digest_match(monkeypatch):
    base, conversation_patch, panel_patch = _equivalence_fixture_records()
    real_apply = model_contract.apply_semantic_patch
    conversation_result = real_apply(base, conversation_patch)
    divergent_panel_patch = replace(
        panel_patch,
        operations=(
            SemanticPatchOperation(
                op="replace",
                path="/mir/processes/0/params/threshold",
                value=0.7,
            ),
        ),
    )
    divergent_panel_result = real_apply(base, divergent_panel_patch)
    disguised_revision = replace(
        divergent_panel_result.lineage[-1],
        patch_digest=conversation_result.lineage[-1].patch_digest,
        mir_digest=conversation_result.mir_digest,
    )
    disguised_panel_result = replace(
        divergent_panel_result,
        mir_digest=conversation_result.mir_digest,
        lineage=divergent_panel_result.lineage[:-1] + (disguised_revision,),
    )

    def apply_disguised_result(contract, patch):
        assert contract is base
        if patch.source == "conversation":
            return conversation_result
        return disguised_panel_result

    monkeypatch.setattr(
        model_contract,
        "apply_semantic_patch",
        apply_disguised_result,
    )

    passed, message = semantic_patch_equivalence_gate(
        base,
        conversation_patch,
        panel_patch,
    )

    assert patch_digest(conversation_patch) == patch_digest(panel_patch)
    assert conversation_result.mir_digest == disguised_panel_result.mir_digest
    assert conversation_result.mir.to_dict() != disguised_panel_result.mir.to_dict()
    assert passed is False
    assert "resulting MIR dictionaries differ" in message


def test_equivalence_gate_requires_visible_distinct_source_revisions(monkeypatch):
    base, conversation_patch, panel_patch = _equivalence_fixture_records()
    real_apply = model_contract.apply_semantic_patch
    conversation_result = real_apply(base, conversation_patch)
    panel_result = real_apply(base, panel_patch)
    hidden_source_result = replace(
        panel_result,
        lineage=panel_result.lineage[:-1]
        + (replace(panel_result.lineage[-1], source="conversation"),),
    )
    same_revision_result = replace(
        panel_result,
        contract_revision=conversation_result.contract_revision,
        lineage=panel_result.lineage[:-1]
        + (
            replace(
                panel_result.lineage[-1],
                contract_revision=conversation_result.contract_revision,
            ),
        ),
    )

    for forged_result, expected_message in (
        (hidden_source_result, "source labels are not independently visible"),
        (same_revision_result, "contract revisions must differ"),
    ):
        monkeypatch.setattr(
            model_contract,
            "apply_semantic_patch",
            lambda contract, patch, result=forged_result: (
                conversation_result if patch.source == "conversation" else result
            ),
        )

        passed, message = semantic_patch_equivalence_gate(
            base,
            conversation_patch,
            panel_patch,
        )

        assert passed is False
        assert expected_message in message


def test_equivalence_gate_contains_exceptions_without_partial_results(monkeypatch):
    base, conversation_patch, panel_patch = _equivalence_fixture_records()

    def fail_after_partial_application(contract, patch):
        raise RuntimeError("secret partial threshold=0.6")

    monkeypatch.setattr(
        model_contract,
        "apply_semantic_patch",
        fail_after_partial_application,
    )

    passed, message = semantic_patch_equivalence_gate(
        base,
        conversation_patch,
        panel_patch,
    )

    assert passed is False
    assert "RuntimeError" in message
    assert "secret" not in message
    assert "partial threshold" not in message
    assert "0.6" not in message
    _assert_gate_scope_is_cautious(message)


class _StringPathLike:
    def __init__(self, path: Path) -> None:
        self.path = path

    def __fspath__(self) -> str:
        return str(self.path)


@pytest.mark.parametrize(
    ("filename", "loader", "record_index"),
    [
        ("base-contract.json", load_model_contract, 0),
        ("conversation-patch.json", load_semantic_patch, 1),
        ("panel-patch.json", load_semantic_patch, 2),
    ],
)
def test_path_loaders_accept_path_and_pathlike(filename, loader, record_index):
    records = _equivalence_fixture_records()
    path = _FIXTURE_DIR / filename

    assert loader(path) == records[record_index]
    assert loader(_StringPathLike(path)) == records[record_index]


@pytest.mark.parametrize(
    ("loader", "record_index"),
    [
        (load_model_contract, 0),
        (load_semantic_patch, 1),
    ],
)
def test_path_loaders_accept_normal_and_exact_limit_regular_files(
    tmp_path,
    loader,
    record_index,
):
    record = _equivalence_fixture_records()[record_index]
    serialized = record.to_json().encode("utf-8")
    assert len(serialized) < MODEL_CONTRACT_MAX_BYTES

    normal_path = tmp_path / "normal.json"
    normal_path.write_bytes(serialized)
    assert loader(normal_path) == record

    boundary_path = tmp_path / "boundary.json"
    boundary_payload = (
        b" " * (MODEL_CONTRACT_MAX_BYTES - len(serialized)) + serialized
    )
    assert len(boundary_payload) == MODEL_CONTRACT_MAX_BYTES
    boundary_path.write_bytes(boundary_payload)
    assert loader(boundary_path) == record


@pytest.mark.parametrize(
    ("loader", "artifact_type", "record_index"),
    [
        (load_model_contract, "model contract", 0),
        (load_semantic_patch, "semantic patch", 1),
    ],
)
def test_path_loaders_reject_oversize_whitespace_wrapped_valid_json(
    tmp_path,
    loader,
    artifact_type,
    record_index,
):
    serialized = _equivalence_fixture_records()[record_index].to_json().encode(
        "utf-8"
    )
    path = tmp_path / "oversize.json"
    payload = (
        b" " * (MODEL_CONTRACT_MAX_BYTES + 1 - len(serialized)) + serialized
    )
    assert len(payload) == MODEL_CONTRACT_MAX_BYTES + 1
    path.write_bytes(payload)

    with pytest.raises(ValueError) as exc_info:
        loader(path)

    message = str(exc_info.value)
    assert artifact_type in message
    assert str(path) in message
    assert "exceeds maximum size" in message
    assert str(MODEL_CONTRACT_MAX_BYTES) in message


@pytest.mark.parametrize(
    ("loader", "artifact_type", "record_index"),
    [
        (load_model_contract, "model contract", 0),
        (load_semantic_patch, "semantic patch", 1),
    ],
)
def test_path_loaders_bound_reads_when_fstat_underreports_size(
    tmp_path,
    monkeypatch,
    loader,
    artifact_type,
    record_index,
):
    serialized = _equivalence_fixture_records()[record_index].to_json().encode(
        "utf-8"
    )
    path = tmp_path / "grew-after-stat.json"
    payload = (
        b" " * (MODEL_CONTRACT_MAX_BYTES + 1 - len(serialized)) + serialized
    )
    path.write_bytes(payload)
    real_fstat = os.fstat

    def understated_fstat(fd):
        result = real_fstat(fd)
        fields = list(result)
        fields[stat.ST_SIZE] = MODEL_CONTRACT_MAX_BYTES
        return os.stat_result(fields)

    monkeypatch.setattr(os, "fstat", understated_fstat)

    with pytest.raises(ValueError) as exc_info:
        loader(path)

    message = str(exc_info.value)
    assert artifact_type in message
    assert str(path) in message
    assert "exceeds maximum size" in message


@pytest.mark.parametrize(
    ("loader", "record_index"),
    [
        (load_model_contract, 0),
        (load_semantic_patch, 1),
    ],
)
def test_path_loaders_fstat_and_read_the_opened_file_descriptor(
    tmp_path,
    monkeypatch,
    loader,
    record_index,
):
    record = _equivalence_fixture_records()[record_index]
    path = tmp_path / "same-fd.json"
    path.write_text(record.to_json(), encoding="utf-8")

    real_open = os.open
    real_fstat = os.fstat
    real_fdopen = os.fdopen
    opened: list[tuple[int, int]] = []
    inspected: list[int] = []
    read: list[int] = []

    def tracked_open(candidate, flags, *args, **kwargs):
        fd = real_open(candidate, flags, *args, **kwargs)
        opened.append((fd, flags))
        return fd

    def tracked_fstat(fd):
        inspected.append(fd)
        return real_fstat(fd)

    def tracked_fdopen(fd, *args, **kwargs):
        read.append(fd)
        return real_fdopen(fd, *args, **kwargs)

    monkeypatch.setattr(os, "open", tracked_open)
    monkeypatch.setattr(os, "fstat", tracked_fstat)
    monkeypatch.setattr(os, "fdopen", tracked_fdopen)

    assert loader(path) == record

    assert len(opened) == 1
    fd, flags = opened[0]
    assert inspected == [fd]
    assert read == [fd]
    assert flags & os.O_ACCMODE == os.O_RDONLY
    if hasattr(os, "O_NONBLOCK"):
        assert flags & os.O_NONBLOCK
    if hasattr(os, "O_CLOEXEC"):
        assert flags & os.O_CLOEXEC
    if hasattr(os, "O_BINARY"):
        assert flags & os.O_BINARY
    with pytest.raises(OSError):
        real_fstat(fd)


@pytest.mark.parametrize(
    ("loader", "record_index"),
    [
        (load_model_contract, 0),
        (load_semantic_patch, 1),
    ],
)
def test_path_loaders_work_without_nonblock_and_include_binary_flag(
    tmp_path,
    monkeypatch,
    loader,
    record_index,
):
    record = _equivalence_fixture_records()[record_index]
    path = tmp_path / "portable-flags.json"
    path.write_text(record.to_json(), encoding="utf-8")

    real_open = os.open
    binary_flag = 1 << 29
    observed_flags: list[int] = []

    def portable_open(candidate, flags, *args, **kwargs):
        observed_flags.append(flags)
        return real_open(candidate, flags & ~binary_flag, *args, **kwargs)

    monkeypatch.delattr(os, "O_NONBLOCK", raising=False)
    monkeypatch.setattr(os, "O_BINARY", binary_flag, raising=False)
    monkeypatch.setattr(os, "open", portable_open)

    assert loader(path) == record
    assert len(observed_flags) == 1
    assert observed_flags[0] & binary_flag


@pytest.mark.parametrize(
    ("loader", "artifact_type", "record_index"),
    [
        (load_model_contract, "model contract", 0),
        (load_semantic_patch, "semantic patch", 1),
    ],
)
def test_path_loaders_wrap_flag_composition_errors(
    tmp_path,
    monkeypatch,
    loader,
    artifact_type,
    record_index,
):
    path = tmp_path / "invalid-flags.json"
    path.write_text(
        _equivalence_fixture_records()[record_index].to_json(),
        encoding="utf-8",
    )
    monkeypatch.setattr(os, "O_CLOEXEC", object(), raising=False)

    with pytest.raises(ValueError) as exc_info:
        loader(path)

    message = str(exc_info.value)
    assert artifact_type in message
    assert str(path) in message
    assert "could not be opened" in message
    assert "TypeError" in message


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="mkfifo is unavailable")
@pytest.mark.parametrize(
    ("loader_name", "artifact_type", "record_index"),
    [
        ("load_model_contract", "model contract", 0),
        ("load_semantic_patch", "semantic patch", 1),
    ],
)
def test_path_loaders_reject_fifo_swapped_at_the_old_stat_open_seam(
    tmp_path,
    loader_name,
    artifact_type,
    record_index,
):
    path = tmp_path / "racing-artifact.json"
    path.write_text(
        _equivalence_fixture_records()[record_index].to_json(),
        encoding="utf-8",
    )
    script = (
        "import os\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"from abm_auto.mir._model_contract import {loader_name}\n"
        "target = Path(sys.argv[1])\n"
        "real_open = os.open\n"
        "real_stat = Path.stat\n"
        "swapped = False\n"
        "def swap_to_fifo():\n"
        "    global swapped\n"
        "    if not swapped:\n"
        "        target.unlink()\n"
        "        os.mkfifo(target)\n"
        "        swapped = True\n"
        "def racing_stat(self, *args, **kwargs):\n"
        "    result = real_stat(self, *args, **kwargs)\n"
        "    if self == target:\n"
        "        swap_to_fifo()\n"
        "    return result\n"
        "def racing_open(candidate, flags, *args, **kwargs):\n"
        "    if Path(candidate) == target:\n"
        "        swap_to_fifo()\n"
        "    return real_open(candidate, flags, *args, **kwargs)\n"
        "Path.stat = racing_stat\n"
        "os.open = racing_open\n"
        "try:\n"
        f"    {loader_name}(target)\n"
        "except ValueError as exc:\n"
        "    print(exc)\n"
        "else:\n"
        "    raise SystemExit('loader accepted swapped FIFO')\n"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert artifact_type in completed.stdout
    assert str(path) in completed.stdout
    assert "regular file" in completed.stdout


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="mkfifo is unavailable")
@pytest.mark.parametrize(
    ("loader_name", "artifact_type"),
    [
        ("load_model_contract", "model contract"),
        ("load_semantic_patch", "semantic patch"),
    ],
)
def test_path_loaders_reject_fifo_without_blocking(
    tmp_path,
    loader_name,
    artifact_type,
):
    path = tmp_path / "artifact.fifo"
    try:
        os.mkfifo(path)
    except OSError as exc:  # pragma: no cover - platform-specific skip
        pytest.skip(f"mkfifo is unsupported: {type(exc).__name__}")

    script = (
        "import sys\n"
        "from pathlib import Path\n"
        f"from abm_auto.mir._model_contract import {loader_name}\n"
        "try:\n"
        f"    {loader_name}(Path(sys.argv[1]))\n"
        "except ValueError as exc:\n"
        "    print(exc)\n"
        "else:\n"
        "    raise SystemExit('loader accepted FIFO')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(path)],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert artifact_type in completed.stdout
    assert str(path) in completed.stdout
    assert "regular file" in completed.stdout


@pytest.mark.parametrize(
    ("loader", "artifact_type"),
    [
        (load_model_contract, "model contract"),
        (load_semantic_patch, "semantic patch"),
    ],
)
def test_path_loaders_reject_invalid_path_types_deterministically(
    loader,
    artifact_type,
):
    with pytest.raises(ValueError) as exc_info:
        loader(object())

    message = str(exc_info.value)
    assert artifact_type in message
    assert "path" in message
    assert "object" in message
    assert "TypeError" in message


@pytest.mark.parametrize(
    ("loader", "artifact_type"),
    [
        (load_model_contract, "model contract"),
        (load_semantic_patch, "semantic patch"),
    ],
)
def test_path_loaders_wrap_embedded_nul_file_errors(loader, artifact_type):
    with pytest.raises(ValueError) as exc_info:
        loader("hostile\x00artifact.json")

    message = str(exc_info.value)
    assert artifact_type in message
    assert "hostile\\x00artifact.json" in message
    assert "ValueError" in message


@pytest.mark.parametrize(
    ("loader", "artifact_type"),
    [
        (load_model_contract, "model contract"),
        (load_semantic_patch, "semantic patch"),
    ],
)
@pytest.mark.parametrize(
    ("failure_kind", "expected_message"),
    [
        ("missing", "FileNotFoundError"),
        ("directory", "regular file"),
        ("non_utf8", "UnicodeDecodeError"),
    ],
)
def test_path_loaders_wrap_file_and_utf8_errors(
    tmp_path,
    loader,
    artifact_type,
    failure_kind,
    expected_message,
):
    path = tmp_path / "hostile.json"
    if failure_kind == "directory":
        path.mkdir()
    elif failure_kind == "non_utf8":
        path.write_bytes(b"\xff\xfe")

    with pytest.raises(ValueError) as exc_info:
        loader(path)

    message = str(exc_info.value)
    assert artifact_type in message
    assert str(path) in message
    assert expected_message in message


@pytest.mark.parametrize(
    ("loader", "artifact_type", "record_index"),
    [
        (load_model_contract, "model contract", 0),
        (load_semantic_patch, "semantic patch", 1),
    ],
)
@pytest.mark.parametrize(
    ("failure_kind", "expected_message"),
    [
        ("malformed", "JSON is invalid"),
        ("duplicate", "duplicate JSON object key"),
        ("nonfinite", "JSON number must be finite"),
        ("unknown", "unknown keys"),
    ],
)
def test_path_loaders_reuse_strict_json_validation(
    tmp_path,
    loader,
    artifact_type,
    record_index,
    failure_kind,
    expected_message,
):
    record = _equivalence_fixture_records()[record_index]
    if failure_kind == "malformed":
        text = "{"
    elif failure_kind == "duplicate":
        text = '{"schema":"duplicate","schema":"duplicate"}'
    elif failure_kind == "nonfinite":
        text = record.to_json()
        finite_token = '"threshold":0.4' if record_index == 0 else '"value":0.6'
        assert finite_token in text
        text = text.replace(finite_token, finite_token.split(":")[0] + ":NaN", 1)
    elif failure_kind == "unknown":
        payload = record.to_dict()
        payload["unknown"] = True
        text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    else:  # pragma: no cover - parametrization is closed above
        raise AssertionError(f"unknown failure kind {failure_kind}")

    path = tmp_path / f"{failure_kind}.json"
    path.write_bytes(text.encode("utf-8"))

    with pytest.raises(ValueError) as exc_info:
        loader(path)

    message = str(exc_info.value)
    assert artifact_type in message
    assert str(path) in message
    assert expected_message in message


@pytest.mark.parametrize(
    ("loader", "artifact_type"),
    [
        (load_model_contract, "model contract"),
        (load_semantic_patch, "semantic patch"),
    ],
)
def test_path_loaders_wrap_excessively_nested_json(
    tmp_path,
    loader,
    artifact_type,
):
    path = tmp_path / "deeply-nested.json"
    path.write_text("[" * 2_000 + "0" + "]" * 2_000, encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        loader(path)

    message = str(exc_info.value)
    assert artifact_type in message
    assert str(path) in message
    assert "RecursionError" in message


@pytest.mark.parametrize(
    "record_type",
    [NaturalLanguageModelContract, SemanticPatch],
)
def test_direct_from_json_wraps_deep_parser_recursion(record_type):
    text = "[" * 2_000 + "0" + "]" * 2_000

    with pytest.raises(ValueError) as exc_info:
        record_type.from_json(text)

    message = str(exc_info.value)
    assert record_type.__name__ in message
    assert "JSON" in message
    assert "RecursionError" in message


@pytest.mark.parametrize(
    "record_type",
    [NaturalLanguageModelContract, SemanticPatch],
)
def test_direct_from_json_wraps_deep_normalizer_recursion(
    monkeypatch,
    record_type,
):
    nested = 0
    for _ in range(2_000):
        nested = [nested]

    if record_type is NaturalLanguageModelContract:
        payload = _contract().to_dict()
        payload["mir"]["run"]["params"]["deep"] = nested
    else:
        payload = {
            "schema": SEMANTIC_PATCH_SCHEMA,
            "base_contract_revision": "a" * 64,
            "source": "conversation",
            "rationale": "Exercise deep normalization.",
            "operations": [
                {
                    "op": "add",
                    "path": "/mir/run/params/deep",
                    "value": nested,
                }
            ],
        }

    monkeypatch.setattr(
        model_contract,
        "_load_json",
        lambda text, *, context: payload,
    )

    with pytest.raises(ValueError) as exc_info:
        record_type.from_json("{}")

    message = str(exc_info.value)
    assert record_type.__name__ in message
    assert "JSON" in message
    assert "RecursionError" in message


_EXISTING_MIR_PUBLIC_EXPORTS = (
    "MIR",
    "MIRMetadata",
    "MIRSpace",
    "MIRProcess",
    "MIRRun",
    "MIRFidelity",
    "netlogo_model_to_mir",
    "netlogo_controls_to_mir",
)

_MODEL_CONTRACT_PUBLIC_EXPORTS = (
    "MODEL_CONTRACT_SCHEMA",
    "SEMANTIC_PATCH_SCHEMA",
    "MODEL_CONTRACT_MAX_BYTES",
    "AssumptionRecord",
    "UnresolvedDecision",
    "RoutingDecision",
    "ContractLock",
    "SemanticPatchOperation",
    "SemanticPatch",
    "RevisionRecord",
    "NaturalLanguageModelContract",
    "mir_digest",
    "patch_digest",
    "state_digest",
    "contract_state_digest",
    "contract_revision_digest",
    "revision_digest",
    "create_model_contract",
    "apply_semantic_patch",
    "promote_to_research",
    "research_readiness",
    "lock_contract",
    "branch_contract",
    "load_model_contract",
    "load_semantic_patch",
    "semantic_patch_equivalence_gate",
)


def test_mir_public_exports_are_explicit_complete_and_backward_compatible():
    expected = set(_EXISTING_MIR_PUBLIC_EXPORTS + _MODEL_CONTRACT_PUBLIC_EXPORTS)

    assert set(mir_api.__all__) == expected
    assert len(mir_api.__all__) == len(expected)
    assert all(not name.startswith("_") for name in mir_api.__all__)


@pytest.mark.parametrize("name", _MODEL_CONTRACT_PUBLIC_EXPORTS)
def test_model_contract_public_exports_preserve_object_identity(name):
    assert globals()[name] is getattr(mir_api, name)
    assert getattr(mir_api, name) is getattr(model_contract, name)


@pytest.mark.parametrize(
    "name",
    [
        "_decode_json_pointer",
        "_apply_patch_operation",
        "_apply_prepared_patch_operations",
        "_validate_lifecycle_state_transitions",
    ],
)
def test_mir_public_exports_do_not_leak_contract_internals(name):
    assert name not in mir_api.__all__
    assert not hasattr(mir_api, name)


def test_natural_language_model_contract_public_api_smoke(tmp_path):
    base = _contract()
    operation = SemanticPatchOperation(
        op="replace",
        path="/mir/processes/0/params/threshold",
        value=0.6,
    )
    conversation_patch = _semantic_patch(
        base,
        (operation,),
        source="conversation",
        rationale="Raise the threshold through conversation.",
    )
    panel_patch = _semantic_patch(
        base,
        (operation,),
        source="panel",
        rationale="Raise the threshold through the panel.",
    )

    equivalent, message = semantic_patch_equivalence_gate(
        base,
        conversation_patch,
        panel_patch,
    )
    patched = apply_semantic_patch(base, conversation_patch)
    promoted = promote_to_research(
        patched,
        rationale="Promote the public API smoke contract.",
        source="conversation",
    )
    readiness = research_readiness(promoted)
    locked = lock_contract(
        promoted,
        reason="Lock the public API smoke contract.",
        source="conversation",
    )
    branched = branch_contract(
        locked,
        branch_id="public-api-child",
        mode="quick",
        rationale="Create an editable public API smoke branch.",
        source="conversation",
    )

    assert equivalent is True
    assert message.startswith("PASS:")
    assert patched.mir.processes[0].params["threshold"] == 0.6
    assert readiness["ready"] is True
    assert branched.lock == ContractLock()
    assert mir_digest(patched.mir) == patched.mir_digest
    assert patch_digest(conversation_patch) == patch_digest(panel_patch)
    assert contract_state_digest(branched) == state_digest(branched)
    assert revision_digest is contract_revision_digest

    contract_path = tmp_path / "contract.json"
    patch_path = tmp_path / "patch.json"
    contract_path.write_text(branched.to_json(), encoding="utf-8")
    patch_path.write_text(conversation_patch.to_json(), encoding="utf-8")

    assert contract_path.stat().st_size < MODEL_CONTRACT_MAX_BYTES
    assert patch_path.stat().st_size < MODEL_CONTRACT_MAX_BYTES
    assert load_model_contract(contract_path) == branched
    assert load_semantic_patch(patch_path) == conversation_patch
