# ADR-001: Three-Tier Memory Architecture

**Status**: Accepted  
**Date**: 2024-04  
**Deciders**: Core team  
**Context**: Pipeline Phase 4-6 loop (Run → Analyze → Optimize)

---

## Context and Problem Statement

ABM parameter exploration requires iterative refinement: run simulation → interpret results → adjust parameters → repeat. Early versions of abm-auto used stateless agents, forcing the LLM to re-read all prior run logs on every iteration. This approach:

1. **Exhausted token budgets** — 10 iterations × 500 tokens/run = 5000 tokens before any reasoning
2. **Lost cross-experiment insights** — patterns discovered in Experiment A were unavailable in Experiment B
3. **Lacked prioritization** — all historical data treated equally, regardless of relevance

The system needed structured memory to:
- Retain context across iterations within one experiment
- Accumulate validated knowledge across experiments
- Fit within LLM token limits (≤4000 tokens for memory)

---

## Decision Drivers

1. **Token efficiency** — Memory must compress 10+ iterations into <4000 tokens
2. **Relevance ranking** — Recent/important information should dominate context
3. **Cross-experiment learning** — Validated patterns should persist beyond single runs
4. **Flat-file simplicity** — No database dependencies (SQLite, PostgreSQL)
5. **Human inspectability** — Memory files should be readable for debugging

---

## Considered Options

### Option 1: Single Append-Only Log
Store all run results in one JSONL file, load last N entries.

**Pros**: Simple implementation, preserves full history  
**Cons**: No prioritization, no cross-experiment learning, token waste on irrelevant old runs

### Option 2: Vector Database (Pinecone, Chroma)
Embed run results as vectors, retrieve top-K similar entries.

**Pros**: Semantic search, automatic relevance ranking  
**Cons**: External dependency, embedding cost, overkill for structured data

### Option 3: Three-Tier Memory (Selected)
Separate storage for:
- **Working memory** — current session state (hypothesis, last run)
- **Episodic memory** — append-only log of all runs in this experiment
- **Semantic memory** — cross-experiment knowledge base (patterns, rules)

**Pros**: Explicit prioritization, cross-experiment learning, token-efficient, flat files  
**Cons**: More complex than single log, requires pruning logic

---

## Decision Outcome

**Chosen option**: Three-tier memory (Option 3)

### Architecture

```
workspace/
  memory/
    working.json      # Session state (max 20 entries, priority-pruned)
    episodic.jsonl    # All runs in this experiment (append-only)
    semantic.json     # Cross-experiment knowledge (max 200 entries, confidence-ranked)
```

### Memory Tiers

#### Working Memory (`working.json`)
**Purpose**: Track current session state  
**Scope**: Single experiment  
**Lifetime**: Cleared between experiments  
**Max size**: 20 entries  
**Pruning**: Priority-based (recent > old, hypothesis > metrics)

**Schema**:
```json
{
  "entries": [
    {
      "type": "hypothesis",
      "content": "Increasing infection_rate should accelerate epidemic peak",
      "iteration": 3,
      "priority": 10
    },
    {
      "type": "last_run",
      "params": {"infection_rate": 0.05},
      "metrics": {"peak_day": 42, "total_infected": 8500},
      "iteration": 3,
      "priority": 9
    }
  ]
}
```

#### Episodic Memory (`episodic.jsonl`)
**Purpose**: Record all simulation runs  
**Scope**: Single experiment  
**Lifetime**: Persists after experiment completes  
**Max size**: Unlimited (append-only)  
**Pruning**: None (full history preserved)

**Schema** (one JSON object per line):
```json
{"iteration": 1, "params": {"infection_rate": 0.03, "recovery_days": 14}, "metrics": {"peak_day": 56, "total_infected": 6200}, "insight": "Slow spread, late peak"}
{"iteration": 2, "params": {"infection_rate": 0.05, "recovery_days": 14}, "metrics": {"peak_day": 42, "total_infected": 8500}, "insight": "Faster spread, earlier peak"}
```

**Token budget allocation**: Load last 10 runs (≈1500 tokens)

#### Semantic Memory (`semantic.json`)
**Purpose**: Store validated patterns across experiments  
**Scope**: Global (all experiments)  
**Lifetime**: Persists indefinitely  
**Max size**: 200 entries  
**Pruning**: Confidence-ranked (low-confidence entries evicted first)

**Schema**:
```json
{
  "patterns": [
    {
      "id": "pattern_001",
      "rule": "In SIR models, doubling infection_rate reduces peak_day by ~30%",
      "evidence": ["exp_2024-04-15_001", "exp_2024-04-18_003"],
      "confidence": 0.85,
      "created": "2024-04-15T10:30:00Z",
      "last_validated": "2024-04-18T14:20:00Z"
    }
  ]
}
```

**Token budget allocation**: Load top 20 patterns by confidence (≈1500 tokens)

---

## Memory Ingestion Flow

```
Phase 4: Run simulation
  ↓
Phase 5: Analyze results
  ↓
  1. Append to episodic.jsonl (params + metrics + insight)
  2. Update working.json (last_run entry, prune if >20)
  3. Check if insight validates/contradicts semantic patterns
     → If validates: increment confidence
     → If contradicts: decrement confidence or create new pattern
  ↓
Phase 6: Optimize (LLM receives working + episodic tail + semantic top-K)
```

---

## Token Budget Allocation

**User-Configurable Budget**: Users specify total token budget via CLI or config file.

**Default Allocation** (3500 tokens total):

| Tier | Tokens | % | Selection Strategy |
|------|--------|---|-------------------|
| Working | 500 | 14% | All entries (max 20, priority-pruned) |
| Episodic | 1500 | 43% | Last N runs (LIFO) |
| Semantic | 1500 | 43% | Top K patterns by confidence |

**Adaptive Allocation Strategy**:
```python
def allocate_budget(total_budget: int) -> dict[str, int]:
    """
    Allocate token budget across memory tiers.
    
    Ratios:
    - Working: 14% (min 200, max 1000)
    - Episodic: 43% (min 500, no max)
    - Semantic: 43% (min 500, no max)
    """
    working = max(200, min(1000, int(total_budget * 0.14)))
    remaining = total_budget - working
    episodic = max(500, int(remaining * 0.5))
    semantic = remaining - episodic
    
    return {
        "working": working,
        "episodic": episodic,
        "semantic": semantic
    }
```

**Example Budgets**:

| Total | Working | Episodic | Semantic | Use Case |
|-------|---------|----------|----------|----------|
| 1000 | 200 | 400 | 400 | Minimal (fast, cheap) |
| 3500 | 500 | 1500 | 1500 | Default (balanced) |
| 8000 | 1000 | 3500 | 3500 | Rich context (deep history) |
| 16000 | 1000 | 7500 | 7500 | Maximum (100+ runs) |

---

## Consequences

### Positive

✅ **Token efficiency**: 10 iterations compressed from 5000 → 1500 tokens (episodic)  
✅ **Cross-experiment learning**: Semantic memory persists validated patterns  
✅ **Relevance ranking**: Working memory prioritizes current hypothesis, episodic uses LIFO, semantic uses confidence  
✅ **Flat-file simplicity**: JSON/JSONL, no database setup  
✅ **Human inspectable**: Plain text files for debugging  
✅ **Graceful degradation**: If semantic.json missing, system still works (episodic + working only)

### Negative

⚠️ **Complexity**: Three files vs. one log  
⚠️ **Pruning logic**: Working memory priority assignment requires heuristics  
⚠️ **Confidence calibration**: Semantic memory confidence scores need tuning  
⚠️ **No semantic search**: Keyword-based retrieval only (no embeddings)

### Risks

🔴 **Semantic memory pollution**: Low-quality patterns accumulate if confidence thresholds too permissive  
**Mitigation**: Require ≥2 experiments to validate a pattern, decay confidence over time

🔴 **Episodic memory bloat**: Large experiments (100+ iterations) → huge JSONL files  
**Mitigation**: Compress old runs (keep params + metrics, discard raw output)

🔴 **Working memory thrashing**: Aggressive pruning loses important context  
**Mitigation**: Reserve slots for hypothesis (priority 10) and last_run (priority 9)

---

## Implementation Notes

### CLI Configuration
```bash
# Use default budget (3500 tokens)
abm-auto run story.md

# Specify custom budget
abm-auto run story.md --memory-budget 8000

# Fine-tune allocation ratios
abm-auto run story.md --memory-budget 8000 \
  --memory-ratio working=0.15,episodic=0.45,semantic=0.40
```

### Config File
```yaml
# .abm-auto.yml
memory:
  budget: 8000
  allocation:
    working: 0.14
    episodic: 0.43
    semantic: 0.43
  constraints:
    working_min: 200
    working_max: 1000
    episodic_min: 500
    semantic_min: 500
```

### Programmatic API
```python
from abm_auto.memory.store import ExperimentMemory

# Auto-allocate from total budget
memory = ExperimentMemory(
    memory_dir=Path("workspace/memory"),
    total_budget=8000  # Adaptive allocation
)

# Manual allocation
memory = ExperimentMemory(
    memory_dir=Path("workspace/memory"),
    budget={"working": 1000, "episodic": 3500, "semantic": 3500}
)
```

### Pruning Triggers
- **Working**: After every Phase 5 (analyze), prune if >20 entries
- **Semantic**: After every experiment completion, prune if >200 entries

### Priority Heuristics (Working Memory)
```python
PRIORITY = {
    "hypothesis": 10,
    "last_run": 9,
    "anomaly": 8,
    "insight": 7,
    "metric": 5,
}
```

### Confidence Updates (Semantic Memory)
```python
# Pattern validated by new experiment
confidence = min(1.0, confidence + 0.1)

# Pattern contradicted by new experiment
confidence = max(0.0, confidence - 0.2)

# Evict if confidence < 0.3 after 5+ experiments
```

---

## Alternatives Considered But Rejected

### SQLite Database
**Reason**: Adds dependency, harder to inspect, overkill for structured logs

### Redis/Memcached
**Reason**: Requires server process, not suitable for CLI tool

### Single JSON File with Sections
**Reason**: No clear separation between session state (working) and history (episodic)

### LangChain Memory
**Reason**: Opinionated abstractions, harder to customize pruning logic

---

## Related Decisions

- **ADR-002**: Token budget allocation across memory tiers (pending)
- **ADR-003**: Semantic memory confidence scoring (pending)
- **ADR-004**: Cross-experiment pattern validation rules (pending)

---

## References

- Grimm, V. et al. (2020). The ODD Protocol. *JASSS*, 23(2), 7.
- Weizenbaum, J. (1966). ELIZA — A Computer Program For the Study of Natural Language Communication. *CACM*, 9(1), 36-45. (Early example of conversational memory)
- Laird, J. E. (2012). *The Soar Cognitive Architecture*. MIT Press. (Working/episodic/semantic memory taxonomy)

---

## Changelog

- **2024-04**: Initial decision (three-tier architecture)
- **2024-04**: Added token budget allocation table
- **2024-04**: Specified pruning triggers and confidence update rules
