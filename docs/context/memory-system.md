# Memory System Architecture

**Status**: Implemented  
**Location**: `abm_auto/memory/store.py`  
**Related ADR**: [ADR-001](../decisions/ADR-001-memory-architecture.md)

---

## Overview

ABM-Auto uses a **3-tier experiment memory system** to accumulate knowledge across simulation runs. This design balances immediate context needs (current experiment state) with long-term learning (cross-experiment patterns).

**Design Philosophy**: Inspired by cognitive psychology's memory models, adapted for iterative ABM research workflows.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   ExperimentMemory                      │
│                  (Unified Interface)                    │
└───────────────┬─────────────────┬──────────────────────┘
                │                 │
    ┌───────────▼──────┐  ┌───────▼────────┐  ┌──────────▼─────────┐
    │ Working Memory   │  │ Episodic Memory│  │ Semantic Memory    │
    │ (Session State)  │  │ (Run History)  │  │ (Knowledge Base)   │
    ├──────────────────┤  ├────────────────┤  ├────────────────────┤
    │ • Max 20 entries │  │ • Append-only  │  │ • Max 200 entries  │
    │ • Priority-pruned│  │ • JSONL format │  │ • Confidence-ranked│
    │ • JSON storage   │  │ • Per-run logs │  │ • Upsert by key    │
    └──────────────────┘  └────────────────┘  └────────────────────┘
         working.json         episodic.jsonl        semantic.json
```

---

## Tier 1: Working Memory

**Purpose**: Track the current experiment's active state.

**Characteristics**:
- **Capacity**: Max 20 entries (priority-pruned when full)
- **Lifetime**: Session-scoped (cleared between experiments)
- **Storage**: `working.json` (key-value pairs with priority scores)
- **Token Budget**: 500 tokens for LLM context injection

**Data Structure**:
```python
@dataclass
class WorkingEntry:
    key: str              # e.g., "current_hypothesis"
    value: Any            # Arbitrary JSON-serializable data
    priority: float       # 0.0–1.0 (higher = more important)
    updated_at: float     # Unix timestamp
```

**Use Cases**:
- Store current parameter sweep configuration
- Track active hypothesis being tested
- Cache last run's metrics for quick comparison
- Flag experimental conditions (e.g., "using_enhanced_mode")

**Example**:
```python
memory.working.set("current_hypothesis", "Higher infection rate → faster epidemic peak", priority=0.8)
memory.working.set("last_run", 42, priority=0.9)
memory.working.get("current_hypothesis")  # Returns the hypothesis string
```

**Pruning Strategy**: When exceeding 20 entries, lowest-priority items are evicted first.

---

## Tier 2: Episodic Memory

**Purpose**: Maintain a chronological log of all simulation runs.

**Characteristics**:
- **Capacity**: Unbounded (append-only)
- **Lifetime**: Persistent across sessions
- **Storage**: `episodic.jsonl` (one JSON object per line)
- **Token Budget**: 1500 tokens (recent 10 runs by default)

**Data Structure**:
```python
@dataclass
class EpisodicEntry:
    run_id: int           # Sequential run identifier
    params: dict          # Input parameters for this run
    metrics: dict         # Final output metrics
    hypothesis: str       # What was being tested
    insights: str         # LLM-generated analysis
    outcome: str          # "success" | "failure" | "neutral"
    importance: float     # 0.0–1.0 (for future retrieval ranking)
    timestamp: float      # Unix timestamp
```

**Use Cases**:
- Retrieve parameter-metric pairs for sensitivity analysis
- Compare current run against historical baselines
- Identify parameter combinations that led to anomalies
- Generate summary statistics across all runs

**Example**:
```python
memory.episodic.record(EpisodicEntry(
    run_id=1,
    params={"infection_rate": 0.05, "recovery_days": 14},
    metrics={"peak_infected": 342, "epidemic_duration": 87},
    hypothesis="Testing baseline scenario",
    insights="Peak occurs at day 23, matches SIR theory",
    outcome="success",
    importance=0.7
))

# Later: retrieve recent runs
recent = memory.episodic.recent(n=5)
```

**Context Injection**: When injecting into LLM prompts, most recent runs appear first (reverse chronological order).

---

## Tier 3: Semantic Memory

**Purpose**: Store validated, cross-experiment knowledge.

**Characteristics**:
- **Capacity**: Max 200 entries (confidence-pruned)
- **Lifetime**: Persistent, manually curated
- **Storage**: `semantic.json` (key-value with metadata)
- **Token Budget**: 1500 tokens (highest confidence first)

**Data Structure**:
```python
@dataclass
class SemanticEntry:
    key: str              # Unique identifier (e.g., "infection_rate_effect")
    knowledge: str        # Natural language description
    confidence: float     # 0.0–1.0 (evidence strength)
    source_runs: list[int]  # Which runs support this claim
    category: str         # "pattern" | "rule" | "anomaly" | "hypothesis"
    updated_at: float     # Unix timestamp
```

**Categories**:
- **pattern**: Observed regularities (e.g., "Higher density → faster spread")
- **rule**: Validated causal relationships (e.g., "Recovery rate inversely affects peak")
- **anomaly**: Unexpected behaviors requiring investigation
- **hypothesis**: Tentative explanations awaiting validation

**Use Cases**:
- Guide parameter selection in new experiments
- Avoid re-testing already-validated hypotheses
- Detect contradictions between new results and prior knowledge
- Build domain-specific heuristics for optimization

**Example**:
```python
memory.semantic.store(
    key="network_topology_impact",
    knowledge="Scale-free networks show 30% higher epidemic peaks than random graphs (n=15 runs)",
    confidence=0.85,
    source_runs=[3, 7, 12, 18, 21],
    category="pattern"
)

# Later: search for relevant knowledge
results = memory.semantic.search("network", category="pattern")
```

**Pruning Strategy**: When exceeding 200 entries, lowest-confidence items are evicted (ties broken by oldest `updated_at`).

---

## Token Budget Management

**User-Configurable**: Total budget specified via CLI (`--memory-budget`) or config file.

**Adaptive Allocation**: System automatically distributes tokens across tiers based on configurable ratios.

### Default Configuration (3500 tokens)

| Tier      | Tokens | % | Rationale                                      |
|-----------|--------|---|------------------------------------------------|
| Working   | 500    | 14% | Small, high-priority state                     |
| Episodic  | 1500   | 43% | Recent runs provide immediate context          |
| Semantic  | 1500   | 43% | Accumulated knowledge guides future decisions  |

### Budget Scaling Examples

| Total Budget | Working | Episodic | Semantic | Use Case |
|--------------|---------|----------|----------|----------|
| 1000         | 200     | 400      | 400      | Minimal (fast iteration, low cost) |
| 3500         | 500     | 1500     | 1500     | Default (balanced) |
| 8000         | 1000    | 3500     | 3500     | Rich context (complex experiments) |
| 16000        | 1000    | 7500     | 7500     | Maximum (100+ runs, deep history) |

### Allocation Algorithm

```python
def allocate_budget(total: int, ratios: dict = None) -> dict:
    """
    Adaptive token allocation with constraints.
    
    Default ratios: working=0.14, episodic=0.43, semantic=0.43
    Constraints: working ∈ [200, 1000], episodic ≥ 500, semantic ≥ 500
    """
    ratios = ratios or {"working": 0.14, "episodic": 0.43, "semantic": 0.43}
    
    working = max(200, min(1000, int(total * ratios["working"])))
    remaining = total - working
    episodic = max(500, int(remaining * ratios["episodic"] / (ratios["episodic"] + ratios["semantic"])))
    semantic = max(500, remaining - episodic)
    
    return {"working": working, "episodic": episodic, "semantic": semantic}
```

### CLI Usage

```bash
# Use default budget (3500 tokens)
abm-auto run story.md

# Specify custom budget
abm-auto run story.md --memory-budget 8000

# Override allocation ratios
abm-auto run story.md --memory-budget 8000 \
  --memory-ratio working=0.15,episodic=0.50,semantic=0.35
```

### Configuration File

```yaml
# .abm-auto.yml
memory:
  budget: 8000
  allocation:
    working: 0.14
    episodic: 0.43
    semantic: 0.43
```

**Why Token Limits?**  
LLM context windows are finite. Injecting all memory would:
1. Exceed context limits on long experiments (100+ runs)
2. Dilute signal with irrelevant historical data
3. Increase API costs unnecessarily

**Estimation Method**: `~3 characters per token` (conservative for mixed CJK/English text).

**Dynamic Adjustment**: System monitors actual token usage and warns if allocation is suboptimal:
- "Working memory underutilized (150/500 tokens) — consider reducing budget"
- "Episodic memory truncated (2000/1500 tokens) — consider increasing budget"

---

## Retrieval Interface

**Unified Context Injection**:
```python
context = memory.retrieve_context()
# Returns formatted string with all 3 tiers, respecting token budgets
```

**Output Format**:
```markdown
### 当前实验状态
- [current_hypothesis] (p=0.8): Testing network topology effects
- [last_run] (p=0.9): 42

### 历史运行记录
Run 42 (success): params={"topology": "scale_free"}, metrics={"peak": 456}
Run 41 (neutral): params={"topology": "random"}, metrics={"peak": 312}
...

### 累积知识
[pattern] network_topology_impact (conf=0.85): Scale-free networks show 30% higher peaks
[rule] recovery_rate_effect (conf=0.92): Recovery rate inversely affects epidemic duration
...
```

This context is injected into LLM prompts during:
- **Phase 4** (Sensitivity Analysis) — Guide parameter exploration
- **Phase 5** (Optimization) — Inform next parameter choices
- **Phase 6** (Reporting) — Synthesize cross-run insights

---

## Workflow Integration

### During Experiment Execution

1. **Initialization** (`pipeline.py:__init__`)
   ```python
   self.memory = ExperimentMemory(self.workspace.path / "memory")
   ```

2. **After Each Run** (`pipeline.py:_ingest_to_memory`)
   ```python
   self.memory.ingest_run(
       run_id=i,
       params=current_params,
       metrics=final_metrics,
       hypothesis=current_hypothesis,
       insights=llm_generated_analysis,
       outcome="success" if meets_criteria else "neutral"
   )
   ```

3. **Knowledge Extraction** (Phase 6e)
   ```python
   # LLM extracts patterns from episodic memory
   semantic_knowledge = extract_patterns(memory.episodic.all())
   memory.add_knowledge(
       key="discovered_pattern_1",
       knowledge=semantic_knowledge,
       confidence=0.7,
       source_runs=[1, 2, 3],
       category="pattern"
   )
   ```

### CLI Inspection

```bash
# View all memory tiers
abm-auto memory workspace/20260430_153000_abc123

# View specific tier
abm-auto memory workspace/my_run --tier semantic

# Export to JSON
abm-auto memory workspace/my_run --export memory_dump.json
```

---

## Design Rationale

**Why 3 Tiers?**  
- **Working**: Immediate context (like human short-term memory)
- **Episodic**: Detailed history (like autobiographical memory)
- **Semantic**: Abstracted knowledge (like learned facts)

**Why Flat Files?**  
- Git-friendly (diffs show actual changes)
- No database setup required
- Portable across systems
- Human-readable for debugging

**Why Not 5 Tiers?**  
Original inspiration (automaton-main) used 5 tiers. ABM experiments have simpler needs:
- No "sensory buffer" (no real-time streaming data)
- No "procedural memory" (skills are in code, not learned)

See [ADR-001](../decisions/ADR-001-memory-architecture.md) for full decision context.

---

## Performance Characteristics

**Write Performance**:
- Working: O(1) upsert + O(n log n) pruning (n ≤ 20)
- Episodic: O(1) append
- Semantic: O(1) upsert + O(n log n) pruning (n ≤ 200)

**Read Performance**:
- Working: O(n) scan (n ≤ 20)
- Episodic: O(m) scan for recent(n), where m = total runs
- Semantic: O(n) scan (n ≤ 200)

**Disk Usage** (typical 50-run experiment):
- `working.json`: ~2 KB
- `episodic.jsonl`: ~50 KB (1 KB per run)
- `semantic.json`: ~20 KB (10-15 entries)

---

## Future Enhancements

**Potential Improvements** (not yet implemented):

1. **Vector Search** for semantic memory (e.g., using sentence-transformers)
2. **Automatic Confidence Decay** (older knowledge loses confidence over time)
3. **Cross-Experiment Memory Sharing** (global semantic memory pool)
4. **Memory Visualization Dashboard** (interactive exploration UI)

See [GitHub Issues](https://github.com/your-repo/abm-auto/issues) for tracking.

---

## Related Documentation

- [ADR-001: Memory Architecture](../decisions/ADR-001-memory-architecture.md) — Why 3 tiers?
- [ADR-002: Flat File Storage](../decisions/ADR-002-flat-file-storage.md) — Why not SQLite?
- [Pipeline Phases](pipeline-phases.md) — How memory integrates into workflow
- [Developer Guide](../guides/developer-guide.md) — Extending memory system
