"""
3-tier experiment memory for ABM research.

Adapted from automaton-main's 5-tier memory, simplified for ABM experiments:

- Working Memory: Current experiment state (active params, hypothesis, run status)
- Episodic Memory: Per-run records (params → metrics → insights, append-only JSONL)
- Semantic Memory: Cross-experiment knowledge (extracted patterns, validated rules)

No SQLite — uses flat files (JSON/JSONL) for portability and git-friendliness.
Token budget prevents context explosion when injecting memory into LLM prompts.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class WorkingEntry:
    key: str
    value: Any
    priority: float = 0.5  # 0.0–1.0
    updated_at: float = field(default_factory=time.time)


@dataclass
class EpisodicEntry:
    run_id: int
    params: dict
    metrics: dict  # final metric values
    hypothesis: str = ""
    insights: str = ""  # LLM-generated analysis
    outcome: str = "neutral"  # success / failure / neutral
    importance: float = 0.5  # 0.0–1.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class SemanticEntry:
    key: str  # e.g. "infection_rate_effect"
    knowledge: str  # natural language description
    confidence: float = 0.5  # 0.0–1.0
    source_runs: list[int] = field(default_factory=list)
    category: str = "pattern"  # pattern | rule | anomaly | hypothesis
    updated_at: float = field(default_factory=time.time)


# ── Token estimation ─────────────────────────────────────────────────────────

def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for mixed CJK/English."""
    return max(1, len(text) // 3)


# ── Working Memory ───────────────────────────────────────────────────────────

class WorkingMemory:
    """Session-scoped active state. Max entries configurable, priority-pruned."""

    def __init__(self, path: Path, max_entries: int = 20):
        self.path = path / "working.json"
        self.max_entries = max_entries
        self._entries: dict[str, WorkingEntry] = {}
        self._load()

    def set(self, key: str, value: Any, priority: float = 0.5) -> None:
        self._entries[key] = WorkingEntry(key=key, value=value, priority=priority)
        self._prune()
        self._save()

    def get(self, key: str) -> Any | None:
        e = self._entries.get(key)
        return e.value if e else None

    def delete(self, key: str) -> None:
        self._entries.pop(key, None)
        self._save()

    def all(self) -> list[WorkingEntry]:
        return sorted(self._entries.values(), key=lambda e: -e.priority)

    def to_context(self, max_tokens: int = 500) -> str:
        """Serialize for LLM injection, respecting token budget."""
        lines = []
        tokens = 0
        for e in self.all():
            line = f"- [{e.key}] (p={e.priority:.1f}): {e.value}"
            t = estimate_tokens(line)
            if tokens + t > max_tokens:
                break
            lines.append(line)
            tokens += t
        return "\n".join(lines)

    def _prune(self) -> None:
        if len(self._entries) > self.max_entries:
            sorted_keys = sorted(self._entries, key=lambda k: self._entries[k].priority)
            for k in sorted_keys[:len(self._entries) - self.max_entries]:
                del self._entries[k]

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self._entries = {
                k: WorkingEntry(**v) for k, v in data.items()
            }

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self._entries.items()}
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── Episodic Memory ──────────────────────────────────────────────────────────

class EpisodicMemory:
    """Append-only run log. JSONL format for streaming and git diffs."""

    def __init__(self, path: Path, max_entries: int | None = None):
        self.path = path / "episodic.jsonl"
        self.max_entries = max_entries  # For future pruning if needed

    def record(self, entry: EpisodicEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def all(self) -> list[EpisodicEntry]:
        if not self.path.exists():
            return []
        entries = []
        for line in self.path.read_text().strip().split("\n"):
            if line.strip():
                entries.append(EpisodicEntry(**json.loads(line)))
        return entries

    def recent(self, n: int = 5) -> list[EpisodicEntry]:
        return self.all()[-n:]

    def by_run(self, run_id: int) -> EpisodicEntry | None:
        for e in self.all():
            if e.run_id == run_id:
                return e
        return None

    def to_context(self, max_tokens: int = 1500, n_recent: int = 10) -> str:
        """Serialize recent episodes for LLM injection."""
        entries = self.recent(n_recent)
        lines = []
        tokens = 0
        for e in reversed(entries):  # most recent first
            line = (
                f"Run {e.run_id} ({e.outcome}): "
                f"params={json.dumps(e.params, ensure_ascii=False)}, "
                f"metrics={json.dumps(e.metrics, ensure_ascii=False)}"
            )
            if e.hypothesis:
                line += f", hypothesis=\"{e.hypothesis}\""
            t = estimate_tokens(line)
            if tokens + t > max_tokens:
                break
            lines.append(line)
            tokens += t
        return "\n".join(lines)

    def summary_stats(self) -> dict:
        """Compute aggregate statistics across all episodes."""
        entries = self.all()
        if not entries:
            return {}

        all_metrics = {}
        for e in entries:
            for k, v in e.metrics.items():
                if isinstance(v, (int, float)):
                    all_metrics.setdefault(k, []).append(v)

        stats = {}
        for k, values in all_metrics.items():
            import numpy as np
            arr = np.array(values)
            stats[k] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "n": len(values),
            }
        return stats


# ── Semantic Memory ──────────────────────────────────────────────────────────

class SemanticMemory:
    """Cross-experiment knowledge base. Upsert by key, confidence-weighted."""

    def __init__(self, path: Path, max_entries: int = 200):
        self.path = path / "semantic.json"
        self.max_entries = max_entries
        self._entries: dict[str, SemanticEntry] = {}
        self._load()

    def store(self, key: str, knowledge: str, confidence: float = 0.5,
              source_runs: list[int] | None = None, category: str = "pattern") -> None:
        existing = self._entries.get(key)
        if existing:
            # Update: merge source_runs, take higher confidence
            merged_runs = sorted(set(existing.source_runs + (source_runs or [])))
            self._entries[key] = SemanticEntry(
                key=key,
                knowledge=knowledge,
                confidence=max(existing.confidence, confidence),
                source_runs=merged_runs,
                category=category,
            )
        else:
            self._entries[key] = SemanticEntry(
                key=key,
                knowledge=knowledge,
                confidence=confidence,
                source_runs=source_runs or [],
                category=category,
            )
        self._prune()
        self._save()

    def get(self, key: str) -> SemanticEntry | None:
        return self._entries.get(key)

    def search(self, query: str, category: str | None = None) -> list[SemanticEntry]:
        """Simple keyword search across knowledge text."""
        query_lower = query.lower()
        results = []
        for e in self._entries.values():
            if category and e.category != category:
                continue
            if query_lower in e.knowledge.lower() or query_lower in e.key.lower():
                results.append(e)
        results.sort(key=lambda e: -e.confidence)
        return results

    def by_category(self, category: str) -> list[SemanticEntry]:
        return [e for e in self._entries.values() if e.category == category]

    def all(self) -> list[SemanticEntry]:
        return sorted(self._entries.values(), key=lambda e: -e.confidence)

    def delete(self, key: str) -> None:
        self._entries.pop(key, None)
        self._save()

    def to_context(self, max_tokens: int = 1500) -> str:
        """Serialize for LLM injection, highest confidence first."""
        lines = []
        tokens = 0
        for e in self.all():
            line = f"[{e.category}] {e.key} (conf={e.confidence:.2f}): {e.knowledge}"
            t = estimate_tokens(line)
            if tokens + t > max_tokens:
                break
            lines.append(line)
            tokens += t
        return "\n".join(lines)

    def _prune(self) -> None:
        if len(self._entries) > self.max_entries:
            sorted_keys = sorted(
                self._entries,
                key=lambda k: (self._entries[k].confidence, self._entries[k].updated_at),
            )
            for k in sorted_keys[:len(self._entries) - self.max_entries]:
                del self._entries[k]

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self._entries = {k: SemanticEntry(**v) for k, v in data.items()}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: asdict(v) for k, v in self._entries.items()}
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ── Unified Retriever ────────────────────────────────────────────────────────

class ExperimentMemory:
    """
    Unified interface for the 3-tier experiment memory.

    Token budget allocation (default 3500 total):
    - Working:  500 tokens (active state)
    - Episodic: 1500 tokens (recent runs)
    - Semantic: 1500 tokens (accumulated knowledge)
    """

    DEFAULT_BUDGET = {
        "working": 500,
        "episodic": 1500,
        "semantic": 1500,
    }

    def __init__(
        self,
        memory_dir: Path,
        budget: dict[str, int] | None = None,
        working_size: int | None = None,
        episodic_size: int | None = None,
        semantic_size: int | None = None,
    ):
        from abm_auto import config

        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.budget = budget or self.DEFAULT_BUDGET

        self.working = WorkingMemory(
            memory_dir,
            max_entries=working_size or config.WORKING_MEMORY_MAX_ENTRIES
        )
        self.episodic = EpisodicMemory(
            memory_dir,
            max_entries=episodic_size or config.EPISODIC_MEMORY_MAX_ENTRIES
        )
        self.semantic = SemanticMemory(
            memory_dir,
            max_entries=semantic_size or config.SEMANTIC_MEMORY_MAX_ENTRIES
        )

    def retrieve_context(self) -> str:
        """Build full memory context for LLM injection."""
        sections = []

        wc = self.working.to_context(self.budget["working"])
        if wc:
            sections.append(f"### 当前实验状态\n{wc}")

        ec = self.episodic.to_context(self.budget["episodic"])
        if ec:
            sections.append(f"### 历史运行记录\n{ec}")

        sc = self.semantic.to_context(self.budget["semantic"])
        if sc:
            sections.append(f"### 累积知识\n{sc}")

        return "\n\n".join(sections)

    def ingest_run(
        self,
        run_id: int,
        params: dict,
        metrics: dict,
        hypothesis: str = "",
        insights: str = "",
        outcome: str = "neutral",
        importance: float = 0.5,
    ) -> None:
        """Record a completed run into episodic memory + update working state."""
        # Episodic
        self.episodic.record(EpisodicEntry(
            run_id=run_id,
            params=params,
            metrics=metrics,
            hypothesis=hypothesis,
            insights=insights,
            outcome=outcome,
            importance=importance,
        ))

        # Update working memory
        self.working.set("last_run", run_id, priority=0.9)
        self.working.set("last_params", params, priority=0.7)
        self.working.set("last_metrics", metrics, priority=0.8)
        if hypothesis:
            self.working.set("current_hypothesis", hypothesis, priority=0.6)

    def add_knowledge(
        self,
        key: str,
        knowledge: str,
        confidence: float = 0.5,
        source_runs: list[int] | None = None,
        category: str = "pattern",
    ) -> None:
        """Store or update semantic knowledge."""
        self.semantic.store(key, knowledge, confidence, source_runs, category)
