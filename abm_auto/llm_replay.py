"""LLM-agent replay event validation helpers."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

SCHEMA = "abm-auto/llm-agent-replay-event/v1"
ALLOWED_EVENT_TYPES = frozenset({
    "environment_event",
    "model_response",
    "observation",
    "prompt",
    "state_update",
    "tool_call",
})


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sorted_values(values: frozenset[str]) -> str:
    return ", ".join(sorted(values))


def validate_llm_replay_events(events: list[dict]) -> dict:
    """Validate append-only LLM-agent replay events."""
    if not isinstance(events, list):
        return {"ok": False, "issues": ["events must be a list"], "event_count": 0}

    issues: list[str] = []
    previous_t: int | None = None
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            issues.append(f"events[{idx}] must be an object")
            continue

        if event.get("schema") != SCHEMA:
            issues.append(f"events[{idx}].schema must be {SCHEMA}")

        t = event.get("t")
        if isinstance(t, bool) or not isinstance(t, int) or t < 0:
            issues.append(f"events[{idx}].t must be a non-negative integer")
        elif previous_t is not None and t < previous_t:
            issues.append(f"events[{idx}].t must be >= previous event time")
        elif isinstance(t, int):
            previous_t = t

        if event.get("event_type") not in ALLOWED_EVENT_TYPES:
            issues.append(
                f"events[{idx}].event_type must be one of {_sorted_values(ALLOWED_EVENT_TYPES)}"
            )
        if not _is_nonempty_string(event.get("agent_id")):
            issues.append(f"events[{idx}].agent_id must be a non-empty string")
        if not isinstance(event.get("payload"), dict):
            issues.append(f"events[{idx}].payload must be an object")

    return {
        "ok": not issues,
        "issues": issues,
        "event_count": len(events),
    }


def load_llm_replay_jsonl(path: Path) -> list[dict]:
    """Load newline-delimited LLM-agent replay events."""
    events: list[dict] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def summarize_llm_replay_events(events: list[dict]) -> dict:
    """Return a compact replay summary."""
    valid_events = [event for event in events if isinstance(event, dict)]
    times = [event["t"] for event in valid_events if isinstance(event.get("t"), int)]
    agents = {
        event.get("agent_id")
        for event in valid_events
        if _is_nonempty_string(event.get("agent_id"))
    }
    event_types = Counter(
        event.get("event_type")
        for event in valid_events
        if event.get("event_type") in ALLOWED_EVENT_TYPES
    )
    return {
        "event_count": len(valid_events),
        "agent_count": len(agents),
        "first_t": min(times) if times else None,
        "last_t": max(times) if times else None,
        "event_types": dict(sorted(event_types.items())),
    }


__all__ = [
    "ALLOWED_EVENT_TYPES",
    "SCHEMA",
    "load_llm_replay_jsonl",
    "summarize_llm_replay_events",
    "validate_llm_replay_events",
]
