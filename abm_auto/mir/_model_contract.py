"""Deterministic natural-language model contract records around MIR v0.

This module owns the Phase 1 record, identity, constrained semantic-patch, and
explicit research lifecycle layers.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from abm_auto.mir._schema import MIR


MODEL_CONTRACT_SCHEMA = "abm-auto/natural-language-model-contract/v1"
SEMANTIC_PATCH_SCHEMA = "abm-auto/semantic-patch/v1"
MODEL_CONTRACT_MAX_BYTES = 1_048_576

_ASSUMPTION_SOURCES = frozenset(
    {"user", "imported", "inferred", "default", "derived"}
)
_MATERIALITIES = frozenset({"low", "material"})
_REQUESTED_MODES = frozenset({"auto", "quick", "research"})
_MODES = frozenset({"quick", "research"})
_REVISION_SOURCES = frozenset({"conversation", "panel", "import", "system"})
_PATCH_OPERATIONS = frozenset({"add", "replace", "remove"})
_REVISION_ACTIONS = frozenset({"create", "patch", "promote", "lock", "branch"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_ALLOWED_TARGET_ROOTS = (
    ("mir", "metadata", "name"),
    ("mir", "metadata", "description"),
    ("mir", "metadata", "domain"),
    ("mir", "entities"),
    ("mir", "state"),
    ("mir", "space"),
    ("mir", "relations"),
    ("mir", "processes"),
    ("mir", "layers"),
    ("mir", "metrics"),
    ("mir", "run", "seed"),
    ("mir", "run", "params"),
    ("assumptions",),
    ("unresolved_decisions",),
)

_FORBIDDEN_TARGET_ROOTS = (
    ("schema",),
    ("contract_id",),
    ("branch_id",),
    ("mode",),
    ("routing",),
    ("lock",),
    ("mir_digest",),
    ("contract_revision",),
    ("parent_contract_revision",),
    ("lineage",),
    ("mir", "metadata", "provenance"),
    ("mir", "fidelity"),
    ("mir", "trace"),
    ("mir", "extensions"),
)

_ARRAY_INDEX_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")

_MIR_KEYS = frozenset(MIR.__dataclass_fields__)
_MIR_NESTED_KEYS = {
    "metadata": frozenset({"name", "description", "domain", "provenance"}),
    "space": frozenset({"spatial_type", "crs", "data_path"}),
    "run": frozenset({"seed", "params"}),
    "fidelity": frozenset(
        {"capability", "required_tokens", "gate", "wrong_space_tokens"}
    ),
}
_MIR_PROCESS_KEYS = frozenset({"mechanism", "params"})


class _MissingValue:
    def __repr__(self) -> str:
        return "<absent>"

    def __copy__(self) -> "_MissingValue":
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> "_MissingValue":
        return self


_MISSING = _MissingValue()


def _normalize_json_value(
    value: Any,
    *,
    context: str,
    _seen: set[int] | None = None,
) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"{context} must contain only finite JSON numbers")
        return value

    seen = _seen if _seen is not None else set()
    if isinstance(value, tuple):
        raise ValueError(f"{context} must be a standard JSON value; tuple is invalid")

    if isinstance(value, list):
        container_id = id(value)
        if container_id in seen:
            raise ValueError(f"{context} must not contain cycles")
        seen.add(container_id)
        try:
            return [
                _normalize_json_value(
                    item,
                    context=f"{context}[{index}]",
                    _seen=seen,
                )
                for index, item in enumerate(value)
            ]
        finally:
            seen.remove(container_id)

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError(f"{context} object keys must be strings")
        container_id = id(value)
        if container_id in seen:
            raise ValueError(f"{context} must not contain cycles")
        seen.add(container_id)
        try:
            return {
                key: _normalize_json_value(
                    item,
                    context=f"{context}.{key}",
                    _seen=seen,
                )
                for key, item in value.items()
            }
        finally:
            seen.remove(container_id)

    raise ValueError(f"{context} must be a standard JSON value")


def _canonical_json(
    value: Any,
    *,
    context: str = "value",
) -> str:
    normalized = _normalize_json_value(
        value,
        context=context,
    )
    try:
        return json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be canonical-JSON serializable") from exc


def _digest(
    value: Any,
    *,
    context: str = "value",
) -> str:
    canonical = _canonical_json(
        value,
        context=context,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_json_number(value: str) -> None:
    raise ValueError(f"JSON number must be finite: {value}")


def _json_recursion_error(context: str) -> ValueError:
    return ValueError(f"{context} JSON is too deeply nested (RecursionError)")


def _load_json(text: str, *, context: str) -> Any:
    if not isinstance(text, str):
        raise ValueError(f"{context} JSON must be a string")
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json_number,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"{context} JSON is invalid: {exc.msg}") from exc
    except RecursionError as exc:
        raise _json_recursion_error(context) from exc


def _read_strict_utf8_file(
    path: str | os.PathLike[str],
    *,
    artifact_type: str,
) -> tuple[Path, str]:
    try:
        file_path = Path(path)
    except Exception as exc:
        raise ValueError(
            f"{artifact_type} path has invalid type {type(path).__name__} "
            f"({type(exc).__name__})"
        ) from exc

    fd: int | None = None
    try:
        try:
            flags = (
                os.O_RDONLY
                | getattr(os, "O_NONBLOCK", 0)
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_BINARY", 0)
            )
            fd = os.open(file_path, flags)
        except Exception as exc:
            raise ValueError(
                f"{artifact_type} file {str(file_path)!r} could not be opened "
                f"({type(exc).__name__})"
            ) from exc

        try:
            file_stat = os.fstat(fd)
        except (OSError, ValueError) as exc:
            raise ValueError(
                f"{artifact_type} file {str(file_path)!r} could not be inspected "
                f"({type(exc).__name__})"
            ) from exc
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(
                f"{artifact_type} file {str(file_path)!r} must be a regular file"
            )
        if file_stat.st_size > MODEL_CONTRACT_MAX_BYTES:
            raise ValueError(
                f"{artifact_type} file {str(file_path)!r} exceeds maximum size of "
                f"{MODEL_CONTRACT_MAX_BYTES} bytes"
            )

        try:
            handle = os.fdopen(fd, "rb")
            fd = None
            with handle:
                raw = handle.read(MODEL_CONTRACT_MAX_BYTES + 1)
        except (OSError, ValueError) as exc:
            raise ValueError(
                f"{artifact_type} file {str(file_path)!r} could not be read "
                f"({type(exc).__name__})"
            ) from exc
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
    if len(raw) > MODEL_CONTRACT_MAX_BYTES:
        raise ValueError(
            f"{artifact_type} file {str(file_path)!r} exceeds maximum size of "
            f"{MODEL_CONTRACT_MAX_BYTES} bytes"
        )

    try:
        return file_path, raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"{artifact_type} file {str(file_path)!r} is not strict UTF-8 "
            f"({type(exc).__name__})"
        ) from exc


def _as_object(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an object")
    return value


def _require_keys(
    value: Any,
    *,
    required: set[str] | frozenset[str],
    optional: set[str] | frozenset[str] = frozenset(),
    context: str,
) -> Mapping[str, Any]:
    obj = _as_object(value, context=context)
    if any(not isinstance(key, str) for key in obj):
        raise ValueError(f"{context} keys must be strings")
    keys = set(obj)
    missing = sorted(set(required) - keys)
    if missing:
        raise ValueError(f"{context} missing required keys: {', '.join(missing)}")
    unknown = sorted(keys - set(required) - set(optional))
    if unknown:
        raise ValueError(f"{context} contains unknown keys: {', '.join(unknown)}")
    return obj


def _field(context: str, name: str) -> str:
    return f"{context}.{name}" if context else name


def _validate_nonempty_string(value: Any, *, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _validate_string(value: Any, *, field_name: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")


def _validate_bool(value: Any, *, field_name: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a bool")


def _validate_choice(
    value: Any,
    choices: frozenset[str],
    *,
    field_name: str,
) -> None:
    if not isinstance(value, str) or value not in choices:
        rendered = ", ".join(sorted(choices))
        raise ValueError(f"{field_name} must be one of: {rendered}")


def _routing_is_overridden(*, requested_mode: str, resolved_mode: str) -> bool:
    return requested_mode != "auto" and requested_mode != resolved_mode


def _validate_digest(value: Any, *, field_name: str, allow_empty: bool = False) -> None:
    if allow_empty and value == "":
        return
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(
            f"{field_name} must be a lowercase 64-character SHA-256 digest"
        )


def _decode_json_pointer(path: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(path, str):
        raise ValueError(f"{field_name} must be an RFC 6901 JSON Pointer")
    if path == "":
        return ()
    if not path.startswith("/"):
        raise ValueError(f"{field_name} must be an RFC 6901 JSON Pointer")

    decoded: list[str] = []
    for raw_token in path[1:].split("/"):
        index = 0
        while index < len(raw_token):
            if raw_token[index] == "~":
                if index + 1 >= len(raw_token) or raw_token[index + 1] not in "01":
                    raise ValueError(f"{field_name} must be an RFC 6901 JSON Pointer")
                index += 2
            else:
                index += 1
        decoded.append(raw_token.replace("~1", "/").replace("~0", "~"))
    return tuple(decoded)


def _validate_target_path(path: Any, *, field_name: str) -> None:
    tokens = _decode_json_pointer(path, field_name=field_name)
    if not any(tokens[: len(root)] == root for root in _ALLOWED_TARGET_ROOTS):
        raise ValueError(f"{field_name} must point into an allowed model path")


def _normalize_tuple(value: Any) -> Any:
    return tuple(value) if isinstance(value, list) else value


class _JSONRecord:
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_json(cls, text: str):
        context = cls.__name__
        try:
            return cls.from_dict(_load_json(text, context=context))
        except RecursionError as exc:
            raise _json_recursion_error(context) from exc


@dataclass(frozen=True)
class AssumptionRecord(_JSONRecord):
    assumption_id: str
    statement: str
    target_path: str
    source: str
    materiality: str
    confirmed: bool

    def validate(self, *, _context: str = "") -> None:
        _validate_nonempty_string(
            self.assumption_id,
            field_name=_field(_context, "assumption_id"),
        )
        _validate_nonempty_string(
            self.statement,
            field_name=_field(_context, "statement"),
        )
        _validate_target_path(
            self.target_path,
            field_name=_field(_context, "target_path"),
        )
        _validate_choice(
            self.source,
            _ASSUMPTION_SOURCES,
            field_name=_field(_context, "source"),
        )
        _validate_choice(
            self.materiality,
            _MATERIALITIES,
            field_name=_field(_context, "materiality"),
        )
        _validate_bool(
            self.confirmed,
            field_name=_field(_context, "confirmed"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "statement": self.statement,
            "target_path": self.target_path,
            "source": self.source,
            "materiality": self.materiality,
            "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        _context: str = "AssumptionRecord",
    ) -> "AssumptionRecord":
        obj = _require_keys(
            value,
            required=frozenset(
                {
                    "assumption_id",
                    "statement",
                    "target_path",
                    "source",
                    "materiality",
                    "confirmed",
                }
            ),
            context=_context,
        )
        record = cls(
            assumption_id=obj["assumption_id"],
            statement=obj["statement"],
            target_path=obj["target_path"],
            source=obj["source"],
            materiality=obj["materiality"],
            confirmed=obj["confirmed"],
        )
        record.validate(_context=_context)
        return record


@dataclass(frozen=True)
class UnresolvedDecision(_JSONRecord):
    decision_id: str
    question: str
    target_path: str
    materiality: str
    status: str
    resolution: str = ""

    def validate(self, *, _context: str = "") -> None:
        _validate_nonempty_string(
            self.decision_id,
            field_name=_field(_context, "decision_id"),
        )
        _validate_nonempty_string(
            self.question,
            field_name=_field(_context, "question"),
        )
        _validate_target_path(
            self.target_path,
            field_name=_field(_context, "target_path"),
        )
        _validate_choice(
            self.materiality,
            _MATERIALITIES,
            field_name=_field(_context, "materiality"),
        )
        _validate_choice(
            self.status,
            frozenset({"open", "resolved"}),
            field_name=_field(_context, "status"),
        )
        _validate_string(
            self.resolution,
            field_name=_field(_context, "resolution"),
        )
        if self.status == "resolved" and not self.resolution.strip():
            raise ValueError(
                f"{_field(_context, 'resolution')} must be non-empty when status is resolved"
            )
        if self.status == "open" and self.resolution != "":
            raise ValueError(
                f"{_field(_context, 'resolution')} must be empty when status is open"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "question": self.question,
            "target_path": self.target_path,
            "materiality": self.materiality,
            "status": self.status,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        _context: str = "UnresolvedDecision",
    ) -> "UnresolvedDecision":
        obj = _require_keys(
            value,
            required=frozenset(
                {
                    "decision_id",
                    "question",
                    "target_path",
                    "materiality",
                    "status",
                }
            ),
            optional=frozenset({"resolution"}),
            context=_context,
        )
        if obj["status"] == "resolved" and "resolution" not in obj:
            raise ValueError(
                f"{_field(_context, 'resolution')} is required when status is resolved"
            )
        record = cls(
            decision_id=obj["decision_id"],
            question=obj["question"],
            target_path=obj["target_path"],
            materiality=obj["materiality"],
            status=obj["status"],
            resolution=obj.get("resolution", ""),
        )
        record.validate(_context=_context)
        return record


@dataclass(frozen=True)
class RoutingDecision(_JSONRecord):
    requested_mode: str
    resolved_mode: str
    rationale: tuple[str, ...]
    overridden: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "rationale", _normalize_tuple(self.rationale))

    def validate(self, *, _context: str = "") -> None:
        _validate_choice(
            self.requested_mode,
            _REQUESTED_MODES,
            field_name=_field(_context, "requested_mode"),
        )
        _validate_choice(
            self.resolved_mode,
            _MODES,
            field_name=_field(_context, "resolved_mode"),
        )
        rationale_field = _field(_context, "rationale")
        if not isinstance(self.rationale, tuple) or not self.rationale:
            raise ValueError(f"{rationale_field} must be a non-empty list of strings")
        for index, item in enumerate(self.rationale):
            if not isinstance(item, str):
                raise ValueError(f"{rationale_field}[{index}] must be a string")
        _validate_bool(
            self.overridden,
            field_name=_field(_context, "overridden"),
        )
        expected_overridden = _routing_is_overridden(
            requested_mode=self.requested_mode,
            resolved_mode=self.resolved_mode,
        )
        if self.overridden != expected_overridden:
            raise ValueError(
                f"{_field(_context, 'overridden')} must equal the canonical value "
                "for requested_mode and resolved_mode"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_mode": self.requested_mode,
            "resolved_mode": self.resolved_mode,
            "rationale": list(self.rationale)
            if isinstance(self.rationale, tuple)
            else self.rationale,
            "overridden": self.overridden,
        }

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        _context: str = "RoutingDecision",
    ) -> "RoutingDecision":
        obj = _require_keys(
            value,
            required=frozenset(
                {"requested_mode", "resolved_mode", "rationale", "overridden"}
            ),
            context=_context,
        )
        rationale = obj["rationale"]
        if not isinstance(rationale, (list, tuple)):
            raise ValueError(
                f"{_field(_context, 'rationale')} must be a non-empty list of strings"
            )
        record = cls(
            requested_mode=obj["requested_mode"],
            resolved_mode=obj["resolved_mode"],
            rationale=tuple(rationale),
            overridden=obj["overridden"],
        )
        record.validate(_context=_context)
        return record


@dataclass(frozen=True)
class ContractLock(_JSONRecord):
    status: str = "unlocked"
    locked_mir_digest: str = ""
    locked_contract_revision: str = ""
    reason: str = ""

    def validate(self, *, _context: str = "") -> None:
        _validate_choice(
            self.status,
            frozenset({"unlocked", "locked"}),
            field_name=_field(_context, "status"),
        )
        if self.status == "unlocked":
            if self.locked_mir_digest != "":
                raise ValueError(
                    f"{_field(_context, 'locked_mir_digest')} must be empty when unlocked"
                )
            if self.locked_contract_revision != "":
                raise ValueError(
                    f"{_field(_context, 'locked_contract_revision')} must be empty when unlocked"
                )
            _validate_string(
                self.reason,
                field_name=_field(_context, "reason"),
            )
            return

        _validate_digest(
            self.locked_mir_digest,
            field_name=_field(_context, "locked_mir_digest"),
        )
        _validate_digest(
            self.locked_contract_revision,
            field_name=_field(_context, "locked_contract_revision"),
        )
        _validate_nonempty_string(
            self.reason,
            field_name=_field(_context, "reason"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "locked_mir_digest": self.locked_mir_digest,
            "locked_contract_revision": self.locked_contract_revision,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        _context: str = "ContractLock",
    ) -> "ContractLock":
        obj = _require_keys(
            value,
            required=frozenset(
                {
                    "status",
                    "locked_mir_digest",
                    "locked_contract_revision",
                    "reason",
                }
            ),
            context=_context,
        )
        record = cls(
            status=obj["status"],
            locked_mir_digest=obj["locked_mir_digest"],
            locked_contract_revision=obj["locked_contract_revision"],
            reason=obj["reason"],
        )
        record.validate(_context=_context)
        return record


@dataclass(frozen=True)
class SemanticPatchOperation(_JSONRecord):
    op: str
    path: str
    value: Any = _MISSING

    def __post_init__(self) -> None:
        raw_value = object.__getattribute__(self, "value")
        if raw_value is not _MISSING:
            object.__setattr__(self, "value", copy.deepcopy(raw_value))

    def __getattribute__(self, name: str) -> Any:
        value = object.__getattribute__(self, name)
        if name == "value" and value is not _MISSING:
            return copy.deepcopy(value)
        return value

    def validate(self, *, _context: str = "") -> None:
        _validate_choice(
            self.op,
            _PATCH_OPERATIONS,
            field_name=_field(_context, "op"),
        )
        _decode_json_pointer(
            self.path,
            field_name=_field(_context, "path"),
        )
        if self.op in {"add", "replace"} and self.value is _MISSING:
            raise ValueError(
                f"{_field(_context, 'value')} is required for {self.op} operations"
            )
        if self.op == "remove" and self.value is not _MISSING:
            raise ValueError(
                f"{_field(_context, 'value')} must be absent for remove operations"
            )
        if self.value is not _MISSING:
            try:
                _canonical_json(
                    self.value,
                    context=_field(_context, "value"),
                )
            except ValueError as exc:
                raise ValueError(
                    f"{_field(_context, 'value')} must be canonical-JSON serializable: "
                    f"{exc}"
                ) from exc

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"op": self.op, "path": self.path}
        if self.value is not _MISSING:
            result["value"] = copy.deepcopy(self.value)
        return result

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        _context: str = "SemanticPatchOperation",
    ) -> "SemanticPatchOperation":
        obj = _require_keys(
            value,
            required=frozenset({"op", "path"}),
            optional=frozenset({"value"}),
            context=_context,
        )
        record = cls(
            op=obj["op"],
            path=obj["path"],
            value=copy.deepcopy(obj["value"]) if "value" in obj else _MISSING,
        )
        record.validate(_context=_context)
        return record


@dataclass(frozen=True)
class SemanticPatch(_JSONRecord):
    schema: str
    base_contract_revision: str
    source: str
    rationale: str
    operations: tuple[SemanticPatchOperation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "operations", _normalize_tuple(self.operations))

    @property
    def patch_digest(self) -> str:
        return patch_digest(self)

    def validate(self, *, _context: str = "") -> None:
        schema_field = _field(_context, "schema")
        if self.schema != SEMANTIC_PATCH_SCHEMA:
            raise ValueError(f"{schema_field} must be {SEMANTIC_PATCH_SCHEMA}")
        _validate_digest(
            self.base_contract_revision,
            field_name=_field(_context, "base_contract_revision"),
        )
        _validate_choice(
            self.source,
            _REVISION_SOURCES,
            field_name=_field(_context, "source"),
        )
        _validate_string(
            self.rationale,
            field_name=_field(_context, "rationale"),
        )
        operations_field = _field(_context, "operations")
        if not isinstance(self.operations, tuple) or not self.operations:
            raise ValueError(f"{operations_field} must be a non-empty list")
        for index, operation in enumerate(self.operations):
            item_context = f"{operations_field}[{index}]"
            if not isinstance(operation, SemanticPatchOperation):
                raise ValueError(
                    f"{item_context} must be a SemanticPatchOperation"
                )
            operation.validate(_context=item_context)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "base_contract_revision": self.base_contract_revision,
            "source": self.source,
            "rationale": self.rationale,
            "operations": [operation.to_dict() for operation in self.operations]
            if isinstance(self.operations, tuple)
            else self.operations,
        }

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        _context: str = "SemanticPatch",
    ) -> "SemanticPatch":
        obj = _require_keys(
            value,
            required=frozenset(
                {"schema", "base_contract_revision", "source", "rationale", "operations"}
            ),
            context=_context,
        )
        raw_operations = obj["operations"]
        if not isinstance(raw_operations, (list, tuple)):
            raise ValueError(f"{_field(_context, 'operations')} must be a non-empty list")
        operations = tuple(
            SemanticPatchOperation.from_dict(
                operation,
                _context=f"{_field(_context, 'operations')}[{index}]",
            )
            for index, operation in enumerate(raw_operations)
        )
        record = cls(
            schema=obj["schema"],
            base_contract_revision=obj["base_contract_revision"],
            source=obj["source"],
            rationale=obj["rationale"],
            operations=operations,
        )
        record.validate(_context=_context)
        return record


@dataclass(frozen=True)
class RevisionRecord(_JSONRecord):
    contract_revision: str
    parent_contract_revision: str
    branch_id: str
    action: str
    source: str
    rationale: str
    patch_digest: str | None
    mir_digest: str
    state_digest: str

    def validate(self, *, _context: str = "") -> None:
        _validate_digest(
            self.contract_revision,
            field_name=_field(_context, "contract_revision"),
        )
        _validate_digest(
            self.parent_contract_revision,
            field_name=_field(_context, "parent_contract_revision"),
            allow_empty=True,
        )
        _validate_nonempty_string(
            self.branch_id,
            field_name=_field(_context, "branch_id"),
        )
        _validate_choice(
            self.action,
            _REVISION_ACTIONS,
            field_name=_field(_context, "action"),
        )
        _validate_choice(
            self.source,
            _REVISION_SOURCES,
            field_name=_field(_context, "source"),
        )
        _validate_string(
            self.rationale,
            field_name=_field(_context, "rationale"),
        )
        patch_field = _field(_context, "patch_digest")
        if self.action == "patch":
            _validate_digest(self.patch_digest, field_name=patch_field)
        elif self.patch_digest is not None:
            raise ValueError(f"{patch_field} is only valid for patch actions")
        _validate_digest(
            self.mir_digest,
            field_name=_field(_context, "mir_digest"),
        )
        _validate_digest(
            self.state_digest,
            field_name=_field(_context, "state_digest"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "contract_revision": self.contract_revision,
            "parent_contract_revision": self.parent_contract_revision,
            "branch_id": self.branch_id,
            "action": self.action,
            "source": self.source,
            "rationale": self.rationale,
            "mir_digest": self.mir_digest,
            "state_digest": self.state_digest,
        }
        if self.patch_digest is not None:
            result["patch_digest"] = self.patch_digest
        return result

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        _context: str = "RevisionRecord",
    ) -> "RevisionRecord":
        obj = _require_keys(
            value,
            required=frozenset(
                {
                    "contract_revision",
                    "parent_contract_revision",
                    "branch_id",
                    "action",
                    "source",
                    "rationale",
                    "mir_digest",
                    "state_digest",
                }
            ),
            optional=frozenset({"patch_digest"}),
            context=_context,
        )
        if obj["action"] != "patch" and "patch_digest" in obj:
            raise ValueError(
                f"{_field(_context, 'patch_digest')} is only valid for patch actions"
            )
        record = cls(
            contract_revision=obj["contract_revision"],
            parent_contract_revision=obj["parent_contract_revision"],
            branch_id=obj["branch_id"],
            action=obj["action"],
            source=obj["source"],
            rationale=obj["rationale"],
            patch_digest=obj.get("patch_digest"),
            mir_digest=obj["mir_digest"],
            state_digest=obj["state_digest"],
        )
        record.validate(_context=_context)
        return record


def _material_research_blocker_ids(
    assumptions: Sequence[AssumptionRecord],
    unresolved_decisions: Sequence[UnresolvedDecision],
) -> tuple[list[str], list[str]]:
    unconfirmed_assumptions = sorted(
        assumption.assumption_id
        for assumption in assumptions
        if assumption.materiality == "material" and not assumption.confirmed
    )
    open_decisions = sorted(
        decision.decision_id
        for decision in unresolved_decisions
        if decision.materiality == "material" and decision.status == "open"
    )
    return unconfirmed_assumptions, open_decisions


def _is_state_changing_patch(
    previous: RevisionRecord,
    revision: RevisionRecord,
) -> bool:
    return (
        revision.action == "patch"
        and revision.state_digest != previous.state_digest
    )


@dataclass(frozen=True)
class NaturalLanguageModelContract(_JSONRecord):
    schema: str
    contract_id: str
    branch_id: str
    mode: str
    mir: MIR
    assumptions: tuple[AssumptionRecord, ...]
    unresolved_decisions: tuple[UnresolvedDecision, ...]
    routing: RoutingDecision
    lock: ContractLock
    mir_digest: str
    contract_revision: str
    parent_contract_revision: str
    lineage: tuple[RevisionRecord, ...]

    def __post_init__(self) -> None:
        raw_mir = object.__getattribute__(self, "mir")
        object.__setattr__(self, "mir", copy.deepcopy(raw_mir))
        object.__setattr__(self, "assumptions", _normalize_tuple(self.assumptions))
        object.__setattr__(
            self,
            "unresolved_decisions",
            _normalize_tuple(self.unresolved_decisions),
        )
        object.__setattr__(self, "lineage", _normalize_tuple(self.lineage))

    def __getattribute__(self, name: str) -> Any:
        value = object.__getattribute__(self, name)
        if name == "mir":
            return copy.deepcopy(value)
        return value

    def to_json(self) -> str:
        value = self.to_dict()
        value["mir"] = _canonical_mir_dict(
            value["mir"],
            accept_fidelity_lists=False,
        )
        return _canonical_json(value, context="contract")

    def validate(self) -> None:
        if self.schema != MODEL_CONTRACT_SCHEMA:
            raise ValueError(f"schema must be {MODEL_CONTRACT_SCHEMA}")
        _validate_nonempty_string(self.contract_id, field_name="contract_id")
        _validate_nonempty_string(self.branch_id, field_name="branch_id")
        _validate_choice(self.mode, _MODES, field_name="mode")

        _validate_mir(self.mir)

        _validate_record_sequence(
            self.assumptions,
            record_type=AssumptionRecord,
            field_name="assumptions",
        )
        for index, assumption in enumerate(self.assumptions):
            assumption.validate(_context=f"assumptions[{index}]")
        _validate_unique_record_ids(
            self.assumptions,
            id_field="assumption_id",
            field_name="assumptions",
        )

        _validate_record_sequence(
            self.unresolved_decisions,
            record_type=UnresolvedDecision,
            field_name="unresolved_decisions",
        )
        for index, decision in enumerate(self.unresolved_decisions):
            decision.validate(_context=f"unresolved_decisions[{index}]")
        _validate_unique_record_ids(
            self.unresolved_decisions,
            id_field="decision_id",
            field_name="unresolved_decisions",
        )

        if not isinstance(self.routing, RoutingDecision):
            raise ValueError("routing must be a RoutingDecision")
        self.routing.validate(_context="routing")
        if self.routing.resolved_mode != self.mode:
            raise ValueError("routing.resolved_mode must equal mode")

        if not isinstance(self.lock, ContractLock):
            raise ValueError("lock must be a ContractLock")
        self.lock.validate(_context="lock")

        expected_mir_digest = mir_digest(self.mir)
        _validate_digest(self.mir_digest, field_name="mir_digest")
        if self.mir_digest != expected_mir_digest:
            raise ValueError("mir_digest does not match canonical mir")

        _validate_digest(self.contract_revision, field_name="contract_revision")
        _validate_digest(
            self.parent_contract_revision,
            field_name="parent_contract_revision",
            allow_empty=True,
        )

        _validate_record_sequence(
            self.lineage,
            record_type=RevisionRecord,
            field_name="lineage",
            require_nonempty=True,
        )
        for index, revision in enumerate(self.lineage):
            revision.validate(_context=f"lineage[{index}]")

        root = self.lineage[0]
        if root.action != "create":
            raise ValueError("lineage[0].action must be create")
        if root.parent_contract_revision != "":
            raise ValueError(
                "lineage[0].parent_contract_revision must be empty for create root"
            )

        latest = self.lineage[-1]
        expected_state_digest = state_digest(self)
        if latest.state_digest != expected_state_digest:
            raise ValueError(
                "lineage[-1].state_digest does not match canonical contract state"
            )
        if latest.mir_digest != self.mir_digest:
            raise ValueError("lineage[-1].mir_digest does not match mir_digest")
        if latest.branch_id != self.branch_id:
            raise ValueError("lineage[-1].branch_id does not match branch_id")
        if self.contract_revision != latest.contract_revision:
            raise ValueError(
                "contract_revision does not match the latest lineage revision"
            )
        if self.parent_contract_revision != latest.parent_contract_revision:
            raise ValueError(
                "parent_contract_revision does not match the latest lineage revision"
            )

        seen_branch_ids: set[str] = set()
        for index, revision in enumerate(self.lineage):
            if index:
                previous = self.lineage[index - 1]
                if (
                    revision.parent_contract_revision
                    != previous.contract_revision
                ):
                    raise ValueError(
                        f"lineage[{index}].parent_contract_revision does not match "
                        "the previous revision"
                    )
                if revision.action == "create":
                    raise ValueError(
                        f"lineage[{index}].action create is valid only at the root"
                    )
                if revision.action == "branch":
                    if revision.branch_id == previous.branch_id:
                        raise ValueError(
                            f"lineage[{index}].branch_id must change for a branch action"
                        )
                    if revision.branch_id in seen_branch_ids:
                        raise ValueError(
                            f"lineage[{index}].branch_id {revision.branch_id!r} has "
                            "already appeared earlier and cannot be reused by a "
                            "branch action"
                        )
                elif revision.branch_id != previous.branch_id:
                    raise ValueError(
                        f"lineage[{index}].branch_id may change only for a branch action"
                    )
                if revision.action == "branch":
                    if previous.action != "lock":
                        raise ValueError(
                            f"lineage[{index}] branch action must directly follow "
                            "a lock action"
                        )
                    if revision.mir_digest != previous.mir_digest:
                        raise ValueError(
                            f"lineage[{index}] branch action mir_digest must match "
                            "the source lock revision"
                        )
                elif previous.action == "lock":
                    raise ValueError(
                        f"lineage[{index}] revision after a lock action must be branch"
                    )
                if revision.action == "promote":
                    if previous.action == "promote":
                        raise ValueError(
                            f"lineage[{index}] promote action cannot directly follow "
                            "another promote action"
                        )
                    if revision.mir_digest != previous.mir_digest:
                        raise ValueError(
                            f"lineage[{index}] promote action mir_digest must match "
                            "the previous revision"
                        )
                if (
                    revision.action == "lock"
                    and revision.mir_digest != previous.mir_digest
                ):
                    raise ValueError(
                        f"lineage[{index}] lock action mir_digest must match "
                        "the previous revision"
                    )
            expected_revision = contract_revision_digest(
                contract_id=self.contract_id,
                parent_contract_revision=revision.parent_contract_revision,
                branch_id=revision.branch_id,
                action=revision.action,
                source=revision.source,
                rationale=revision.rationale,
                patch_digest=revision.patch_digest,
                state_digest=revision.state_digest,
                mir_digest=revision.mir_digest,
            )
            if revision.contract_revision != expected_revision:
                raise ValueError(
                    f"lineage[{index}].contract_revision does not match its revision event"
                )
            seen_branch_ids.add(revision.branch_id)

        confirmed_external_assumption_ids = sorted(
            assumption.assumption_id
            for assumption in self.assumptions
            if assumption.source in {"inferred", "default"}
            and assumption.confirmed
        )
        has_state_changing_patch = any(
            _is_state_changing_patch(previous, revision)
            for previous, revision in zip(self.lineage, self.lineage[1:])
        )
        if confirmed_external_assumption_ids and not has_state_changing_patch:
            raise ValueError(
                "confirmed inferred/default assumptions require at least one "
                "state-changing patch revision in lineage as confirmation audit "
                "evidence: "
                + ", ".join(confirmed_external_assumption_ids)
                + "; this proves only that contract state changed during a patch, "
                "not which fields changed or that the patch confirmed those "
                "assumptions, because RevisionRecord stores only state_digest and "
                "patch_digest"
            )

        if latest.action == "promote" and self.mode != "research":
            raise ValueError("a promote action must resolve the contract to research mode")
        if latest.action == "lock" and self.lock.status != "locked":
            raise ValueError("a lock action requires lock.status to be locked")
        if self.lock.status == "locked":
            if self.mode != "research":
                raise ValueError("a locked contract must be in research mode")
            if latest.action != "lock":
                raise ValueError("a locked contract must end with a lock action")
            unconfirmed_assumptions, open_decisions = (
                _material_research_blocker_ids(
                    self.assumptions,
                    self.unresolved_decisions,
                )
            )
            if unconfirmed_assumptions:
                raise ValueError(
                    "locked contract has unconfirmed material assumptions: "
                    + ", ".join(unconfirmed_assumptions)
                )
            if open_decisions:
                raise ValueError(
                    "locked contract has open material decisions: "
                    + ", ".join(open_decisions)
                )
            if self.lock.locked_mir_digest != self.mir_digest:
                raise ValueError("lock.locked_mir_digest does not match mir_digest")
            if self.lock.locked_contract_revision != self.parent_contract_revision:
                raise ValueError(
                    "lock.locked_contract_revision must equal the pre-lock revision"
                )

        _validate_lifecycle_state_transitions(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "contract_id": self.contract_id,
            "branch_id": self.branch_id,
            "mode": self.mode,
            "mir": _mir_to_dict(self.mir),
            "assumptions": [record.to_dict() for record in self.assumptions]
            if isinstance(self.assumptions, tuple)
            else self.assumptions,
            "unresolved_decisions": [
                record.to_dict() for record in self.unresolved_decisions
            ]
            if isinstance(self.unresolved_decisions, tuple)
            else self.unresolved_decisions,
            "routing": self.routing.to_dict()
            if isinstance(self.routing, RoutingDecision)
            else self.routing,
            "lock": self.lock.to_dict()
            if isinstance(self.lock, ContractLock)
            else self.lock,
            "mir_digest": self.mir_digest,
            "contract_revision": self.contract_revision,
            "parent_contract_revision": self.parent_contract_revision,
            "lineage": [record.to_dict() for record in self.lineage]
            if isinstance(self.lineage, tuple)
            else self.lineage,
        }

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        _context: str = "contract",
    ) -> "NaturalLanguageModelContract":
        obj = _require_keys(
            value,
            required=frozenset(
                {
                    "schema",
                    "contract_id",
                    "branch_id",
                    "mode",
                    "mir",
                    "assumptions",
                    "unresolved_decisions",
                    "routing",
                    "lock",
                    "mir_digest",
                    "contract_revision",
                    "parent_contract_revision",
                    "lineage",
                }
            ),
            context=_context,
        )
        mir = _strict_mir_from_dict(obj["mir"])
        assumptions = _records_from_list(
            obj["assumptions"],
            record_type=AssumptionRecord,
            field_name="assumptions",
        )
        unresolved_decisions = _records_from_list(
            obj["unresolved_decisions"],
            record_type=UnresolvedDecision,
            field_name="unresolved_decisions",
        )
        routing = RoutingDecision.from_dict(obj["routing"], _context="routing")
        lock = ContractLock.from_dict(obj["lock"], _context="lock")
        lineage = _records_from_list(
            obj["lineage"],
            record_type=RevisionRecord,
            field_name="lineage",
        )
        contract = cls(
            schema=obj["schema"],
            contract_id=obj["contract_id"],
            branch_id=obj["branch_id"],
            mode=obj["mode"],
            mir=mir,
            assumptions=assumptions,
            unresolved_decisions=unresolved_decisions,
            routing=routing,
            lock=lock,
            mir_digest=obj["mir_digest"],
            contract_revision=obj["contract_revision"],
            parent_contract_revision=obj["parent_contract_revision"],
            lineage=lineage,
        )
        contract.validate()
        return contract


def load_model_contract(
    path: str | os.PathLike[str],
) -> NaturalLanguageModelContract:
    """Load one strictly validated UTF-8 model-contract JSON file."""
    file_path, text = _read_strict_utf8_file(
        path,
        artifact_type="model contract",
    )
    try:
        return NaturalLanguageModelContract.from_json(text)
    except (RecursionError, ValueError) as exc:
        detail = f": {exc}" if isinstance(exc, ValueError) else ""
        raise ValueError(
            f"model contract file {str(file_path)!r} contains invalid JSON data "
            f"({type(exc).__name__}){detail}"
        ) from exc


def load_semantic_patch(path: str | os.PathLike[str]) -> SemanticPatch:
    """Load one strictly validated UTF-8 semantic-patch JSON file."""
    file_path, text = _read_strict_utf8_file(
        path,
        artifact_type="semantic patch",
    )
    try:
        return SemanticPatch.from_json(text)
    except (RecursionError, ValueError) as exc:
        detail = f": {exc}" if isinstance(exc, ValueError) else ""
        raise ValueError(
            f"semantic patch file {str(file_path)!r} contains invalid JSON data "
            f"({type(exc).__name__}){detail}"
        ) from exc


def _validate_record_sequence(
    value: Any,
    *,
    record_type: type,
    field_name: str,
    require_nonempty: bool = False,
) -> None:
    if not isinstance(value, tuple):
        raise ValueError(f"{field_name} must be a list of {record_type.__name__} records")
    if require_nonempty and not value:
        raise ValueError(f"{field_name} must be a non-empty list")
    for index, record in enumerate(value):
        if not isinstance(record, record_type):
            raise ValueError(
                f"{field_name}[{index}] must be a {record_type.__name__}"
            )


def _validate_unique_record_ids(
    records: Sequence[Any],
    *,
    id_field: str,
    field_name: str,
) -> None:
    seen: dict[str, int] = {}
    for index, record in enumerate(records):
        record_id = getattr(record, id_field)
        if record_id in seen:
            raise ValueError(
                f"{field_name} contains duplicate {id_field} {record_id!r} "
                f"at indexes {seen[record_id]} and {index}"
            )
        seen[record_id] = index


def _records_from_list(
    value: Any,
    *,
    record_type: type,
    field_name: str,
) -> tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list")
    return tuple(
        record_type.from_dict(item, _context=f"{field_name}[{index}]")
        for index, item in enumerate(value)
    )


def _validate_mir(mir: Any) -> None:
    if not isinstance(mir, MIR):
        raise ValueError("mir must be an MIR")

    record_list_fields = ("entities", "state", "relations", "layers", "metrics")
    for field_name in record_list_fields:
        records = getattr(mir, field_name)
        if not isinstance(records, list):
            raise ValueError(f"mir.{field_name} must be a list")
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(f"mir.{field_name}[{index}] must be a dict")
    if not isinstance(mir.processes, list):
        raise ValueError("mir.processes must be a list")
    if not isinstance(mir.trace, dict):
        raise ValueError("mir.trace must be a dict")
    if not isinstance(mir.extensions, dict):
        raise ValueError("mir.extensions must be a dict")

    try:
        mir.validate()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"mir is invalid: {exc}") from exc

    for field_name in ("name", "description", "domain"):
        _validate_string(
            getattr(mir.metadata, field_name),
            field_name=f"mir.metadata.{field_name}",
        )
    if not isinstance(mir.metadata.provenance, dict):
        raise ValueError("mir.metadata.provenance must be a dict")

    for field_name in ("spatial_type", "crs", "data_path"):
        _validate_string(
            getattr(mir.space, field_name),
            field_name=f"mir.space.{field_name}",
        )

    if type(mir.run.seed) is not int:
        raise ValueError("mir.run.seed must be an int and not a bool")
    if not isinstance(mir.run.params, dict):
        raise ValueError("mir.run.params must be a dict")

    for field_name in ("capability", "gate"):
        _validate_string(
            getattr(mir.fidelity, field_name),
            field_name=f"mir.fidelity.{field_name}",
        )
    for field_name in ("required_tokens", "wrong_space_tokens"):
        value = getattr(mir.fidelity, field_name)
        if not isinstance(value, tuple):
            raise ValueError(f"mir.fidelity.{field_name} must be a tuple")
        if not all(isinstance(item, str) for item in value):
            raise ValueError(
                f"mir.fidelity.{field_name} must be a tuple of strings"
            )
    for index, process in enumerate(mir.processes):
        _validate_string(
            process.mechanism,
            field_name=f"mir.processes[{index}].mechanism",
        )
        if not isinstance(process.params, dict):
            raise ValueError(f"mir.processes[{index}].params must be a dict")

    json_fields = (
        ("metadata.provenance", mir.metadata.provenance),
        *((field_name, getattr(mir, field_name)) for field_name in record_list_fields),
        ("run.params", mir.run.params),
        ("trace", mir.trace),
        ("extensions", mir.extensions),
    )
    for field_name, value in json_fields:
        _normalize_json_value(value, context=f"mir.{field_name}")
    for index, process in enumerate(mir.processes):
        _normalize_json_value(
            process.params,
            context=f"mir.processes[{index}].params",
        )


def _canonical_mir_dict(
    value: Any,
    *,
    accept_fidelity_lists: bool,
) -> dict[str, Any]:
    obj = _as_object(value, context="mir")
    fidelity = _as_object(obj.get("fidelity"), context="mir.fidelity")
    normalized_mir = dict(obj)
    normalized_fidelity = dict(fidelity)
    allowed_types = (tuple, list) if accept_fidelity_lists else (tuple,)
    for field_name in ("required_tokens", "wrong_space_tokens"):
        tokens = fidelity.get(field_name)
        if not isinstance(tokens, allowed_types):
            expected = "a tuple or list" if accept_fidelity_lists else "a tuple"
            raise ValueError(f"mir.fidelity.{field_name} must be {expected}")
        normalized_fidelity[field_name] = list(tokens)
    normalized_mir["fidelity"] = normalized_fidelity
    normalized = _normalize_json_value(normalized_mir, context="mir")
    if not isinstance(normalized, dict):
        raise ValueError("mir must be an object")
    return normalized


def _mir_to_dict(mir: Any, *, canonical: bool = False) -> dict[str, Any]:
    _validate_mir(mir)
    try:
        raw = mir.to_dict()
    except RecursionError as exc:
        raise ValueError("mir contains a cyclic value and cannot be serialized") from exc
    except (TypeError, ValueError) as exc:
        raise ValueError(f"mir could not be serialized: {exc}") from exc
    canonical_value = _canonical_mir_dict(
        raw,
        accept_fidelity_lists=False,
    )
    return canonical_value if canonical else raw


def _strict_mir_from_dict(value: Any) -> MIR:
    obj = _require_keys(value, required=_MIR_KEYS, context="mir")
    for field_name, keys in _MIR_NESTED_KEYS.items():
        _require_keys(obj[field_name], required=keys, context=f"mir.{field_name}")

    processes = obj["processes"]
    if not isinstance(processes, list):
        raise ValueError("mir.processes must be a list")
    for index, process in enumerate(processes):
        _require_keys(
            process,
            required=_MIR_PROCESS_KEYS,
            context=f"mir.processes[{index}]",
        )

    input_canonical = _canonical_mir_dict(
        obj,
        accept_fidelity_lists=True,
    )
    try:
        mir = MIR.from_dict(copy.deepcopy(dict(obj)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"mir is invalid: {exc}") from exc
    _validate_mir(mir)

    if _canonical_json(
        _mir_to_dict(mir, canonical=True),
        context="reconstructed mir",
    ) != _canonical_json(input_canonical, context="input mir"):
        raise ValueError("mir does not round-trip exactly")
    return mir


def _path_starts_with(
    tokens: tuple[str, ...],
    root: tuple[str, ...],
) -> bool:
    return tokens[: len(root)] == root


def _authorize_patch_path(
    tokens: tuple[str, ...],
    *,
    path: str,
    field_name: str,
) -> None:
    if not tokens:
        raise ValueError(
            f"{field_name} {path!r}: root-object replacement is not allowed"
        )
    if any(_path_starts_with(tokens, root) for root in _FORBIDDEN_TARGET_ROOTS):
        raise ValueError(f"{field_name} {path!r} is a forbidden path")
    if not any(_path_starts_with(tokens, root) for root in _ALLOWED_TARGET_ROOTS):
        raise ValueError(f"{field_name} {path!r} is not an allowed model path")


def _prepare_patch_operations(
    patch: SemanticPatch,
) -> tuple[tuple[SemanticPatchOperation, tuple[str, ...]], ...]:
    prepared: list[tuple[SemanticPatchOperation, tuple[str, ...]]] = []
    for index, operation in enumerate(patch.operations):
        field_name = f"operations[{index}].path"
        tokens = _decode_json_pointer(operation.path, field_name=field_name)
        _authorize_patch_path(
            tokens,
            path=operation.path,
            field_name=field_name,
        )
        if "-" in tokens and (
            tokens[-1] != "-"
            or operation.op != "add"
            or tokens.count("-") != 1
        ):
            raise ValueError(
                f"{field_name} {operation.path!r} may use '-' only as the final "
                "token of an add operation on a list"
            )
        prepared.append((operation, tokens))
    return tuple(prepared)


def _array_index(
    token: str,
    *,
    length: int,
    allow_end: bool,
    path: str,
) -> int:
    if _ARRAY_INDEX_RE.fullmatch(token) is None:
        raise ValueError(f"invalid array index {token!r} at {path}")
    maximum = length if allow_end else length - 1
    maximum_token = str(maximum)
    if maximum < 0 or len(token) > len(maximum_token) or (
        len(token) == len(maximum_token) and token > maximum_token
    ):
        raise ValueError(f"array index {token!r} is out of bounds at {path}")
    try:
        return int(token)
    except ValueError:
        raise ValueError(f"invalid array index {token!r} at {path}") from None


def _patch_parent(
    document: dict[str, Any],
    tokens: tuple[str, ...],
    *,
    path: str,
) -> tuple[dict[str, Any] | list[Any], str]:
    current: Any = document
    for token in tokens[:-1]:
        if isinstance(current, dict):
            if token == "-":
                raise ValueError(f"'-' is valid only for a list add at {path}")
            if token not in current:
                raise ValueError(f"patch target does not exist: {path}")
            current = current[token]
            continue
        if isinstance(current, list):
            index = _array_index(
                token,
                length=len(current),
                allow_end=False,
                path=path,
            )
            current = current[index]
            continue
        raise ValueError(f"patch target parent is not a container: {path}")

    if not isinstance(current, (dict, list)):
        raise ValueError(f"patch target parent is not a container: {path}")
    return current, tokens[-1]


def _apply_patch_operation(
    document: dict[str, Any],
    operation: SemanticPatchOperation,
    tokens: tuple[str, ...],
) -> None:
    parent, token = _patch_parent(document, tokens, path=operation.path)
    value = _MISSING
    if operation.op in {"add", "replace"}:
        value = _normalize_json_value(
            operation.value,
            context=f"patch value at {operation.path}",
        )

    if isinstance(parent, dict):
        if token == "-":
            raise ValueError(f"'-' is valid only for a list add at {operation.path}")
        if operation.op == "add":
            parent[token] = value
            return
        if token not in parent:
            raise ValueError(f"patch target does not exist: {operation.path}")
        if operation.op == "replace":
            parent[token] = value
        else:
            del parent[token]
        return

    if operation.op == "add" and token == "-":
        parent.append(value)
        return

    index = _array_index(
        token,
        length=len(parent),
        allow_end=operation.op == "add",
        path=operation.path,
    )
    if operation.op == "add":
        parent.insert(index, value)
    elif operation.op == "replace":
        parent[index] = value
    else:
        del parent[index]


def _apply_prepared_patch_operations(
    document: dict[str, Any],
    prepared_operations: tuple[
        tuple[SemanticPatchOperation, tuple[str, ...]],
        ...,
    ],
) -> None:
    for operation, tokens in prepared_operations:
        _apply_patch_operation(document, operation, tokens)


def _apply_patch_to_fresh_copy(
    source: dict[str, Any],
    prepared_operations: tuple[
        tuple[SemanticPatchOperation, tuple[str, ...]],
        ...,
    ],
) -> dict[str, Any]:
    result_copy = copy.deepcopy(source)
    _apply_prepared_patch_operations(result_copy, prepared_operations)
    return result_copy


def _strict_records_from_patched_list(
    value: Any,
    *,
    record_type: type,
    field_name: str,
) -> tuple[Any, ...]:
    records = _records_from_list(
        value,
        record_type=record_type,
        field_name=field_name,
    )
    rebuilt = [record.to_dict() for record in records]
    if rebuilt != value:
        raise ValueError(f"{field_name} must round-trip exactly after reconstruction")
    return records


def _strict_patch_audit_records(
    document: dict[str, Any],
) -> tuple[
    tuple[AssumptionRecord, ...],
    tuple[UnresolvedDecision, ...],
]:
    assumptions = _strict_records_from_patched_list(
        document.get("assumptions", _MISSING),
        record_type=AssumptionRecord,
        field_name="assumptions",
    )
    unresolved_decisions = _strict_records_from_patched_list(
        document.get("unresolved_decisions", _MISSING),
        record_type=UnresolvedDecision,
        field_name="unresolved_decisions",
    )
    return assumptions, unresolved_decisions


def _validate_patch_audit_identities(
    *,
    original_assumptions: Sequence[AssumptionRecord],
    patched_assumptions: Sequence[AssumptionRecord],
    original_decisions: Sequence[UnresolvedDecision],
    patched_decisions: Sequence[UnresolvedDecision],
) -> None:
    for records, id_field, field_name in (
        (original_assumptions, "assumption_id", "assumptions"),
        (patched_assumptions, "assumption_id", "assumptions"),
        (original_decisions, "decision_id", "unresolved_decisions"),
        (patched_decisions, "decision_id", "unresolved_decisions"),
    ):
        _validate_unique_record_ids(
            records,
            id_field=id_field,
            field_name=field_name,
        )

    patched_assumptions_by_id = {
        record.assumption_id: record for record in patched_assumptions
    }
    for original in original_assumptions:
        patched = patched_assumptions_by_id.get(original.assumption_id)
        if patched is None:
            raise ValueError(
                f"existing assumption_id {original.assumption_id!r} must be preserved"
            )
        if patched.source != original.source:
            raise ValueError(
                f"source for assumption_id {original.assumption_id!r} "
                "must not change"
            )

    patched_decisions_by_id = {
        record.decision_id: record for record in patched_decisions
    }
    for original in original_decisions:
        if original.decision_id not in patched_decisions_by_id:
            raise ValueError(
                f"existing decision_id {original.decision_id!r} must be preserved"
            )


def _validate_patch_application(
    source: dict[str, Any],
    prepared_operations: tuple[
        tuple[SemanticPatchOperation, tuple[str, ...]],
        ...,
    ],
) -> None:
    original_assumptions, original_decisions = _strict_patch_audit_records(source)
    validation_copy = copy.deepcopy(source)
    _apply_prepared_patch_operations(validation_copy, prepared_operations)
    patched_assumptions, patched_decisions = _strict_patch_audit_records(
        validation_copy
    )
    _validate_patch_audit_identities(
        original_assumptions=original_assumptions,
        patched_assumptions=patched_assumptions,
        original_decisions=original_decisions,
        patched_decisions=patched_decisions,
    )


def mir_digest(mir: MIR) -> str:
    """Return SHA-256 over canonical ``mir.to_dict()``."""
    return _digest(
        _mir_to_dict(mir, canonical=True),
        context="mir",
    )


def patch_digest(
    patch_or_operations: SemanticPatch | Sequence[SemanticPatchOperation],
) -> str:
    """Return SHA-256 over the ordered operations only."""
    if isinstance(patch_or_operations, SemanticPatch):
        patch_or_operations.validate()
        operations = patch_or_operations.operations
    elif isinstance(patch_or_operations, Sequence) and not isinstance(
        patch_or_operations,
        (str, bytes, bytearray),
    ):
        operations = tuple(patch_or_operations)
        if not operations:
            raise ValueError("operations must be a non-empty sequence")
        for index, operation in enumerate(operations):
            if not isinstance(operation, SemanticPatchOperation):
                raise ValueError(
                    f"operations[{index}] must be a SemanticPatchOperation"
                )
            operation.validate(_context=f"operations[{index}]")
    else:
        raise ValueError("patch must be a SemanticPatch or operation sequence")
    return _digest(
        [operation.to_dict() for operation in operations],
        context="operations",
    )


def _state_digest_from_components(
    *,
    mode: str,
    assumptions: Sequence[AssumptionRecord],
    unresolved_decisions: Sequence[UnresolvedDecision],
    routing: RoutingDecision,
    lock: ContractLock,
) -> str:
    state = {
        "mode": mode,
        "assumptions": [record.to_dict() for record in assumptions],
        "unresolved_decisions": [
            record.to_dict() for record in unresolved_decisions
        ],
        "routing": routing.to_dict(),
        "lock": lock.to_dict(),
    }
    return _digest(state, context="contract state")


def state_digest(contract: NaturalLanguageModelContract) -> str:
    """Hash current non-MIR state, excluding lineage and revision fields."""
    if not isinstance(contract, NaturalLanguageModelContract):
        raise ValueError("contract must be a NaturalLanguageModelContract")
    return _state_digest_from_components(
        mode=contract.mode,
        assumptions=contract.assumptions,
        unresolved_decisions=contract.unresolved_decisions,
        routing=contract.routing,
        lock=contract.lock,
    )


contract_state_digest = state_digest


def contract_revision_digest(
    *,
    contract_id: str,
    parent_contract_revision: str,
    branch_id: str,
    action: str,
    source: str,
    rationale: str,
    patch_digest: str | None,
    state_digest: str,
    mir_digest: str,
) -> str:
    """Hash one source-aware revision event and its resulting identities."""
    _validate_nonempty_string(contract_id, field_name="contract_id")
    _validate_digest(
        parent_contract_revision,
        field_name="parent_contract_revision",
        allow_empty=True,
    )
    _validate_nonempty_string(branch_id, field_name="branch_id")
    _validate_choice(action, _REVISION_ACTIONS, field_name="action")
    _validate_choice(source, _REVISION_SOURCES, field_name="source")
    _validate_string(rationale, field_name="rationale")
    if action == "patch":
        _validate_digest(patch_digest, field_name="patch_digest")
    elif patch_digest is not None:
        raise ValueError("patch_digest is only valid for patch actions")
    _validate_digest(state_digest, field_name="state_digest")
    _validate_digest(mir_digest, field_name="mir_digest")

    event: dict[str, Any] = {
        "contract_id": contract_id,
        "parent_contract_revision": parent_contract_revision,
        "branch_id": branch_id,
        "action": action,
        "source": source,
        "rationale": rationale,
        "state_digest": state_digest,
        "mir_digest": mir_digest,
    }
    if patch_digest is not None:
        event["patch_digest"] = patch_digest
    return _digest(event, context="revision event")


revision_digest = contract_revision_digest


def create_model_contract(
    *,
    contract_id: str,
    branch_id: str,
    mode: str,
    mir: MIR,
    assumptions: Sequence[AssumptionRecord],
    unresolved_decisions: Sequence[UnresolvedDecision],
    routing: RoutingDecision,
    source: str,
) -> NaturalLanguageModelContract:
    """Wrap a validated MIR in one deterministic, unlocked create revision."""
    _validate_nonempty_string(contract_id, field_name="contract_id")
    _validate_nonempty_string(branch_id, field_name="branch_id")
    _validate_choice(mode, _MODES, field_name="mode")
    _validate_choice(source, _REVISION_SOURCES, field_name="source")

    source_mir_dict = _mir_to_dict(mir)
    wrapped_mir = _strict_mir_from_dict(source_mir_dict)
    if _mir_to_dict(wrapped_mir) != source_mir_dict:
        raise ValueError("mir must be preserved exactly during contract creation")

    if not isinstance(assumptions, Sequence) or isinstance(
        assumptions, (str, bytes, bytearray)
    ):
        raise ValueError("assumptions must be a list of AssumptionRecord records")
    assumption_records = tuple(assumptions)
    _validate_record_sequence(
        assumption_records,
        record_type=AssumptionRecord,
        field_name="assumptions",
    )
    for index, assumption in enumerate(assumption_records):
        assumption.validate(_context=f"assumptions[{index}]")
        if assumption.source in {"inferred", "default"} and assumption.confirmed:
            raise ValueError(
                f"assumptions[{index}].confirmed must be false when source is "
                f"{assumption.source!r} at contract creation"
            )

    if not isinstance(unresolved_decisions, Sequence) or isinstance(
        unresolved_decisions, (str, bytes, bytearray)
    ):
        raise ValueError(
            "unresolved_decisions must be a list of UnresolvedDecision records"
        )
    decision_records = tuple(unresolved_decisions)
    _validate_record_sequence(
        decision_records,
        record_type=UnresolvedDecision,
        field_name="unresolved_decisions",
    )
    for index, decision in enumerate(decision_records):
        decision.validate(_context=f"unresolved_decisions[{index}]")

    if not isinstance(routing, RoutingDecision):
        raise ValueError("routing must be a RoutingDecision")
    routing.validate(_context="routing")
    if routing.resolved_mode != mode:
        raise ValueError("routing.resolved_mode must equal mode")

    lock = ContractLock()
    current_mir_digest = mir_digest(wrapped_mir)
    provisional = NaturalLanguageModelContract(
        schema=MODEL_CONTRACT_SCHEMA,
        contract_id=contract_id,
        branch_id=branch_id,
        mode=mode,
        mir=wrapped_mir,
        assumptions=assumption_records,
        unresolved_decisions=decision_records,
        routing=routing,
        lock=lock,
        mir_digest=current_mir_digest,
        contract_revision="",
        parent_contract_revision="",
        lineage=(),
    )
    current_state_digest = state_digest(provisional)
    rationale = "create model contract"
    current_revision = contract_revision_digest(
        contract_id=contract_id,
        parent_contract_revision="",
        branch_id=branch_id,
        action="create",
        source=source,
        rationale=rationale,
        patch_digest=None,
        state_digest=current_state_digest,
        mir_digest=current_mir_digest,
    )
    revision = RevisionRecord(
        contract_revision=current_revision,
        parent_contract_revision="",
        branch_id=branch_id,
        action="create",
        source=source,
        rationale=rationale,
        patch_digest=None,
        mir_digest=current_mir_digest,
        state_digest=current_state_digest,
    )
    contract = NaturalLanguageModelContract(
        schema=MODEL_CONTRACT_SCHEMA,
        contract_id=contract_id,
        branch_id=branch_id,
        mode=mode,
        mir=wrapped_mir,
        assumptions=assumption_records,
        unresolved_decisions=decision_records,
        routing=routing,
        lock=lock,
        mir_digest=current_mir_digest,
        contract_revision=current_revision,
        parent_contract_revision="",
        lineage=(revision,),
    )
    contract.validate()
    return contract


def apply_semantic_patch(
    contract: NaturalLanguageModelContract,
    patch: SemanticPatch,
) -> NaturalLanguageModelContract:
    """Apply one constrained semantic patch and append an atomic revision."""
    if not isinstance(contract, NaturalLanguageModelContract):
        raise ValueError("contract must be a NaturalLanguageModelContract")
    contract.validate()
    if not isinstance(patch, SemanticPatch):
        raise ValueError("patch must be a SemanticPatch")
    patch.validate()

    if patch.base_contract_revision != contract.contract_revision:
        raise ValueError(
            "patch.base_contract_revision does not match contract.contract_revision"
        )
    if contract.lock.status == "locked":
        raise ValueError("cannot apply a semantic patch to a locked contract")

    prepared_operations = _prepare_patch_operations(patch)
    source = contract.to_dict()
    _validate_patch_application(source, prepared_operations)
    patched = _apply_patch_to_fresh_copy(source, prepared_operations)

    patched_mir_dict = patched["mir"]
    rebuilt_mir = _strict_mir_from_dict(patched_mir_dict)
    if _canonical_json(
        _mir_to_dict(rebuilt_mir, canonical=True),
        context="reconstructed patched mir",
    ) != _canonical_json(
        _canonical_mir_dict(
            patched_mir_dict,
            accept_fidelity_lists=True,
        ),
        context="patched mir",
    ):
        raise ValueError("patched mir must round-trip exactly after reconstruction")

    assumptions, unresolved_decisions = _strict_patch_audit_records(patched)
    _validate_patch_audit_identities(
        original_assumptions=contract.assumptions,
        patched_assumptions=assumptions,
        original_decisions=contract.unresolved_decisions,
        patched_decisions=unresolved_decisions,
    )

    current_mir_digest = mir_digest(rebuilt_mir)
    provisional = NaturalLanguageModelContract(
        schema=contract.schema,
        contract_id=contract.contract_id,
        branch_id=contract.branch_id,
        mode=contract.mode,
        mir=rebuilt_mir,
        assumptions=assumptions,
        unresolved_decisions=unresolved_decisions,
        routing=contract.routing,
        lock=contract.lock,
        mir_digest=current_mir_digest,
        contract_revision=contract.contract_revision,
        parent_contract_revision=contract.parent_contract_revision,
        lineage=contract.lineage,
    )
    current_state_digest = state_digest(provisional)
    current_patch_digest = patch_digest(patch)
    parent_revision = contract.contract_revision
    current_revision = contract_revision_digest(
        contract_id=contract.contract_id,
        parent_contract_revision=parent_revision,
        branch_id=contract.branch_id,
        action="patch",
        source=patch.source,
        rationale=patch.rationale,
        patch_digest=current_patch_digest,
        state_digest=current_state_digest,
        mir_digest=current_mir_digest,
    )
    revision = RevisionRecord(
        contract_revision=current_revision,
        parent_contract_revision=parent_revision,
        branch_id=contract.branch_id,
        action="patch",
        source=patch.source,
        rationale=patch.rationale,
        patch_digest=current_patch_digest,
        mir_digest=current_mir_digest,
        state_digest=current_state_digest,
    )
    result = NaturalLanguageModelContract(
        schema=contract.schema,
        contract_id=contract.contract_id,
        branch_id=contract.branch_id,
        mode=contract.mode,
        mir=rebuilt_mir,
        assumptions=assumptions,
        unresolved_decisions=unresolved_decisions,
        routing=contract.routing,
        lock=contract.lock,
        mir_digest=current_mir_digest,
        contract_revision=current_revision,
        parent_contract_revision=parent_revision,
        lineage=contract.lineage + (revision,),
    )
    result.validate()
    return result


_EQUIVALENCE_NON_CLAIMS = (
    "No claim is made about natural-language utterance equivalence, LLM "
    "extraction equivalence, UI behavior equivalence, runtime behavior "
    "equivalence, construct validity, or scientific truth."
)


def _equivalence_failure(reason: str) -> tuple[bool, str]:
    return (
        False,
        "FAIL: structured-patch equivalence was not established: "
        f"{reason}. {_EQUIVALENCE_NON_CLAIMS}",
    )


def semantic_patch_equivalence_gate(
    base_contract: NaturalLanguageModelContract,
    patch_a: SemanticPatch,
    patch_b: SemanticPatch,
) -> tuple[bool, str]:
    """Check cross-source equivalence of two already-structured patches only.

    This gate does not evaluate natural-language utterances, LLM extraction, UI
    behavior, runtime behavior, construct validity, or scientific truth.
    """
    try:
        result_a = apply_semantic_patch(base_contract, patch_a)
        result_b = apply_semantic_patch(base_contract, patch_b)
        patch_digest_a = patch_digest(patch_a)
        patch_digest_b = patch_digest(patch_b)

        if patch_digest_a != patch_digest_b:
            return _equivalence_failure("ordered patch digests differ")
        if result_a.mir_digest != result_b.mir_digest:
            return _equivalence_failure("resulting MIR digests differ")
        if result_a.mir.to_dict() != result_b.mir.to_dict():
            return _equivalence_failure("resulting MIR dictionaries differ")
        if patch_a.source == patch_b.source:
            return _equivalence_failure("producer source labels must be distinct")
        if (
            result_a.lineage[-1].source != patch_a.source
            or result_b.lineage[-1].source != patch_b.source
        ):
            return _equivalence_failure(
                "producer source labels are not independently visible in lineage"
            )
        if result_a.contract_revision == result_b.contract_revision:
            return _equivalence_failure(
                "contract revisions must differ for distinct producer sources"
            )
    except ValueError as exc:
        return _equivalence_failure(
            f"validation or patch application failed: {exc}"
        )
    except Exception as exc:
        return _equivalence_failure(
            "validation or patch application failed "
            f"({type(exc).__name__}); no partial result is reported"
        )

    return (
        True,
        "PASS: structured-patch equivalence only; ordered patch operations and "
        "resulting MIR are equal, while distinct producer source labels remain "
        "visible in distinct contract revisions. This does not establish "
        "natural-language utterance equivalence, LLM extraction equivalence, "
        "UI behavior equivalence, runtime behavior equivalence, construct "
        "validity, or scientific truth.",
    )


def _routing_before_lifecycle_action(
    routing: RoutingDecision,
    revision: RevisionRecord,
    *,
    index: int,
    result_mode: str,
    predecessor_mode: str,
) -> RoutingDecision:
    action = revision.action
    if routing.resolved_mode != result_mode:
        raise ValueError(
            f"lineage[{index}] {action} action routing.resolved_mode must be "
            f"{result_mode}"
        )
    expected_overridden = _routing_is_overridden(
        requested_mode=routing.requested_mode,
        resolved_mode=result_mode,
    )
    if routing.overridden != expected_overridden:
        raise ValueError(
            f"lineage[{index}] {action} action routing.overridden does not match "
            "requested and resolved modes"
        )
    if routing.rationale[-1] != revision.rationale:
        raise ValueError(
            f"lineage[{index}] {action} action routing rationale must end with "
            "the revision rationale"
        )
    if len(routing.rationale) == 1:
        raise ValueError(
            f"lineage[{index}] {action} action predecessor routing rationale "
            "must be non-empty"
        )
    return RoutingDecision(
        requested_mode=routing.requested_mode,
        resolved_mode=predecessor_mode,
        rationale=routing.rationale[:-1],
        overridden=_routing_is_overridden(
            requested_mode=routing.requested_mode,
            resolved_mode=predecessor_mode,
        ),
    )


def _validate_lifecycle_state_transitions(
    contract: NaturalLanguageModelContract,
) -> None:
    mode = contract.mode
    assumptions = contract.assumptions
    unresolved_decisions = contract.unresolved_decisions
    routing = contract.routing
    lock = contract.lock
    replayed_state_digest = _state_digest_from_components(
        mode=mode,
        assumptions=assumptions,
        unresolved_decisions=unresolved_decisions,
        routing=routing,
        lock=lock,
    )

    for index in range(len(contract.lineage) - 1, 0, -1):
        revision = contract.lineage[index]
        previous = contract.lineage[index - 1]
        if replayed_state_digest != revision.state_digest:
            raise ValueError(
                f"lineage[{index}] {revision.action} action state_digest does not "
                "match the replayed result state"
            )

        if revision.action == "patch":
            # Operations are not retained. A state-neutral patch can be crossed;
            # a state-changing patch is the replay boundary for earlier actions.
            if _is_state_changing_patch(previous, revision):
                break
            continue

        _validate_nonempty_string(
            revision.rationale,
            field_name=f"lineage[{index}].rationale",
        )

        if revision.action == "promote":
            if mode != "research":
                raise ValueError(
                    f"lineage[{index}] promote action must result in research mode"
                )
            if lock.status != "unlocked":
                raise ValueError(
                    f"lineage[{index}] promote action must result in an unlocked state"
                )
            predecessor_routing = _routing_before_lifecycle_action(
                routing,
                revision,
                index=index,
                result_mode="research",
                predecessor_mode="quick",
            )
            predecessor_mode = "quick"
            predecessor_lock = lock
        elif revision.action == "lock":
            if mode != "research":
                raise ValueError(
                    f"lineage[{index}] lock action must result in research mode"
                )
            if lock.status != "locked":
                raise ValueError(
                    f"lineage[{index}] lock action must result in a locked state"
                )
            if lock.reason != revision.rationale:
                raise ValueError(
                    f"lineage[{index}] lock action reason must match the revision "
                    "rationale"
                )
            if lock.locked_mir_digest != revision.mir_digest:
                raise ValueError(
                    f"lineage[{index}] lock action locked_mir_digest must match "
                    "the revision mir_digest"
                )
            if (
                lock.locked_contract_revision
                != revision.parent_contract_revision
            ):
                raise ValueError(
                    f"lineage[{index}] lock action locked_contract_revision must "
                    "match the revision parent"
                )
            unconfirmed_assumptions, open_decisions = (
                _material_research_blocker_ids(
                    assumptions,
                    unresolved_decisions,
                )
            )
            if unconfirmed_assumptions:
                raise ValueError(
                    f"lineage[{index}] lock action has unconfirmed material "
                    "assumptions: " + ", ".join(unconfirmed_assumptions)
                )
            if open_decisions:
                raise ValueError(
                    f"lineage[{index}] lock action has open material decisions: "
                    + ", ".join(open_decisions)
                )
            predecessor_mode = "research"
            predecessor_routing = routing
            predecessor_lock = ContractLock()
        elif revision.action == "branch":
            if lock != ContractLock():
                raise ValueError(
                    f"lineage[{index}] branch action must result in an unlocked "
                    "default lock state"
                )
            predecessor_routing = _routing_before_lifecycle_action(
                routing,
                revision,
                index=index,
                result_mode=mode,
                predecessor_mode="research",
            )
            predecessor_mode = "research"
            predecessor_lock = ContractLock(
                status="locked",
                reason=previous.rationale,
                locked_mir_digest=revision.mir_digest,
                locked_contract_revision=previous.parent_contract_revision,
            )
        else:
            continue

        predecessor_state_digest = _state_digest_from_components(
            mode=predecessor_mode,
            assumptions=assumptions,
            unresolved_decisions=unresolved_decisions,
            routing=predecessor_routing,
            lock=predecessor_lock,
        )
        if predecessor_state_digest != previous.state_digest:
            raise ValueError(
                f"lineage[{index}] {revision.action} action predecessor "
                "state_digest does not match the previous revision"
            )

        mode = predecessor_mode
        routing = predecessor_routing
        lock = predecessor_lock
        replayed_state_digest = predecessor_state_digest


def _lifecycle_routing(
    routing: RoutingDecision,
    *,
    resolved_mode: str,
    rationale: str,
) -> RoutingDecision:
    return RoutingDecision(
        requested_mode=routing.requested_mode,
        resolved_mode=resolved_mode,
        rationale=routing.rationale + (rationale,),
        overridden=_routing_is_overridden(
            requested_mode=routing.requested_mode,
            resolved_mode=resolved_mode,
        ),
    )


def _append_lifecycle_revision(
    contract: NaturalLanguageModelContract,
    *,
    branch_id: str,
    mode: str,
    routing: RoutingDecision,
    lock: ContractLock,
    action: str,
    source: str,
    rationale: str,
) -> NaturalLanguageModelContract:
    parent_revision = contract.contract_revision
    current_mir = contract.mir
    provisional = NaturalLanguageModelContract(
        schema=contract.schema,
        contract_id=contract.contract_id,
        branch_id=branch_id,
        mode=mode,
        mir=current_mir,
        assumptions=contract.assumptions,
        unresolved_decisions=contract.unresolved_decisions,
        routing=routing,
        lock=lock,
        mir_digest=contract.mir_digest,
        contract_revision=contract.contract_revision,
        parent_contract_revision=contract.parent_contract_revision,
        lineage=contract.lineage,
    )
    current_state_digest = state_digest(provisional)
    current_revision = contract_revision_digest(
        contract_id=contract.contract_id,
        parent_contract_revision=parent_revision,
        branch_id=branch_id,
        action=action,
        source=source,
        rationale=rationale,
        patch_digest=None,
        state_digest=current_state_digest,
        mir_digest=contract.mir_digest,
    )
    revision = RevisionRecord(
        contract_revision=current_revision,
        parent_contract_revision=parent_revision,
        branch_id=branch_id,
        action=action,
        source=source,
        rationale=rationale,
        patch_digest=None,
        mir_digest=contract.mir_digest,
        state_digest=current_state_digest,
    )
    result = NaturalLanguageModelContract(
        schema=contract.schema,
        contract_id=contract.contract_id,
        branch_id=branch_id,
        mode=mode,
        mir=current_mir,
        assumptions=contract.assumptions,
        unresolved_decisions=contract.unresolved_decisions,
        routing=routing,
        lock=lock,
        mir_digest=contract.mir_digest,
        contract_revision=current_revision,
        parent_contract_revision=parent_revision,
        lineage=contract.lineage + (revision,),
    )
    result.validate()
    return result


def promote_to_research(
    contract: NaturalLanguageModelContract,
    rationale: str,
    source: str,
) -> NaturalLanguageModelContract:
    """Explicitly promote one unlocked quick contract to research mode."""
    if not isinstance(contract, NaturalLanguageModelContract):
        raise ValueError("contract must be a NaturalLanguageModelContract")
    contract.validate()
    _validate_nonempty_string(rationale, field_name="rationale")
    _validate_choice(source, _REVISION_SOURCES, field_name="source")

    if contract.lock.status == "locked":
        raise ValueError("cannot promote a locked contract")
    if contract.mode != "quick":
        raise ValueError("promotion requires an unlocked quick contract")

    routing = _lifecycle_routing(
        contract.routing,
        resolved_mode="research",
        rationale=rationale,
    )
    return _append_lifecycle_revision(
        contract,
        branch_id=contract.branch_id,
        mode="research",
        routing=routing,
        lock=contract.lock,
        action="promote",
        source=source,
        rationale=rationale,
    )


def research_readiness(contract: NaturalLanguageModelContract) -> dict[str, Any]:
    """Return deterministic model-contract readiness for a research lock.

    This checks only the stored interaction contract. It is not scientific
    validation, a construct-validity assessment, or proof of Git provenance.
    """
    if not isinstance(contract, NaturalLanguageModelContract):
        raise ValueError("contract must be a NaturalLanguageModelContract")
    contract.validate()

    unconfirmed_assumptions, open_decisions = _material_research_blocker_ids(
        contract.assumptions,
        contract.unresolved_decisions,
    )

    issues: list[str] = []
    if contract.mode != "research":
        issues.append("mode_not_research")
    if contract.lock.status != "unlocked":
        issues.append("contract_locked")
    if unconfirmed_assumptions:
        issues.append("unconfirmed_material_assumptions")
    if open_decisions:
        issues.append("open_material_decisions")

    return {
        "ready": not issues,
        "issues": issues,
        "unconfirmed_material_assumptions": unconfirmed_assumptions,
        "open_material_decisions": open_decisions,
    }


def lock_contract(
    contract: NaturalLanguageModelContract,
    reason: str,
    source: str,
) -> NaturalLanguageModelContract:
    """Lock a research-ready contract at its current MIR and revision.

    The application lock is not Git ancestry proof or an evidentiary prediction
    lock, and it makes no claim about construct or scientific validity.
    """
    if not isinstance(contract, NaturalLanguageModelContract):
        raise ValueError("contract must be a NaturalLanguageModelContract")
    contract.validate()
    _validate_nonempty_string(reason, field_name="reason")
    _validate_choice(source, _REVISION_SOURCES, field_name="source")

    if contract.lock.status == "locked":
        raise ValueError("cannot lock an already locked contract")
    readiness = research_readiness(contract)
    if not readiness["ready"]:
        issues = ", ".join(readiness["issues"])
        raise ValueError(f"contract is not ready for research lock: {issues}")

    lock = ContractLock(
        status="locked",
        locked_mir_digest=contract.mir_digest,
        locked_contract_revision=contract.contract_revision,
        reason=reason,
    )
    return _append_lifecycle_revision(
        contract,
        branch_id=contract.branch_id,
        mode=contract.mode,
        routing=contract.routing,
        lock=lock,
        action="lock",
        source=source,
        rationale=reason,
    )


def branch_contract(
    contract: NaturalLanguageModelContract,
    branch_id: str,
    mode: str,
    rationale: str,
    source: str,
) -> NaturalLanguageModelContract:
    """Create one explicit unlocked child from a locked research contract."""
    if not isinstance(contract, NaturalLanguageModelContract):
        raise ValueError("contract must be a NaturalLanguageModelContract")
    contract.validate()
    _validate_nonempty_string(branch_id, field_name="branch_id")
    _validate_choice(mode, _MODES, field_name="mode")
    _validate_nonempty_string(rationale, field_name="rationale")
    _validate_choice(source, _REVISION_SOURCES, field_name="source")

    if any(revision.branch_id == branch_id for revision in contract.lineage):
        raise ValueError(
            "branch_id must be different from every branch_id already used in "
            "the contract lineage"
        )
    if contract.lock.status != "locked" or contract.mode != "research":
        raise ValueError("branching requires a locked research contract")

    routing = _lifecycle_routing(
        contract.routing,
        resolved_mode=mode,
        rationale=rationale,
    )
    return _append_lifecycle_revision(
        contract,
        branch_id=branch_id,
        mode=mode,
        routing=routing,
        lock=ContractLock(),
        action="branch",
        source=source,
        rationale=rationale,
    )
