"""MIR — the Model Intermediate Representation (v0, open core).

The shared semantic contract between the open forward side (abm-auto / GIS) and
the closed inverse side (gaese). This package is the OPEN core only: it never
imports or interprets the closed extensions — those attach through the opaque
`MIR.extensions` field (the data-contract seam, strategic ADR-013).

See docs/superpowers/specs/2026-06-23-mir-v0-forward-design.md.
"""
from abm_auto.mir._schema import (
    MIR,
    MIRFidelity,
    MIRMetadata,
    MIRProcess,
    MIRRun,
    MIRSpace,
)
from abm_auto.mir._netlogo_adapter import (
    netlogo_controls_to_mir,
    netlogo_model_to_mir,
)
from abm_auto.mir._model_contract import (
    MODEL_CONTRACT_MAX_BYTES,
    MODEL_CONTRACT_SCHEMA,
    SEMANTIC_PATCH_SCHEMA,
    AssumptionRecord,
    ContractLock,
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
    load_model_contract,
    load_semantic_patch,
    lock_contract,
    mir_digest,
    patch_digest,
    promote_to_research,
    research_readiness,
    revision_digest,
    semantic_patch_equivalence_gate,
    state_digest,
)

__all__ = [
    "MIR",
    "MIRMetadata",
    "MIRSpace",
    "MIRProcess",
    "MIRRun",
    "MIRFidelity",
    "netlogo_model_to_mir",
    "netlogo_controls_to_mir",
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
]
