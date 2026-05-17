# ADR-002: Flat File Storage Over SQLite

**Status**: Accepted  
**Date**: 2024-04  
**Deciders**: Core team  
**Related**: [ADR-001](ADR-001-memory-architecture.md)

---

## Context and Problem Statement

The 3-tier memory system (ADR-001) requires persistent storage for:
- Working memory (session state)
- Episodic memory (run history)
- Semantic memory (cross-experiment knowledge)

Storage options range from plain text files to relational databases. The choice affects:
1. **Setup complexity** — Does the user need to install/configure a database?
2. **Portability** — Can workspaces be copied between machines?
3. **Version control** — Can memory be tracked in git?
4. **Inspectability** — Can users debug memory without special tools?

---

## Decision Drivers

1. **Zero-config deployment** — `pip install abm-auto` should be sufficient
2. **Git-friendly diffs** — Memory changes should produce readable diffs
3. **Human inspectability** — Users should be able to `cat memory/episodic.jsonl`
4. **Cross-platform portability** — Workspaces should work on macOS/Linux/Windows
5. **No server processes** — CLI tool should not require background daemons

---

## Considered Options

### Option 1: SQLite Database
Store all memory in `memory.db` with tables for working/episodic/semantic.

**Pros**:
- Structured queries (SQL)
- ACID transactions
- Efficient indexing for large datasets

**Cons**:
- Binary format (not human-readable)
- Git diffs show "binary file changed" (no line-level diffs)
- Requires SQLite library (usually available, but adds dependency)
- Schema migrations needed for updates

### Option 2: Flat Files (JSON/JSONL) — Selected
- `working.json` — Key-value pairs
- `episodic.jsonl` — One JSON object per line
- `semantic.json` — Key-value pairs

**Pros**:
- Human-readable (plain text)
- Git-friendly (line-level diffs)
- Zero dependencies (Python stdlib `json` module)
- Portable (copy directory = copy workspace)
- No schema migrations (flexible structure)

**Cons**:
- No indexing (linear scans for queries)
- No transactions (risk of partial writes on crash)
- Larger file sizes (no compression)

### Option 3: Pickle Files
Serialize Python objects to `.pkl` files.

**Pros**:
- Native Python serialization
- Preserves object types (datetime, custom classes)

**Cons**:
- Binary format (not human-readable)
- Security risk (pickle can execute arbitrary code)
- Not portable across Python versions
- Git diffs useless

---

## Decision Outcome

**Chosen option**: Flat files (JSON/JSONL) — Option 2

### File Formats

#### Working Memory: `working.json`
```json
{
  "current_hypothesis": {
    "value": "Higher infection rate → faster peak",
    "priority": 0.8,
    "updated_at": 1714473600.0
  },
  "last_run": {
    "value": 42,
    "priority": 0.9,
    "updated_at": 1714473650.0
  }
}
```

**Rationale**: Key-value structure, infrequent updates (once per iteration), small size (<5 KB).

#### Episodic Memory: `episodic.jsonl`
```jsonl
{"run_id": 1, "params": {"infection_rate": 0.03}, "metrics": {"peak_day": 56}, "insights": "Slow spread", "timestamp": 1714473600.0}
{"run_id": 2, "params": {"infection_rate": 0.05}, "metrics": {"peak_day": 42}, "insights": "Faster spread", "timestamp": 1714473650.0}
```

**Rationale**: Append-only log, one entry per run. JSONL (not JSON array) allows:
- Streaming writes (no need to rewrite entire file)
- Git diffs show new lines (not entire array change)
- Tail-like reading (`tail -n 10 episodic.jsonl`)

#### Semantic Memory: `semantic.json`
```json
{
  "pattern_001": {
    "key": "infection_rate_effect",
    "knowledge": "Doubling infection_rate reduces peak_day by ~30%",
    "confidence": 0.85,
    "source_runs": [1, 2, 5],
    "category": "pattern",
    "updated_at": 1714473700.0
  }
}
```

**Rationale**: Key-value structure, infrequent updates (once per experiment), moderate size (<100 KB).

---

## Consequences

### Positive

✅ **Zero-config**: No database installation required  
✅ **Git-friendly**: Line-level diffs for episodic memory  
✅ **Human-readable**: `cat memory/episodic.jsonl | jq` for debugging  
✅ **Portable**: Copy workspace directory = copy all state  
✅ **No migrations**: Schema changes don't break old workspaces  
✅ **Crash-safe (mostly)**: Episodic memory is append-only (partial writes just truncate last line)

### Negative

⚠️ **No indexing**: Searching 1000+ runs requires linear scan  
⚠️ **No transactions**: Working/semantic memory updates not atomic (risk of corruption on crash)  
⚠️ **Larger files**: JSON is verbose (no compression)  
⚠️ **Manual parsing**: No SQL queries (must write Python loops)

### Risks

🔴 **Episodic memory bloat**: 1000-run experiments → 1 MB+ JSONL files  
**Mitigation**: Compress old runs (keep params + metrics, discard raw output)

🔴 **Concurrent writes**: Multiple processes writing to same workspace → corruption  
**Mitigation**: Use file locking (Python `fcntl` module) or workspace-level locks

🔴 **JSON parsing overhead**: Large files slow to load  
**Mitigation**: Lazy loading (read last N lines of JSONL, not entire file)

---

## Implementation Details

### Write Safety

**Atomic writes** (working/semantic memory):
```python
import json
from pathlib import Path

def atomic_write(path: Path, data: dict):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(path)  # Atomic on POSIX systems
```

**Append-only writes** (episodic memory):
```python
def append_episode(path: Path, entry: dict):
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
```

### Read Optimization

**Tail reading** (episodic memory):
```python
def read_last_n_lines(path: Path, n: int) -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-n:]]
```

**Lazy loading** (semantic memory):
```python
class SemanticMemory:
    def __init__(self, path: Path):
        self.path = path
        self._cache = None
    
    def load(self):
        if self._cache is None:
            self._cache = json.loads(self.path.read_text())
        return self._cache
```

---

## Performance Characteristics

### Typical Workload (50-run experiment)

| Operation | Time | File Size |
|-----------|------|-----------|
| Write working.json | <1 ms | 2 KB |
| Append to episodic.jsonl | <1 ms | +1 KB |
| Read last 10 episodes | <5 ms | 10 KB |
| Load semantic.json | <10 ms | 20 KB |

### Large Workload (1000-run experiment)

| Operation | Time | File Size |
|-----------|------|-----------|
| Append to episodic.jsonl | <1 ms | +1 KB |
| Read last 10 episodes | <5 ms | 10 KB |
| Read all episodes | ~50 ms | 1 MB |
| Search episodes (linear) | ~100 ms | 1 MB |

**Conclusion**: Flat files are fast enough for typical ABM experiments (<100 runs). For large-scale studies (1000+ runs), consider SQLite migration.

---

## When to Reconsider

Revisit this decision if:

1. **Episodic memory exceeds 10 MB** (>10,000 runs)
2. **Complex queries needed** (e.g., "find all runs where peak_day < 30 AND infection_rate > 0.05")
3. **Concurrent access required** (multiple processes reading/writing same workspace)
4. **Cross-workspace analytics** (e.g., "compare all experiments from last month")

In these cases, migrate to SQLite with:
- Indexed columns (run_id, timestamp, params)
- Full-text search on insights
- Aggregation queries (AVG, MAX, GROUP BY)

---

## Alternatives Considered But Rejected

### CSV Files
**Reason**: No nested structures (params/metrics are dicts), harder to parse

### YAML Files
**Reason**: Slower to parse than JSON, no standard library support in Python <3.11

### MessagePack
**Reason**: Binary format (not human-readable), requires external library

### Parquet Files
**Reason**: Columnar format optimized for analytics, overkill for append-only logs

---

## Related Decisions

- **ADR-001**: Memory architecture (defines what needs storage)
- **ADR-003**: LLM orchestration (how memory is injected into prompts)

---

## References

- [JSONL Specification](https://jsonlines.org/)
- [SQLite When To Use](https://www.sqlite.org/whentouse.html)
- [Git-Friendly Data Formats](https://bost.ocks.org/mike/make/)

---

## Changelog

- **2024-04**: Initial decision (flat files over SQLite)
- **2024-04**: Added performance benchmarks
- **2024-04**: Specified atomic write strategy
